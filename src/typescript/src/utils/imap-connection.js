import {parseExpr, Parser} from "imap/lib/Parser";
import {inspect} from "util";
const Imap = require('imap')
import {Socket} from "net";
import tls from "tls";
import {EventEmitter} from "events";


const RE_IDLENOOPRES = /^(IDLE|NOOP) /,
      CRLF = '\r\n'


class ImapConnection extends Imap {
  constructor(config) {
    super(config)
  }

  connect() {
    let config = this._config,
      self = this,
      socket,
      parser,
      tlsOptions

    socket = config.socket || new Socket();
    socket.setKeepAlive(true);
    this._sock = undefined;
    this._tagcount = 0;
    this._tmrConn = undefined;
    this._tmrKeepalive = undefined;
    this._tmrAuth = undefined;
    this._queue = [];
    this._box = undefined;
    this._idle = {started: undefined, enabled: false};
    this._parser = undefined;
    this._curReq = undefined;
    this.delimiter = undefined;
    this.namespaces = undefined;
    this.state = 'disconnected';

    if (config.tls) {
      tlsOptions = {};
      tlsOptions.host = config.host;
      // Host name may be overridden the tlsOptions
      for (let k in config.tlsOptions)
        tlsOptions[k] = config.tlsOptions[k];
      tlsOptions.socket = socket;
    }

    if (config.tls)
      this._sock = tls.connect(tlsOptions, onconnect);
    else {
      socket.once('connect', onconnect);
      this._sock = socket;
    }

    function onconnect() {
      clearTimeout(self._tmrConn);
      self.state = 'connected';
      self.debug && self.debug('[connection] Connected to host');
      self._tmrAuth = setTimeout(function () {
        const err = new Error('Timed out while authenticating with server');
        err.source = 'timeout-auth';
        self.emit('error', err);
        socket.destroy();
      }, config.authTimeout);
    }

    this._onError = function (err) {
      clearTimeout(self._tmrConn);
      clearTimeout(self._tmrAuth);
      self.debug && self.debug('[connection] Error: ' + err);
      err.source = 'socket';
      self.emit('error', err);
    };
    this._sock.on('error', this._onError);

    this._onSocketTimeout = function () {
      clearTimeout(self._tmrConn);
      clearTimeout(self._tmrAuth);
      clearTimeout(self._tmrKeepalive);
      self.state = 'disconnected';
      self.debug && self.debug('[connection] Socket timeout');

      const err = new Error('Socket timed out while talking to server');
      err.source = 'socket-timeout';
      self.emit('error', err);
      socket.destroy();
    };
    this._sock.on('timeout', this._onSocketTimeout);
    socket.setTimeout(config.socketTimeout);

    socket.once('close', function (had_err) {
      clearTimeout(self._tmrConn);
      clearTimeout(self._tmrAuth);
      clearTimeout(self._tmrKeepalive);
      self.state = 'disconnected';
      self.debug && self.debug('[connection] Closed');
      self.emit('close', had_err);
    });

    socket.once('end', function () {
      clearTimeout(self._tmrConn);
      clearTimeout(self._tmrAuth);
      clearTimeout(self._tmrKeepalive);
      self.state = 'disconnected';
      self.debug && self.debug('[connection] Ended');
      self.emit('end');
    });

    this._parser = parser = new Parser(this._sock, this.debug);

    parser.on('untagged', function (info) {
      self._resUntagged(info);
    });
    parser.on('tagged', function (info) {
      self._resTagged(info);
    });
    parser.on('body', function (stream, info) {
      let msg = self._curReq.fetchCache[info.seqno], toget;

      if (msg === undefined) {
        msg = self._curReq.fetchCache[info.seqno] = {
          msgEmitter: new EventEmitter(),
          toget: self._curReq.fetching.slice(0),
          attrs: {},
          ended: false
        };

        self._curReq.bodyEmitter.emit('message', msg.msgEmitter, info.seqno);
      }

      toget = msg.toget;

      // here we compare the parsed version of the expression inside BODY[]
      // because 'HEADER.FIELDS (TO FROM)' really is equivalent to
      // 'HEADER.FIELDS ("TO" "FROM")' and some servers will actually send the
      // quoted form even if the client did not use quotes
      var thisbody = parseExpr(info.which);
      for (var i = 0, len = toget.length; i < len; ++i) {
        if (_deepEqual(thisbody, toget[i])) {
          toget.splice(i, 1);
          msg.msgEmitter.emit('body', stream, info);
          return;
        }
      }
      stream.resume(); // a body we didn't ask for?
    });
    parser.on('continue', function (info) {
      var type = self._curReq.type;
      if (type === 'IDLE') {
        if (self._queue.length
          && self._idle.started === 0
          && self._curReq
          && self._curReq.type === 'IDLE'
          && self._sock
          && self._sock.writable
          && !self._idle.enabled) {
          self.debug && self.debug('=> DONE');
          self._sock.write('DONE' + CRLF);
          return;
        }
        // now idling
        self._idle.started = Date.now();
      } else if (/^AUTHENTICATE XOAUTH/.test(self._curReq.fullcmd)) {
        self._curReq.oauthError = new Buffer(info.text, 'base64').toString('utf8');
        self.debug && self.debug('=> ' + inspect(CRLF));
        self._sock.write(CRLF);
      } else if (type === 'APPEND') {
        self._sockWriteAppendData(self._curReq.appendData);
      } else if (self._curReq.lines && self._curReq.lines.length) {
        var line = self._curReq.lines.shift() + '\r\n';
        self.debug && self.debug('=> ' + inspect(line));
        self._sock.write(line, 'binary');
      }
    });
    parser.on('other', function (line) {
      var m;
      if (m = RE_IDLENOOPRES.exec(line)) {
        // no longer idling
        self._idle.enabled = false;
        self._idle.started = undefined;
        clearTimeout(self._tmrKeepalive);

        self._curReq = undefined;

        if (self._queue.length === 0
          && self._config.keepalive
          && self.state === 'authenticated'
          && !self._idle.enabled) {
          self._idle.enabled = true;
          if (m[1] === 'NOOP')
            self._doKeepaliveTimer();
          else
            self._doKeepaliveTimer(true);
        }

        self._processQueue();
      }
    });

    this._tmrConn = setTimeout(function () {
      var err = new Error('Timed out while connecting to server');
      err.source = 'timeout';
      self.emit('error', err);
      socket.destroy();
    }, config.connTimeout);

    if (!socket.remoteAddress) {
      socket.connect({
        port: config.port,
        host: config.host,
        localAddress: config.localAddress
      });
    }
  }
}

