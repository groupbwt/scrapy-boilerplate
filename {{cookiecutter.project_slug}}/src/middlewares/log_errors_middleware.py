from scrapy import Request, Spider
from scrapy.http import Response


class LogErrorsMiddleware:
    def process_response(self, request: Request, response: Response, spider: Spider) -> Response:
        if response.status >= 400:
            spider.logger.critical(
                "Error {} on processing page <{}>".format(response.status, response.url)
            )
            # if response.status in [405, 503, 429, 456]:
            #     return scrapy.Request(request.url, dont_filter=True)

        return response
