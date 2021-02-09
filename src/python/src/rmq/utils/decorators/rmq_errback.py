import functools
import inspect

import scrapy
from twisted.python.failure import Failure

from rmq.signals import errback_completed, item_scheduled
from rmq.utils import RMQConstants


def rmq_errback(errback_method):
    @functools.wraps(errback_method)
    def wrapper(self, *args, **kwargs):
        delivery_tag_meta_key = RMQConstants.DELIVERY_TAG_META_KEY.value
        errback_result = errback_method(self, *args, **kwargs)
        if isinstance(self, scrapy.Spider):
            if len(args) > 0:
                response_or_failure = args[0]
                if isinstance(response_or_failure, scrapy.http.Response):
                    delivery_tag = response_or_failure.meta.get(delivery_tag_meta_key, None)
                    try:
                        iter(errback_result)
                        for errback_result_item in errback_result:
                            if isinstance(errback_result_item, scrapy.Item):
                                self.crawler.signals.send_catch_log(
                                    signal=item_scheduled,
                                    response=response_or_failure,
                                    spider=self,
                                    delivery_tag=delivery_tag,
                                )
                            yield errback_result_item
                    except TypeError:
                        pass
                    self.crawler.signals.send_catch_log(
                        signal=errback_completed,
                        response=response_or_failure,
                        spider=self,
                        delivery_tag=delivery_tag,
                    )
                if isinstance(response_or_failure, Failure):
                    if hasattr(response_or_failure, "request"):
                        delivery_tag = response_or_failure.request.meta.get(
                            delivery_tag_meta_key, None
                        )
                        try:
                            iter(errback_result)
                            for errback_result_item in errback_result:
                                if isinstance(errback_result_item, scrapy.Item):
                                    self.crawler.signals.send_catch_log(
                                        signal=item_scheduled,
                                        response=response_or_failure,
                                        spider=self,
                                        delivery_tag=delivery_tag,
                                    )
                                yield errback_result_item
                        except TypeError:
                            pass
                        self.crawler.signals.send_catch_log(
                            signal=errback_completed,
                            failure=response_or_failure,
                            spider=self,
                            delivery_tag=delivery_tag,
                        )
            else:
                try:
                    iter(errback_result)
                    for errback_result_item in errback_result:
                        if (
                            isinstance(errback_result_item, scrapy.Item)
                            and delivery_tag_meta_key in errback_result_item.keys()
                        ):
                            self.crawler.signals.send_catch_log(
                                signal=item_scheduled,
                                response=None,
                                spider=self,
                                delivery_tag=errback_result_item[delivery_tag_meta_key],
                            )
                except TypeError:
                    pass
                self.crawler.signals.send_catch_log(signal=errback_completed)
        else:
            try:
                iter(errback_result)
                for errback_result_item in errback_result:
                    if (
                        isinstance(errback_result_item, scrapy.Item)
                        and delivery_tag_meta_key in errback_result_item.keys()
                    ):
                        self.crawler.signals.send_catch_log(
                            signal=item_scheduled,
                            response=None,
                            spider=self,
                            delivery_tag=errback_result_item[delivery_tag_meta_key],
                        )
            except TypeError:
                pass

    wrapper.__decorator_name__ = inspect.currentframe().f_code.co_name
    return wrapper