// Pulled from assert.deepEqual:
var pSlice = Array.prototype.slice;
function _deepEqual(actual, expected) {
  // 7.1. All identical values are equivalent, as determined by ===.
  if (actual === expected) {
    return true;

  } else if (Buffer.isBuffer(actual) && Buffer.isBuffer(expected)) {
    if (actual.length !== expected.length) return false;

    for (var i = 0; i < actual.length; i++) {
      if (actual[i] !== expected[i]) return false;
    }

    return true;

  // 7.2. If the expected value is a Date object, the actual value is
  // equivalent if it is also a Date object that refers to the same time.
  } else if (actual instanceof Date && expected instanceof Date) {
    return actual.getTime() === expected.getTime();

  // 7.3 If the expected value is a RegExp object, the actual value is
  // equivalent if it is also a RegExp object with the same source and
  // properties (`global`, `multiline`, `lastIndex`, `ignoreCase`).
  } else if (actual instanceof RegExp && expected instanceof RegExp) {
    return actual.source === expected.source &&
           actual.global === expected.global &&
           actual.multiline === expected.multiline &&
           actual.lastIndex === expected.lastIndex &&
           actual.ignoreCase === expected.ignoreCase;

  // 7.4. Other pairs that do not both pass typeof value == 'object',
  // equivalence is determined by ==.
  } else if (typeof actual !== 'object' && typeof expected !== 'object') {
    return actual == expected;

  // 7.5 For all other Object pairs, including Array objects, equivalence is
  // determined by having the same number of owned properties (as verified
  // with Object.prototype.hasOwnProperty.call), the same set of keys
  // (although not necessarily the same order), equivalent values for every
  // corresponding key, and an identical 'prototype' property. Note: this
  // accounts for both named and indexed properties on Arrays.
  } else {
    return objEquiv(actual, expected);
  }
}

function objEquiv(a, b) {
  var ka, kb, key, i;
  if (isUndefinedOrNull(a) || isUndefinedOrNull(b))
    return false;
  // an identical 'prototype' property.
  if (a.prototype !== b.prototype) return false;
  //~~~I've managed to break Object.keys through screwy arguments passing.
  //   Converting to array solves the problem.
  if (isArguments(a)) {
    if (!isArguments(b)) {
      return false;
    }
    a = pSlice.call(a);
    b = pSlice.call(b);
    return _deepEqual(a, b);
  }
  try {
    ka = Object.keys(a);
    kb = Object.keys(b);
  } catch (e) {//happens when one is a string literal and the other isn't
    return false;
  }
  // having the same number of owned properties (keys incorporates
  // hasOwnProperty)
  if (ka.length !== kb.length)
    return false;
  //the same set of keys (although not necessarily the same order),
  ka.sort();
  kb.sort();
  //~~~cheap key test
  for (i = ka.length - 1; i >= 0; i--) {
    if (ka[i] != kb[i])
      return false;
  }
  //equivalent values for every corresponding key, and
  //~~~possibly expensive deep test
  for (i = ka.length - 1; i >= 0; i--) {
    key = ka[i];
    if (!_deepEqual(a[key], b[key])) return false;
  }
  return true;
}

function isArguments(object) {
  return Object.prototype.toString.call(object) === '[object Arguments]';
}

function isUndefinedOrNull(value) {
  return value === null || value === undefined;
}

export default ImapConnection
