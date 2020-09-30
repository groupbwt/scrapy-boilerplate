from datetime import datetime


class Task(object):
    def __init__(self):
        self.body = None
        self.id = None
        self._is_empty = True
        self._in_process = False

    def set(self, row):
        if not self.is_empty:
            raise Exception("Task is not empty. Please remove old task before set new task!")
        self.body = row
        self.id = datetime.now().timestamp()
        self._is_empty = False

    def remove(self):
        self.id = None
        self.body = None
        self._is_empty = True
        self._in_process = False

    def set_in_process(self):
        self._in_process = True

    def is_empty(self):
        return self._is_empty

    def set_not_in_process(self):
        self._in_process = False

    def in_process(self):
        return self._in_process

    def __repr__(self):
        return dict({"body": self.body, "id": self.id}).__repr__()

    def get(self):
        return {"id": self.id, "body": self.body}
