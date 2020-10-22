import functools
import inspect

import scrapy
from twisted.python.failure import Failure
from direct.signals.direct_signals import errback_completed
from typing import Callable, Union
from direct.items import DirectItem


def direct_errback(errback_method: Callable) -> Callable:
    @functools.wraps(errback_method)
    def wrapper(self, *args: list, **kwargs: dict) -> Union[DirectItem, None]:
        errback_result = errback_method(self, *args, **kwargs)
        if isinstance(self, scrapy.Spider):
            if len(args) > 0:
                response_or_failure = args[0]
                if isinstance(response_or_failure, scrapy.http.Response):
                    try:
                        iter(errback_result)
                        for errback_result_item in errback_result:
                            yield errback_result_item
                    except TypeError:
                        pass
                    self.crawler.signals.send_catch_log(
                        signal=errback_completed,
                        response=response_or_failure,
                        spider=self,
                    )
                if isinstance(response_or_failure, Failure):
                    if hasattr(response_or_failure, "request"):
                        try:
                            iter(errback_result)
                            for errback_result_item in errback_result:
                                yield errback_result_item
                        except TypeError:
                            pass
                        self.crawler.signals.send_catch_log(
                            signal=errback_completed,
                            failure=response_or_failure,
                            spider=self,
                        )
            else:
                self.crawler.signals.send_catch_log(signal=errback_completed)
        else:
            raise Exception("Method must be Spider's class.")

    wrapper.__decorator_name__ = inspect.currentframe().f_code.co_name
    return wrapper
