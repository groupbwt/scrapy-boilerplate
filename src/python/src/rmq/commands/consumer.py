import functools
import json
import logging
from enum import Enum
from optparse import OptionValueError

import pika
from MySQLdb import OperationalError
from MySQLdb.cursors import DictCursor
from scrapy.commands import ScrapyCommand
from scrapy.utils.log import configure_logging
from scrapy.utils.project import get_project_settings
from sqlalchemy.dialects import mysql
from sqlalchemy.sql.base import Executable as SQLAlchemyExecutable
from twisted.enterprise import adbapi
from twisted.internet import reactor

from rmq.connections import PikaSelectConnection
from rmq.utils import RMQConstants, RMQDefaultOptions
from rmq.utils.decorators import call_once


class Consumer(ScrapyCommand):
    class CommandModes(Enum):
        ACTION = "action"
        WORKER = "worker"
        DEFAULT = ACTION

    _DEFAULT_CHECK_INTERACT_READY_DELAY = 3  # seconds
    _DEFAULT_PREFETCH_COUNT = 4

    def __init__(self):
        super().__init__()
        self.project_settings = get_project_settings()
        self.logger = logging.getLogger(Consumer.__class__.__name__)

        self.action_modes = [
            Consumer.CommandModes.ACTION.value,
            Consumer.CommandModes.WORKER.value,
        ]
        self.mode = Consumer.CommandModes.DEFAULT.value
        self.prefetch_count = self._DEFAULT_PREFETCH_COUNT

        self.delivery_tag_meta_key = RMQConstants.DELIVERY_TAG_META_KEY.value
        self.msg_body_meta_key = RMQConstants.MSG_BODY_META_KEY.value

        self.queue_name = None

        self.rmq_connection = None
        self._can_interact = False
        self._can_get_next_message = False

        self.db_connection_pool = None

        self.check_interact_ready_delay = Consumer._DEFAULT_CHECK_INTERACT_READY_DELAY

    def set_logger(self, name: str = "COMMAND", level: str = "DEBUG"):
        self.logger = logging.getLogger(name=name)
        self.logger.setLevel(level)
        configure_logging()
        logging.getLogger("pika").setLevel(self.project_settings.get("PIKA_LOG_LEVEL", "WARNING"))

    def add_options(self, parser):
        ScrapyCommand.add_options(self, parser)
        parser.add_option(
            "-q",
            "--queue",
            type="str",
            dest="queue_name",
            help="Queue name to consume messages",
            action="callback",
            callback=self.queue_option_callback,
        )
        parser.add_option(
            "-m",
            "--mode",
            type="choice",
            choices=self.action_modes,
            default="action",
            dest="mode",
            help="Command run mode: action for one time execution and exit or worker",
        )
        parser.add_option(
            "-p",
            "--prefetch_count",
            type="int",
            default=None,
            dest="prefetch_count",
            help="RabbitMQ consumer prefetch count setting",
        )

    def queue_option_callback(self, _option, opt, value, parser):
        if value is not None and len(str(value).strip()):
            self.queue_name = value
            setattr(parser.values, "queue_name", value)
        else:
            raise OptionValueError(f"Option {opt} has incorrect value provided")

    def init_queue_name(self, opts):
        queue_name = getattr(opts, "queue_name", None)
        if queue_name is None:
            queue_name = self.queue_name
        if queue_name is None:
            raise NotImplementedError(
                "queue name must be provided with options or override this method to return it"
            )
        self.queue_name = queue_name
        return queue_name

    def init_prefetch_count(self, opts):
        mode = getattr(opts, "mode", None)
        if mode == Consumer.CommandModes.ACTION.value:
            self.prefetch_count = 1
        thread_pool = reactor.getThreadPool()
        if thread_pool and hasattr(thread_pool, "max"):
            self.prefetch_count = int(thread_pool.max - (thread_pool.max % 4))
        if opts.prefetch_count is not None and opts.prefetch_count > 0:
            self.prefetch_count = opts.prefetch_count
        return self.prefetch_count

    def init_db_connection_pool(self):
        """In case of using non mysql database or if pymysql is preferred this method must be overridden
        Also self.process_message method must be overridden in case of replacing database engine
        """
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

    def execute(self, _args, opts):
        self.init_queue_name(opts)
        self.init_prefetch_count(opts)
        self.mode = opts.mode

        self.init_db_connection_pool()

        parameters = pika.ConnectionParameters(
            host=self.project_settings.get("RABBITMQ_HOST"),
            port=int(self.project_settings.get("RABBITMQ_PORT")),
            virtual_host=self.project_settings.get("RABBITMQ_VIRTUAL_HOST"),
            credentials=pika.credentials.PlainCredentials(
                username=self.project_settings.get("RABBITMQ_USERNAME"),
                password=self.project_settings.get("RABBITMQ_PASSWORD"),
            ),
            heartbeat=RMQDefaultOptions.CONNECTION_HEARTBEAT.value,
        )
        reactor.callInThread(self.connect, parameters, self.queue_name)

    def on_basic_get_message(self, message):
        delivery_tag = message.get("method").delivery_tag
        ack_cb = nack_cb = None
        if isinstance(self.rmq_connection.connection, pika.SelectConnection):
            ack_cb = call_once(
                functools.partial(
                    self.rmq_connection.connection.ioloop.add_callback_threadsafe,
                    functools.partial(
                        self.rmq_connection.acknowledge_message, delivery_tag=delivery_tag
                    ),
                )
            )
            nack_cb = call_once(
                functools.partial(
                    self.rmq_connection.connection.ioloop.add_callback_threadsafe,
                    functools.partial(
                        self.rmq_connection.negative_acknowledge_message, delivery_tag=delivery_tag
                    ),
                )
            )

        message_body = json.loads(message["body"])

        d = self.db_connection_pool.runInteraction(self.process_message, message_body)
        d.addCallback(
            self.on_message_processed, ack_callback=ack_cb, nack_callback=nack_cb,
        ).addErrback(self.on_message_process_failure, nack_callback=nack_cb).addBoth(
            self._check_mode
        )

        self._can_get_next_message = True

    def process_message(self, transaction, message_body):
        """If processing message task requires several queries to db or single query has extreme difficulty
        then this method could be overridden.
        In this case using of self.build_message_store_stmt method is not required
        and could be overridden with pass statement
        This method must return boolean (or interpretable as boolean) result which determines to ack or nack message
        Also this method must be overridden in case of target database changed from mysql
        """
        stmt = self.build_message_store_stmt(message_body)
        if isinstance(stmt, SQLAlchemyExecutable):
            stmt_compiled = stmt.compile(
                dialect=mysql.dialect(), compile_kwargs={"literal_binds": True}
            )
            transaction.execute(str(stmt_compiled))
            # transaction.execute(str(stmt_compiled), stmt_compiled.params)
        else:
            transaction.execute(stmt)
        return True

    def build_message_store_stmt(self, message_body):
        """If processing message task requires several queries to db or single query has extreme difficulty
        then this self.process_message method could be overridden.
        In this case using of self.build_message_store_stmt method is not required
        and could be overridden with pass statement

        Example:
        message_body['status'] = TaskStatusCodes.SUCCESS.value
        del message_body['created_at']
        del message_body['updated_at']
        stmt = insert(SearchEngineQuery)
        stmt = stmt.on_duplicate_key_update({
            'status': stmt.inserted.status
        }).values(message_body)
        return stmt
        """
        raise NotImplementedError

    @staticmethod
    def _compile_and_stringify_statement(stmt):
        return str(stmt.compile(compile_kwargs={"literal_binds": True}, dialect=mysql.dialect()))

    def on_message_processed(self, message_store_result, ack_callback=None, nack_callback=None):
        if message_store_result:
            if callable(ack_callback):
                ack_callback()
        else:
            if callable(nack_callback):
                nack_callback()

    def on_message_process_failure(self, failure, nack_callback=None):
        failure.trap(Exception)
        self.logger.error("failure: {}".format(failure))
        if callable(nack_callback):
            nack_callback()
        if failure.check(NotImplementedError):
            self.logger.critical("Required method is not implemented. Shutting down...")
            reactor.callLater(0, self.crawler_process._graceful_stop_reactor)
        if failure.check(OperationalError):
            if "1065" in failure.getErrorMessage():
                self.logger.critical(
                    "Got empty query to DB. Incorrect implementation. Shutting down..."
                )
                reactor.callLater(0, self.crawler_process._graceful_stop_reactor)

    def _check_mode(self, arg):
        if self.mode == Consumer.CommandModes.ACTION.value:
            reactor.callLater(0, self.crawler_process._graceful_stop_reactor)
        return arg

    def on_message_consumed(self, message):
        self.on_basic_get_message(message)

    def on_basic_get_empty(self):
        self.logger.debug("got empty response")
        self._can_get_next_message = True

    def set_connection_handle(self, connection):
        self.rmq_connection = connection
        self._can_interact = True
        self._can_get_next_message = True

    def set_can_interact(self, can_interact):
        self._can_interact = can_interact
        self._can_get_next_message = can_interact

    def connect(self, parameters, queue_name):
        c = PikaSelectConnection(
            parameters,
            queue_name,
            owner=self,
            options={
                "enable_delivery_confirmations": False,
                "prefetch_count": self.prefetch_count,
            },
            is_consumer=True,
        )
        c.run()

    def run(self, args, opts):
        self.set_logger(self.__class__.__name__, self.project_settings.get("LOG_LEVEL"))
        reactor.callLater(0, self.execute, args, opts)
        reactor.run()
