from twisted.internet import reactor
from twisted.internet.defer import Deferred


def sleep_deferred(second: float) -> Deferred:
    d = Deferred()
    reactor.callLater(second, d.callback, None)
    return d
