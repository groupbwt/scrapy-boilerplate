# -*- coding: utf-8 -*-
from rmq.extensions import RPCTaskConsumer
from rmq.spiders import TaskBaseSpider
from rmq.utils import TaskObserver


class TaskToMultipleResultsSpider(TaskBaseSpider):
    name = "multiple"

    def __init__(self, *args, **kwargs):
        super(TaskToMultipleResultsSpider, self).__init__(*args, **kwargs)
        self.processing_tasks = TaskObserver()
        self.completion_strategy = RPCTaskConsumer.CompletionStrategies.REQUESTS_BASED
