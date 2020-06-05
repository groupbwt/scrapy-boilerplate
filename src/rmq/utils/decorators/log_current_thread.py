import logging
import threading
from functools import wraps


def log_current_thread(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        logging.debug(f"Callable name: {f.__name__}\tCurrent thread: {threading.current_thread()}")
        return f(*args, **kwargs)

    return wrapper
