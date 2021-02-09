from .task import Task


class TaskObserver:
    def __init__(self):
        self.__tasks = {}

    def add_task(self, task: Task):
        delivery_tag = task.delivery_tag
        if delivery_tag in self.__tasks.keys():
            raise ValueError(f"Delivery tag {delivery_tag} is already exists")
        self.__tasks[delivery_tag] = task

    def get_task(self, delivery_tag):
        return self.__tasks.get(delivery_tag, None)

    def get_all(self):
        return self.__tasks

    def remove_task(self, delivery_tag):
        try:
            del self.__tasks[delivery_tag]
        except KeyError:
            pass

    def current_processing_count(self):
        return len(self.__tasks.keys())

    def is_empty(self):
        return self.current_processing_count() == 0

    def handle_request(self, delivery_tag):
        if delivery_tag not in self.__tasks.keys():
            raise ValueError(f"Delivery tag {delivery_tag} is not exists in observer")
        self.__tasks[delivery_tag].request_scheduled()

    def handle_response(self, delivery_tag, response_code=200):
        try:
            if 200 <= response_code < 300:
                self.__tasks[delivery_tag].success_response_received()
            else:
                self.__tasks[delivery_tag].fail_response_received()
        except KeyError:
            pass

    def handle_item_scheduled(self, delivery_tag):
        if delivery_tag not in self.__tasks.keys():
            raise ValueError(f"Delivery tag {delivery_tag} is not exists in observer")
        self.__tasks[delivery_tag].item_scheduled()

    def handle_item_scraped(self, delivery_tag):
        if delivery_tag not in self.__tasks.keys():
            raise ValueError(f"Delivery tag {delivery_tag} is not exists in observer")
        self.__tasks[delivery_tag].item_scraped_received()

    def handle_item_dropped(self, delivery_tag):
        if delivery_tag not in self.__tasks.keys():
            raise ValueError(f"Delivery tag {delivery_tag} is not exists in observer")
        self.__tasks[delivery_tag].item_dropped_received()

    def handle_item_error(self, delivery_tag):
        if delivery_tag not in self.__tasks.keys():
            raise ValueError(f"Delivery tag {delivery_tag} is not exists in observer")
        self.__tasks[delivery_tag].item_error_received()

    def set_status(self, delivery_tag, status):
        try:
            self.__tasks[delivery_tag].status = status
        except KeyError:
            pass

    def set_exception(self, delivery_tag, exception):
        try:
            self.__tasks[delivery_tag].exception = exception
        except KeyError:
            pass

    def set_should_stop(self, delivery_tag, value):
        try:
            self.__tasks[delivery_tag].should_stop = value
        except KeyError:
            pass
