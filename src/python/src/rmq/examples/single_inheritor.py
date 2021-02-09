import json

import scrapy
from scrapy.core.downloader.handlers.http11 import TunnelError

from rmq.items import RMQItem
from rmq.pipelines import ItemProducerPipeline
from rmq.spiders import TaskToSingleResultSpider
from rmq.utils import get_import_full_name
from rmq.utils.decorators import rmq_callback, rmq_errback


class MetaDescriptionItem(RMQItem):
    description = scrapy.Field()


class SingleInheritor(TaskToSingleResultSpider):
    name = "single_inheritor_example"

    custom_settings = {"ITEM_PIPELINES": {get_import_full_name(ItemProducerPipeline): 310,}}

    def __init__(self, *args, **kwargs):
        super(SingleInheritor, self).__init__(*args, **kwargs)
        self.task_queue_name = f"{self.name}_task_queue"
        self.result_queue_name = f"{self.name}_result_queue"

    def next_request(self, _delivery_tag, msg_body):
        data = json.loads(msg_body)
        return scrapy.Request(data["url"], callback=self.parse)

    @rmq_callback
    def parse(self, response):
        meta_description = response.xpath('//meta[@name="description"]/@content').get(default=None)
        yield MetaDescriptionItem({"description": meta_description})

    @rmq_errback
    def _errback(self, failure):
        if failure.check(TunnelError):
            self.logger.info("TunnelError. Copy request")
            yield failure.request.copy()
        else:
            self.logger.warning(f"IN ERRBACK: {repr(failure)}")
