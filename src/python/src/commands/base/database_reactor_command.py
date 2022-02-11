from abc import ABC
from typing import Any, Union

from MySQLdb.cursors import DictCursor
from sqlalchemy.dialects import mysql
from sqlalchemy.sql.base import Executable as SQLAlchemyExecutable
from twisted.enterprise.adbapi import Transaction, ConnectionPool
from twisted.internet.defer import Deferred

from commands.base import BaseReactorCommand


class DatabaseReactorCommand(BaseReactorCommand, ABC):
    db_connection_pool: ConnectionPool

    def init(self):
        self.db_connection_pool = ConnectionPool(
            "MySQLdb",
            host=self.settings.get("DB_HOST"),
            port=self.settings.getint("DB_PORT"),
            user=self.settings.get("DB_USERNAME"),
            passwd=self.settings.get("DB_PASSWORD"),
            db=self.settings.get("DB_DATABASE"),
            charset="utf8mb4",
            use_unicode=True,
            cursorclass=DictCursor,
            cp_reconnect=True,
        )

    def execute(self, args: list, opts: list) -> Deferred:
        query: Deferred = self.db_connection_pool.runInteraction(self.process_message, {})
        return query

    def process_message(self, transaction: Transaction, message_body: Any):
        stmt = self.build_stmt(message_body)
        if isinstance(stmt, SQLAlchemyExecutable):
            stmt_compiled = stmt.compile(
                dialect=mysql.dialect(), compile_kwargs={"literal_binds": True}
            )
            transaction.execute(str(stmt_compiled))
        else:
            transaction.execute(stmt)
        return True

    def build_stmt(self, message_body: Any) -> Union[SQLAlchemyExecutable, str]:
        raise NotImplementedError('"build_stmt" method must be overridden')
