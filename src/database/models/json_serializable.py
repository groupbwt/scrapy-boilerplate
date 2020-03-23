# -*- coding: utf-8 -*-


class JSONSerializable:
    def _serialize(self, value: object) -> object:
        if type(value) not in (int, float, bool, type(None)):
            return str(value)

        return value

    def as_dict(self) -> dict:
        return {c.name: self._serialize(getattr(self, c.name)) for c in self.__table__.columns}
