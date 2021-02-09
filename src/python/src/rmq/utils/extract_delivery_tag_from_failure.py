from typing import Optional

from scrapy import Request
from scrapy.http import Response
from twisted.python.failure import Failure


def extract_delivery_tag_from_failure(failure: Failure) -> Optional[int]:
    if hasattr(failure, "request") and isinstance(failure.request, Request):
        return failure.request.meta.get("delivery_tag")
    elif hasattr(failure, "response") and isinstance(failure.response, Response):
        return failure.response.meta.get("delivery_tag")
    elif hasattr(failure.value, "request") and isinstance(failure.value.request, Request):
        return failure.value.request.meta.get("delivery_tag")
    elif hasattr(failure.value, "response") and isinstance(failure.value.response, Response):
        return failure.value.response.meta.get("delivery_tag")
    elif hasattr(failure.value, "meta"):
        return failure.value.meta.get("delivery_tag")

    return None
