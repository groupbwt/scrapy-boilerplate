import functools
import inspect

import scrapy

from rmq.signals import callback_completed, item_scheduled
from rmq.utils import RMQConstants


def rmq_callback(callback_method):
    @functools.wraps(callback_method)
    def wrapper(self, *args, **kwargs):
        delivery_tag_meta_key = RMQConstants.DELIVERY_TAG_META_KEY.value
        callback_result = callback_method(self, *args, **kwargs)
        if isinstance(self, scrapy.Spider):
            if len(args) > 0:
                response = args[0]
                if isinstance(response, scrapy.http.Response):
                    delivery_tag = response.meta.get(delivery_tag_meta_key, None)
                    try:
                        iter(callback_result)
                        for callback_result_item in callback_result:
                            if isinstance(callback_result_item, scrapy.Item):
                                self.crawler.signals.send_catch_log(
                                    signal=item_scheduled,
                                    response=response,
                                    spider=self,
                                    delivery_tag=delivery_tag,
                                )
                            yield callback_result_item
                    except TypeError:
                        pass
                    self.crawler.signals.send_catch_log(
                        signal=callback_completed,
                        response=response,
                        spider=self,
                        delivery_tag=delivery_tag,
                    )
            else:
                try:
                    iter(callback_result)
                    for callback_result_item in callback_result:
                        if isinstance(callback_result_item, scrapy.Item):
                            self.crawler.signals.send_catch_log(signal=item_scheduled, spider=self)
                        yield callback_result_item
                except TypeError:
                    pass
                self.crawler.signals.send_catch_log(signal=callback_completed, spider=self)
        else:
            try:
                iter(callback_result)
                yield from callback_result
            except TypeError:
                pass

    wrapper.__decorator_name__ = inspect.currentframe().f_code.co_name
    return wrapper
