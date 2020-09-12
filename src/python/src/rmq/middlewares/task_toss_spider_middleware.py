from scrapy import Request

from rmq.utils import RMQConstants


class TaskTossSpiderMiddleware:
    def process_spider_output(self, response, result, spider):
        delivery_tag_key = RMQConstants.DELIVERY_TAG_META_KEY.value
        for result_item in result:
            if isinstance(result_item, Request):
                response_delivery_tag = response.meta.get(delivery_tag_key, None)
                request_delivery_tag = result_item.meta.get(delivery_tag_key, None)
                if response_delivery_tag is not None and request_delivery_tag is None:
                    result_item.meta[delivery_tag_key] = response_delivery_tag
            yield result_item
