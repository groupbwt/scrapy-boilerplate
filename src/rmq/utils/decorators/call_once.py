from functools import wraps


def call_once(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not wrapper.__is_called:
            wrapper.__is_called = True
            return f(*args, **kwargs)

    wrapper.__is_called = False
    return wrapper
