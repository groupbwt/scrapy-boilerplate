from twisted.internet import reactor
from twisted.internet.defer import Deferred


class DelayedRequestsMiddleware:
    def process_request(self, request, spider):
        delay = request.meta.get('delay_request', None)
        if delay:
            d = Deferred()
            reactor.callLater(delay, d.callback, None)
            return d
