import csv
import datetime
import logging
from datetime import date
from os import path

from MySQLdb.cursors import DictCursor
from scrapy.commands import ScrapyCommand
from sqlalchemy import select
from sqlalchemy.sql import update
from sqlalchemy.dialects.mysql import dialect
from sqlalchemy.sql.base import Executable as SQLAlchemyExecutable
from scrapy.utils.project import get_project_settings
from twisted.enterprise import adbapi
from twisted.internet import reactor, defer


class BaseCSVExporter(ScrapyCommand):
    def __init__(self, table=None):
        super().__init__()
        self.table = table
        self.project_settings = get_project_settings()
        self.logger = logging.getLogger(BaseCSVExporter.__class__.__name__)
        self.file_timestamp_format = '%Y%b%d%H%M%S'
        self.export_date_column = 'sent_to_customer'
        self.chunk_size = 1000
        self.exclude = []
        self.headers = []
        self.file_path = None
        self.filename_prefix = None
        self.filename_postfix = None

    def short_desc(self):
        return 'Abstract command for export into CSV'

    def add_options(self, parser):
        super().add_options(parser)

    def execute(self, _args, opts):
        self.init_db_connection_pool()
        self.logger.debug('Connection established.')
        reactor.callFromThread(self.produce_data)

    def produce_data(self, _result=None):
        d = self.db_connection_pool.runInteraction(self.get_data, self.chunk_size)
        d.addCallback(self.export).addErrback(self._on_data_export_error)

    def get_data(self, transaction, chunk_size=None):
        if chunk_size is None:
            chunk_size = self.chunk_size
        stmt = self.build_select_query_stmt(chunk_size)
        if isinstance(stmt, SQLAlchemyExecutable):
            stmt_compiled = stmt.compile(compile_kwargs={"literal_binds": True}, dialect=dialect())
            transaction.execute(str(stmt_compiled))
        if chunk_size == 1:
            return transaction.fetchone()
        return transaction.fetchall()

    def export(self, rows):
        if not rows:
            self.logger.debug('Export finished: nothing found.')
            reactor.stop()
        else:
            if self.chunk_size == 1:
                rows = [rows]
            else:
                rows = list(rows)
            rows = self.exclude_columns(rows)
            self.get_headers(rows[0])
            self.get_file_path()
            self.save(rows)
            deferred_interactions = []
            for row in rows:
                deferred_interactions.append(self.db_connection_pool.runInteraction(self.update, row))
            deferred_list = defer.DeferredList(deferred_interactions, consumeErrors=True)
            deferred_list.addCallback(self._on_row_update_completed)
            deferred_list.addErrback(self._on_row_update_error)

    def save(self, rows):
        with open(self.file_path, 'a', encoding='utf-8') as file:
            self.logger.debug(f'Exporting to {self.file_path}...')
            writer = csv.DictWriter(file, fieldnames=self.headers)
            writer.writerows(rows)

    def init_db_connection_pool(self):
        self.db_connection_pool = adbapi.ConnectionPool(
            "MySQLdb",
            host=self.project_settings.get("DB_HOST"),
            port=self.project_settings.getint("DB_PORT"),
            user=self.project_settings.get("DB_USERNAME"),
            passwd=self.project_settings.get("DB_PASSWORD"),
            db=self.project_settings.get("DB_DATABASE"),
            charset="utf8mb4",
            use_unicode=True,
            cursorclass=DictCursor,
            cp_reconnect=True,
        )

    def build_select_query_stmt(self, chunk_size):
        return select(self.table).limit(chunk_size).where(self.table.sent_to_customer == None)

    def update(self, transaction, row):
        stmt = self.build_update_query_stmt(row)
        if isinstance(stmt, SQLAlchemyExecutable):
            stmt_compiled = stmt.compile(compile_kwargs={'literal_binds': True})
            transaction.execute(str(stmt_compiled))

    def build_update_query_stmt(self, row):
        export_date = {self.export_date_column: date.today().strftime('%Y-%m-%d')}
        update_date_stmt = update(self.table).values(**export_date)
        return update_date_stmt.where(self.table.id == row['id'])

    def get_headers(self, row):
        if not self.headers:
            self.headers = row.keys()

    def get_file_path(self):
        if not self.file_path:
            export_path = path.join(path.abspath('.'), 'storage')
            file_name = datetime.datetime.now().strftime(self.file_timestamp_format)
            file_name = self.add_prefix(file_name)
            file_name = self.add_postfix(file_name)
            file_name += '.csv'
            self.file_path = path.join(export_path, file_name)

    def exclude_columns(self, rows):
        if self.exclude:
            for column in self.exclude:
                for row in rows:
                    del row[column]
            return rows
        return rows

    def run(self, args, opts):
        if not self.table:
            raise ValueError(f"{type(self).__name__} must have a table")
        reactor.callFromThread(self.execute, args, opts)
        reactor.run()

    def add_prefix(self, file):
        if self.filename_prefix:
            return self.filename_prefix + file
        return file

    def add_postfix(self, file):
        if self.filename_postfix:
            return file + self.filename_postfix
        return file

    def _on_data_export_error(self, failure):
        self.logger.error("failure: {}".format(failure.getErrorMessage()))
        failure.trap(Exception)

    def _on_row_update_completed(self, _result=None):
        reactor.callFromThread(self.produce_data)

    def _on_row_update_error(self, failure):
        self.logger.error("failure: {}".format(failure.getErrorMessage()))
        failure.trap(Exception)
