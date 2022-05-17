from twisted.python.failure import Failure


def get_response_or_request(failure: Failure):
    if hasattr(failure, 'response'):
        return failure.response
    if hasattr(failure.value, 'response'):
        return failure.value.response
    if hasattr(failure, 'request'):
        return failure.request
    if hasattr(failure.value, 'request'):
        return failure.value.request
    raise Exception('failed to retrieve response or request')
