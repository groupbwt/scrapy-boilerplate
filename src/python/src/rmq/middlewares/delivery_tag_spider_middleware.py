from rmq.items import RMQItem
from rmq.utils import RMQConstants


class DeliveryTagSpiderMiddleware:
    def process_spider_output(self, response, result, spider):
        delivery_tag_key = RMQConstants.DELIVERY_TAG_META_KEY.value
        for result_item in result:
            if isinstance(result_item, RMQItem):
                response_delivery_tag = response.meta.get(delivery_tag_key, None)
                if response_delivery_tag is not None and (
                    delivery_tag_key not in result_item.keys()
                    or result_item[delivery_tag_key] is None
                    or result_item[delivery_tag_key] == ""
                ):
                    result_item[delivery_tag_key] = response_delivery_tag
            yield result_item
