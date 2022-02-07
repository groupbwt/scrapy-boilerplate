import scrapy
from direct.examples import DirectExampleItem
import random
from direct.spiders import DirectSpider
from direct.utils.direct_errback import direct_errback


class DirectExmapleSpider(DirectSpider):
    name = "direct_exmaple_spider"
    fetch_chunk = 10

    custom_settings = {"EXTENSIONS": {"extensions.DirectExampleExtension": 100,}}

    def parse(self, response):
        item = DirectExampleItem()
        meta = response.meta
        data = meta["task_body"]
        item["id"] = data["id"]
        item["page"] = random.randint(0, 100)
        item["title"] = response.text[:100]
        yield item

    @direct_errback
    def _errback(self, failure):
        self.logger.debug("errback")

    def next_request(self, task_id, body):
        url = body["url"].strip()
        if not url.startswith("http"):
            url = f"https://{url}"
        return scrapy.Request(url=url, errback=self._errback)
