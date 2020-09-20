import json

from rmq.exceptions import ConsumedDataCorrupted


class Task:
    def __init__(self, consumed_data, ack_callback=None, nack_callback=None):
        if not isinstance(consumed_data, dict):
            raise ConsumedDataCorrupted("Consumed data is not a dict")
        if consumed_data.get("method", None) is None:
            raise ConsumedDataCorrupted('Consumed data has no "method" key')
        if consumed_data.get("properties", None) is None:
            raise ConsumedDataCorrupted('Consumed data has no "properties" key')
        if consumed_data.get("body", None) is None:
            raise ConsumedDataCorrupted('Consumed data has no "body" key')
        self.__consumed_data = consumed_data

        self.payload = json.loads(self.__consumed_data.get("body"))
        self.delivery_tag = self.__consumed_data.get("method").delivery_tag
        self.reply_to = self.__consumed_data.get("properties").reply_to
        self.status = 1
        self.exception = None

        self.__ack_callback = (
            ack_callback
            if ack_callback is not None and callable(ack_callback)
            else self.__empty_callback
        )
        self.__nack_callback = (
            nack_callback
            if nack_callback is not None and callable(nack_callback)
            else self.__empty_callback
        )

        self.scheduled_requests = 0
        self.success_responses = 0
        self.failed_responses = 0

        self.scheduled_items = 0
        self.scraped_items = 0
        self.dropped_items = 0
        self.error_items = 0

        self.should_stop = False

    def __empty_callback(self):
        pass

    def __disable_callbacks(self):
        self.__ack_callback = self.__empty_callback
        self.__nack_callback = self.__empty_callback

    def ack(self):
        self.__ack_callback()
        self.__disable_callbacks()

    def nack(self):
        self.__nack_callback()
        self.__disable_callbacks()

    def request_scheduled(self):
        self.scheduled_requests += 1

    def success_response_received(self):
        self.success_responses += 1

    def fail_response_received(self):
        self.failed_responses += 1

    def total_responses(self):
        return self.success_responses + self.failed_responses

    def item_scheduled(self):
        self.scheduled_items += 1

    def item_scraped_received(self):
        self.scraped_items += 1

    def item_dropped_received(self):
        self.dropped_items += 1

    def item_error_received(self):
        self.error_items += 1

    def total_items(self):
        return self.scraped_items + self.dropped_items + self.error_items

    def is_items_completed(self, ignore_zero=True):
        if ignore_zero is True and self.scheduled_items == 0:
            return False
        return self.scheduled_items == (self.scraped_items + self.dropped_items + self.error_items)

    def is_requests_completed(self, ignore_zero=True):
        if ignore_zero is True and self.scheduled_requests == 0:
            return False
        return self.scheduled_requests == (self.success_responses + self.failed_responses)

    def __repr__(self):
        return json.dumps(
            {
                "scheduled": self.scheduled_requests,
                "total_responses": self.total_responses(),
                "success_requests": self.success_responses,
                "failed_reqiests": self.failed_responses,
                "scheduled_items": self.scheduled_items,
                "total_items": self.total_items(),
                "success_items": self.scraped_items,
                "failed_items": self.dropped_items + self.error_items,
            }
        )
