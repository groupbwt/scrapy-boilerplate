from scrapy import signals
import logging
from twisted.internet import reactor, task, defer
from twisted.enterprise import adbapi
from scrapy.utils.project import get_project_settings
from MySQLdb.cursors import DictCursor
from sqlalchemy.sql.base import Executable as SQLAlchemyExecutable
from sqlalchemy.dialects import mysql
from MySQLdb import OperationalError
from scrapy.exceptions import DontCloseSpider
from copy import deepcopy
from scrapy import Request
from rmq.utils.task_status_codes import TaskStatusCodes

logger = logging.getLogger(__name__)


class DirectDBConnectionExtension:
    _RELIEVE_DELAY = 3
    THRESHOLD_SIZE = 1500

    @classmethod
    def from_crawler(cls, crawler):
        o = cls(crawler)
        """Subscribe to signals which controls opening and shutdown hooks/behaviour"""
        crawler.signals.connect(o.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(o.spider_closed, signal=signals.spider_closed)
        crawler.signals.connect(o.spider_idle, signal=signals.spider_idle)

        """Subscribe to signals which controls requests scheduling and responses or error retrieving"""
        crawler.signals.connect(o.on_spider_error, signal=signals.spider_error)

        """Subscribe to signals which controls item processing"""
        crawler.signals.connect(o.on_item_scraped, signal=signals.item_scraped)
        crawler.signals.connect(o.on_item_dropped, signal=signals.item_dropped)
        crawler.signals.connect(o.on_item_error, signal=signals.item_error)

        return o

    def spider_closed(self, spider, reason):
        spider.logger.info(reason)

    def __init__(self, crawler):
        super().__init__()
        self.crawler = crawler
        self.project_settings = get_project_settings()
        self.db_connection_pool = None
        self.can_interact = False
        self.can_next_request = True
        self.task_tag_meta_key = "task_id"
        self.task_body_meta_key = "task_body"

    def spider_opened(self, spider):
        self.__spider = spider
        self.logger = self.__spider.logger
        self.can_interact = False
        logger.setLevel(self.__spider.settings.get("LOG_LEVEL", "INFO"))
        self.db_connection_pool = self.init_db_connection_pool()
        self._relieve_task = task.LoopingCall(self._relieve)
        self._relieve_task.start(self._RELIEVE_DELAY)

    def on_item_scraped(self, item, response, spider):
        if response is not None and spider is not None:
            task_id = self.extract_task_id(response, item)
            if task_id is not None:
                d = self.db_connection_pool.runInteraction(
                    self.save_task_interaction, item, TaskStatusCodes.SUCCESS.value
                )
                d.addCallback(self._on_success_save, spider, task_id).addErrback(self._on_error)

    def _on_success_save(self, _result, spider, task_id):
        spider.task.remove()
        self.logger.debug(f"Task completed success {task_id}. Task removed.")

    def on_item_dropped(self, item, response, exception, spider):
        task_id = self.extract_task_id(response, item)
        if task_id is not None:
            d = self.db_connection_pool.runInteraction(
                self.update_status_task_interaction, item, TaskStatusCodes.DROPPED.value
            )
            d.addCallback(self._on_dropped_save, spider, task_id).addErrback(self._on_error)

    def _on_dropped_save(self, _result, spider, task_id):
        spider.task.remove()
        self.logger.debug(f"Task dropped {task_id}. Task removed.")

    def on_item_error(self, item, response, spider, failure):
        task_id = self.extract_task_id(response, item)
        if task_id is not None:
            d = self.db_connection_pool.runInteraction(
                self.update_status_task_interaction, item, TaskStatusCodes.ERROR.value
            )
            d.addCallback(self._on_error_save, spider, task_id).addErrback(self._on_error)
            self.logger.debug(f"Task error {task_id}. ")

    def on_spider_error(self, failure, response, spider):
        meta = response.meta
        body = meta.get("body")
        if body:
            task_id = meta.get("task_id")
            if task_id:
                d = self.db_connection_pool.runInteraction(
                    self.update_status_task_interaction, body, TaskStatusCodes.ERROR.value
                )
                d.addCallback(self._on_error_save, spider, task_id).addErrback(self._on_error)
                self.logger.debug(f"Task error {task_id}. ")

    def _on_error_save(self, _result, spider, task_id):
        spider.task.remove()
        self.logger.debug(f"Task error finished {task_id}. Task removed.")

    def _on_error(self, failure):
        self.logger.error(f"failure: {failure}")
        failure.trap(Exception)

    def extract_task_id(self, response, item):
        task_id = response.meta.get(self.task_tag_meta_key, None)
        if task_id is None and hasattr(item, self.task_tag_meta_key):
            task_id = getattr(item, self.task_tag_meta_key, None)
        return task_id

    def save_task_interaction(self, transaction, item, status):
        stmt = self.build_task_save_stmt(item, status)
        if isinstance(stmt, SQLAlchemyExecutable):
            stmt_compiled = stmt.compile(compile_kwargs={"literal_binds": True}, dialect=mysql.dialect())
            transaction.execute(str(stmt_compiled))
            # transaction.execute(str(stmt_compiled), stmt_compiled.params)
        else:
            transaction.execute(stmt)

    def build_task_save_stmt(self, item, status):
        raise NotImplemented

    def update_status_task_interaction(self, transaction, item, status):
        stmt = self.build_task_update_status_stmt(item, status)
        if isinstance(stmt, SQLAlchemyExecutable):
            stmt_compiled = stmt.compile(compile_kwargs={"literal_binds": True}, dialect=mysql.dialect())
            transaction.execute(str(stmt_compiled))
            # transaction.execute(str(stmt_compiled), stmt_compiled.params)
        else:
            transaction.execute(stmt)

    def build_task_update_status_stmt(self, item, status):
        """
            update = Update(Table).values({"status":status}).where(Table.id == item["id"])
            return update
        """
        raise NotImplemented

    def _relieve(self):
        if not self.__spider.task.is_empty() and not self.__spider.task.in_process():
            self.__spider.task.set_in_process()
            relieve_task = self.__spider.task.get()
            body = relieve_task["body"]
            task_id = relieve_task["id"]
            prepared_request = self.__spider.next_request(task_id, body)
            if isinstance(prepared_request, Request):
                prepared_request_meta = deepcopy(prepared_request.meta)
                should_replace_meta = False
                if self.task_tag_meta_key not in prepared_request_meta.keys():
                    prepared_request_meta[self.task_tag_meta_key] = task_id
                    should_replace_meta = True
                if self.task_body_meta_key not in prepared_request_meta.keys():
                    prepared_request_meta[self.task_body_meta_key] = body
                    should_replace_meta = True
                if should_replace_meta:
                    prepared_request = prepared_request.replace(meta=prepared_request_meta)
                if prepared_request.dont_filter is False:
                    prepared_request = prepared_request.replace(dont_filter=True)
                self.crawler.engine.crawl(prepared_request, spider=self.__spider)

    def produce_tasks(self):
        self.check_interact()
        if self.can_interact:
            d = self.db_connection_pool.runInteraction(self.process_message)
            d.addCallback(self.process_tasks).addErrback(self.on_get_tasks_error)
        else:
            reactor.callLater(2, self.produce_tasks)

    def check_interact(self):
        if not self.db_connection_pool.running:
            self.can_interact = False
            logger.warning(f"DB connection pool not running.{self.__spider = }")
        elif not hasattr(self.__spider, "next_request"):
            raise Exception("Spider has no next_request method")
        elif not self.__spider.task.is_empty():
            self.can_interact = False
        else:
            self.can_interact = True

    def spider_idle(self, spider):
        reactor.callLater(2, self.produce_tasks)
        raise DontCloseSpider

    def process_tasks(self, row):
        if bool(row):
            self.__spider.task.set(row)
        reactor.callLater(1, self.produce_tasks)

    def process_message(self, transaction):
        stmt = self.build_message_store_stmt()
        if isinstance(stmt, SQLAlchemyExecutable):
            stmt_compiled = stmt.compile(
                dialect=mysql.dialect(), compile_kwargs={"literal_binds": True}
            )
            transaction.execute(str(stmt_compiled))
            # transaction.execute(str(stmt_compiled), stmt_compiled.params)
        else:
            transaction.execute(stmt)
        return transaction.fetchone()

    def build_message_store_stmt(self):
        raise NotImplemented

    def init_db_connection_pool(self):
        """In case of using non mysql database or if pymysql is preferred this method must be overridden
        """
        db_connection_pool = adbapi.ConnectionPool(
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
        return db_connection_pool

    def on_get_tasks_error(self, failure):
        self.logger.error("failure: {}".format(failure))
        if failure.check(NotImplementedError):
            self.logger.critical("Required method is not implemented. Shutting down...")
            reactor.callLater(0, self.crawler._graceful_stop_reactor)
        if failure.check(OperationalError):
            if "1065" in failure.getErrorMessage():
                self.logger.error(
                    "Got empty query to DB. Incorrect implementation. Shutting down..."
                )
                reactor.callLater(0, self.crawler._graceful_stop_reactor)
        failure.trap(Exception)