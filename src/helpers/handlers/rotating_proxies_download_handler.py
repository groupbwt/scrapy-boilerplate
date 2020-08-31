from scrapy.core.downloader.handlers.http import HTTPDownloadHandler
from scrapy.utils import reactor
from twisted.web.client import HTTPConnectionPool


class RotatingProxiesDownloadHandler(HTTPDownloadHandler):
    def __init__(self, settings, crawler=None):
        super(RotatingProxiesDownloadHandler, self).__init__(settings, crawler)
        self._pool = HTTPConnectionPool(reactor, persistent=False)
        self._pool.maxPersistentPerHost = settings.getint("CONCURRENT_REQUESTS_PER_DOMAIN")
        self._pool._factory.noisy = False
