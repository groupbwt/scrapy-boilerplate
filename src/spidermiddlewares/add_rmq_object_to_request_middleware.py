import scrapy


class AddRMQObjectToRequestMiddleware:
    def process_spider_output(self, response, result, spider):
        for request_or_item in result:
            if isinstance(request_or_item, scrapy.Request):
                if response.meta.get('rmq_object'):
                    request_or_item.meta['rmq_object'] = response.meta.get('rmq_object')
                yield request_or_item
            else:
                yield request_or_item
