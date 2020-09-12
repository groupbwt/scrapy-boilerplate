# -*- coding: utf-8 -*-
from sqlalchemy import Table


class JSONSerializable:
    __table__: Table = None

    @staticmethod
    def _serialize(value: object) -> object:
        if type(value) not in (int, float, bool, type(None)):
            return str(value)

        return value

    def as_dict(self) -> dict:
        return {c.name: self._serialize(getattr(self, c.name)) for c in self.__table__.columns}
