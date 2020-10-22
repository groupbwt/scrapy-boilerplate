from hashlib import sha256


class DirectTask(object):
    def __init__(self, row: dict) -> None:
        if not isinstance(row, dict):
            raise TypeError("Task body must be a dict type.")
        self.body: dict = row
        self.id: str = sha256(str(row).encode()).hexdigest()

    def __repr__(self) -> str:
        return dict({"body": self.body, "id": self.id}).__repr__()
