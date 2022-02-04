import csv
import datetime
from datetime import date
from optparse import Values
from os import path
from typing import List, Dict, Union

from MySQLdb.cursors import DictCursor
from sqlalchemy import select, Table
from sqlalchemy.dialects.mysql import dialect
from sqlalchemy.sql import update
from sqlalchemy.sql.base import Executable as SQLAlchemyExecutable
from twisted.enterprise import adbapi
from twisted.enterprise.adbapi import Transaction
from twisted.internet import reactor, defer

from commands.base import BaseCommand


class BaseCSVExporter(BaseCommand):
    table: Table
    file_timestamp_format: str = '%Y%b%d%H%M%S'
    export_date_column: str = 'sent_to_customer'
    file_extension: str = 'csv'
    chunk_size: int = 1000
    excluded_columns: List[str] = []
    specific_columns: List[str] = []
    headers: List[str] = []
    new_mapping: Dict[str, str] = {}
    filename_prefix: str = ''
    filename_postfix: str = ''
    file_path: str = ''
    file_exists: bool = False

    def init(self) -> None:
        if not isinstance(self.table.__table__, Table):
            raise ValueError(f'{type(self).__name__} must have a valid table object')
        self.file_path = self.get_file_path()
        self.init_db_connection_pool()
        self.logger.debug('Connection established.')

    def produce_data(self) -> None:
        d = self.db_connection_pool.runInteraction(self.get_data, self.chunk_size)
        d.addCallback(self.export).addErrback(self._on_data_export_error)

    def get_data(self, transaction: Transaction, chunk_size: int = None) -> Union[tuple, Dict]:
        if chunk_size is None:
            chunk_size = self.chunk_size
        stmt = self.build_select_query_stmt(chunk_size)
        if isinstance(stmt, SQLAlchemyExecutable):
            stmt_compiled = stmt.compile(compile_kwargs={"literal_binds": True}, dialect=dialect())
            transaction.execute(str(stmt_compiled))
        if chunk_size == 1:
            return transaction.fetchone()
        return transaction.fetchall()

    def export(self, rows: Union[tuple, Dict]) -> None:
        if not rows:
            if self.file_exists:
                self.logger.debug(f'Export finished successfully to {path.basename(self.file_path)}.')
            else:
                self.logger.warning('Nothing found')
            reactor.stop()
        else:
            if self.chunk_size == 1:
                rows = [rows]
            else:
                rows = list(rows)
            rows = self.map_columns(rows)
            self.get_headers(rows[0])
            self.save(rows)
            deferred_interactions = []
            for row in rows:
                deferred_interactions.append(self.db_connection_pool.runInteraction(self.update, row))
            deferred_list = defer.DeferredList(deferred_interactions, consumeErrors=True)
            deferred_list.addCallback(self._on_row_update_completed)
            deferred_list.addErrback(self._on_row_update_error)

    def save(self, rows: List[Dict]) -> None:
        with open(self.file_path, 'a', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=self.headers)
            if not self.file_exists:
                writer.writeheader()
                self.file_exists = True
            self.logger.debug(f'Exporting to {self.file_path}...')
            writer.writerows(rows)

    def init_db_connection_pool(self) -> None:
        self.db_connection_pool = adbapi.ConnectionPool(
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

    def build_select_query_stmt(self, chunk_size: int) -> SQLAlchemyExecutable:
        if columns := self.specify_columns():
            return select(*columns).limit(chunk_size).where(self.table.sent_to_customer == None)
        else:
            return select(self.table).limit(chunk_size).where(self.table.sent_to_customer == None)

    def update(self, transaction: Transaction, row: Dict) -> None:
        stmt = self.build_update_query_stmt(row)
        if isinstance(stmt, SQLAlchemyExecutable):
            stmt_compiled = stmt.compile(compile_kwargs={'literal_binds': True})
            transaction.execute(str(stmt_compiled))

    def build_update_query_stmt(self, row: Dict) -> SQLAlchemyExecutable:
        export_date = {self.export_date_column: date.today().strftime('%Y-%m-%d')}
        update_date_stmt = update(self.table).values(**export_date)
        return update_date_stmt.where(self.table.id == row['id'])

    def map_columns(self, rows: List[Dict]) -> List[Dict]:
        if self.new_mapping:
            for row in rows:
                for old_name, new_name in self.new_mapping.items():
                    row[new_name] = row.pop(old_name)
            return rows
        return rows

    def specify_columns(self) -> Union[List, None]:
        if self.specific_columns:
            columns = []
            for column_name in self.specific_columns:
                if column := getattr(self.table, column_name, None):
                    columns.append(column)
                else:
                    raise ValueError(f'Column "{column_name}" is not found in the table.')
            if self.table.__table__.columns.id not in columns:
                columns.insert(0, self.table.__table__.columns.id)
            return columns
        elif self.excluded_columns:
            columns = []
            for column in self.table.__table__.columns:
                if column.name not in self.excluded_columns:
                    columns.append(column)
            if self.table.__table__.columns.id not in columns:
                raise ValueError('Column "id" cannot be excluded!')
            return columns
        return None

    def get_headers(self, row: Dict) -> None:
        if not self.headers:
            self.headers = list(row.keys())

    def get_file_path(self, timestamp_format=None, prefix=None, postfix=None, extension=None):
        if timestamp_format is None:
            timestamp_format = self.file_timestamp_format
        if prefix is None:
            prefix = self.filename_prefix
        if postfix is None:
            postfix = self.filename_postfix
        if extension is None:
            extension = self.file_extension
        export_path = path.join(path.abspath('..'), 'storage')
        file_name = f'{prefix}{datetime.datetime.now().strftime(timestamp_format)}{postfix}.{extension}'
        return path.join(export_path, file_name)

    def run(self, args: Values, opts: List) -> None:
        reactor.callFromThread(self.produce_data)
        reactor.run()

    def add_postfix(self, file):
        return file + self.filename_postfix

    def _on_row_update_completed(self, _result=None):
        reactor.callFromThread(self.produce_data)

    def _on_data_export_error(self, failure):
        self.logger.error("failure: {}".format(failure.getErrorMessage()))
        failure.trap(Exception)

    def _on_row_update_error(self, failure):
        self.logger.error("failure: {}".format(failure.getErrorMessage()))
        failure.trap(Exception)
