import logging

from scrapy import Spider, Request
from scrapy.core.downloader.handlers.http import HTTPDownloadHandler


# custom_settings = {
#     "DOWNLOAD_HANDLERS": {
#         'http': 'utils.handlers.RotatingProxiesDownloadHandler',
#         'https': 'utils.handlers.RotatingProxiesDownloadHandler'
#     },
#     'ROTATING_PROXIES_DOWNLOADER_HANDLER_AUTO_CLOSE_CACHED_CONNECTIONS_ENABLED': False,
# }


class RotatingProxiesDownloadHandler(HTTPDownloadHandler):
    logger = logging.getLogger(name=__name__)

    def download_request(self, request: Request, spider: Spider):
        """Return a deferred for the HTTP download"""
        if (
            spider.settings.get('ROTATING_PROXIES_DOWNLOADER_HANDLER_AUTO_CLOSE_CACHED_CONNECTIONS_ENABLED') or
            request.meta.get('close_cached_connections')
        ):
            if request.meta.get('close_cached_connections'):
                self.logger.debug('close cached connections')
            self._pool.closeCachedConnections()

        return super().download_request(request, spider)
