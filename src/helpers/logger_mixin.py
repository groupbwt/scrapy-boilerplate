import logging

from scrapy.utils.project import get_project_settings


class LoggerMixin:
    def __init__(self, logger=None, settings=None):
        if logger:
            self.logger = logger
        else:
            if not settings:
                settings = get_project_settings()

            self.logger = logging.getLogger(name=self.__class__.__name__)
            self.logger.setLevel(settings.get('LOG_LEVEL', 'DEBUG'))
