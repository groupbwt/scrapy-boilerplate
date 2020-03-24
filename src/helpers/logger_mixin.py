import logging

from scrapy.settings import Settings
from scrapy.utils.project import get_project_settings


class LoggerMixin:
    """Class for adding .logger property and setup logging"""

    def __init__(self, logger: logging.Logger = None, settings: Settings = None):
        if logger:
            self.logger = logger
        else:
            if not settings:
                settings = get_project_settings()

            self.logger = logging.getLogger(name=self.__class__.__name__)
            self.logger.setLevel(settings.get("LOG_LEVEL", "DEBUG"))
