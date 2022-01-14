from MySQLdb.cursors import DictCursor
from scrapy import signals
from scrapy.exceptions import NotConfigured
from twisted.enterprise import adbapi
from sqlalchemy.sql.base import Executable as SQLAlchemyExecutable
from sqlalchemy.dialects.mysql import insert


class BaseDBPipeline:
    def __init__(self, project_settings):
        self.project_settings = project_settings
        self.db_connection_pool = None
        self.db_api_name = 'MySQLdb'
        self.charset = 'utf8mb4'
        self.table = None

    @classmethod
    def from_crawler(cls, crawler):
        pipeline = cls(crawler.settings)
        crawler.signals.connect(pipeline.spider_opened, signal=signals.spider_opened)
        return pipeline

    def spider_opened(self):
        if not self.table:
            raise NotConfigured('Table attribute is not set for DB pipeline.')
        self.db_connection_pool = adbapi.ConnectionPool(
            self.db_api_name,
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

    def process_item(self, item, spider):
        self.db_connection_pool.runInteraction(self.save_item, item)
        return item

    def save_item(self, transaction, item):
        stmt = self.build_insert_update_query_stmt(item)
        if isinstance(stmt, SQLAlchemyExecutable):
            stmt_compiled = stmt.compile(compile_kwargs={'literal_binds': True})
            transaction.execute(str(stmt_compiled))

    def build_insert_update_query_stmt(self, item):
        stmt = insert(self.table).values(**item)
        return stmt.on_duplicate_key_update(**stmt.inserted)
