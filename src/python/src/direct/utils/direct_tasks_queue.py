from .direct_task import DirectTask
from typing import Union
import logging


class DirectTasksQueue(object):
    def __init__(self):
        self.tasks: list = []
        self.length: int = 0
        self.total_handle: int = 0
        self.total_dropped: int = 0
        self.total_success: int = 0
        self.total_error: int = 0
        self._in_process: bool = False

    def add_task(self, task: DirectTask) -> None:
        self.tasks.append(task)
        self.length += 1
        self.inc_total()

    def __len__(self) -> int:
        return len(self.tasks)

    def get_task(self) -> Union[DirectTask, None]:
        if not self.is_empty():
            task = self.tasks[self.length - 1]
            self._in_process = True
            return task
        else:
            raise Exception("Try to get task but queue is empty")

    def __repr__(self) -> str:
        return self.tasks.__repr__()

    def is_empty(self) -> int:
        return self.length < 1

    def remove_task(self, task_id: str) -> Union[DirectTask, None]:
        for i, task in enumerate(self.tasks):
            if task_id == task.id:
                target_task = self.tasks[i]
                del self.tasks[i]
                self.length -= 1
                self._in_process = False
                return target_task
        logging.warning(f"Task with {task_id=} already removed")

    def in_process(self) -> bool:
        return self._in_process

    def inc_total(self) -> None:
        self.total_handle += 1

    def inc_dropped(self) -> None:
        self.total_dropped += 1

    def inc_error(self) -> None:
        self.total_error += 1

    def inc_success(self) -> None:
        self.total_success += 1
