import logging

from MySQLdb.cursors import DictCursor
from scrapy.exceptions import NotConfigured
from sqlalchemy.dialects import mysql
from twisted.enterprise import adbapi
from sqlalchemy.sql.base import Executable as SQLAlchemyExecutable
from sqlalchemy.dialects.mysql import insert


class BaseDBPipeline:
    """Base pipeline for saving items direct to database,
    for correct work it must be inherited and its table property must be overridden"""
    table = None

    def __init__(self, project_settings):
        self.project_settings = project_settings
        self.logger = logging.getLogger(self.__class__.__name__)
        self.db_connection_pool = None
        self.db_api = 'MySQLdb'
        self.charset = 'utf8mb4'
        if not getattr(self, 'table', None):
            raise NotConfigured('Table attribute is not set for DB pipeline.')

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings)

    def open_spider(self, spider):
        self.db_connection_pool = adbapi.ConnectionPool(
            self.db_api,
            host=self.project_settings.get("DB_HOST"),
            port=self.project_settings.getint("DB_PORT"),
            user=self.project_settings.get("DB_USERNAME"),
            passwd=self.project_settings.get("DB_PASSWORD"),
            db=self.project_settings.get("DB_DATABASE"),
            charset=self.charset,
            use_unicode=True,
            cursorclass=DictCursor,
            cp_reconnect=True,
        )
        self.logger.debug('Connection with database established.')

    def process_item(self, item, spider):
        self.db_connection_pool.runInteraction(self.save_item, item)
        return item

    def save_item(self, transaction, item):
        stmt = self.build_insert_update_query_stmt(item)
        if isinstance(stmt, SQLAlchemyExecutable):
            stmt_compiled = stmt.compile(dialect=mysql.dialect(), compile_kwargs={'literal_binds': False})
            transaction.execute(str(stmt_compiled), tuple(stmt_compiled.params.values()))
            self.logger.debug('Item was successfully saved to database.')

    def build_insert_update_query_stmt(self, item):
        """If there are fields not to be saved it is possible to override this method"""
        stmt = insert(self.table).values(**item)
        return stmt.on_duplicate_key_update(**stmt.inserted)
