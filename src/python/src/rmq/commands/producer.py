import datetime
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
from sqlalchemy.sql.base import Executable as SQLAlchemyExecutable
from sqlalchemy.dialects import mysql
from twisted.enterprise import adbapi
from twisted.internet import reactor, defer

from rmq.connections import PikaSelectConnection
from rmq.utils import RMQConstants, RMQDefaultOptions, TaskStatusCodes


class Producer(ScrapyCommand):
    class CommandModes(Enum):
        ACTION = "action"
        WORKER = "worker"
        DEFAULT = ACTION

    _DEFAULT_CHUNK_SIZE = 100
    _DEFAULT_CHECK_INTERACT_READY_DELAY = 3  # seconds

    def __init__(self):
        super().__init__()
        self.project_settings = get_project_settings()
        self.logger = logging.getLogger(Producer.__class__.__name__)

        self.action_modes = [
            Producer.CommandModes.ACTION.value,
            Producer.CommandModes.WORKER.value,
        ]
        self.mode = Producer.CommandModes.DEFAULT.value
        self.chunk_size = Producer._DEFAULT_CHUNK_SIZE

        self.delivery_tag_meta_key = RMQConstants.DELIVERY_TAG_META_KEY.value
        self.msg_body_meta_key = RMQConstants.MSG_BODY_META_KEY.value

        self.task_queue_name = None
        self.reply_to_queue_name = None

        self.rmq_connection = None
        self._can_interact = False

        self.db_connection_pool = None

        self.check_interact_ready_delay = Producer._DEFAULT_CHECK_INTERACT_READY_DELAY

    def set_logger(self, name: str = "COMMAND", level: str = "DEBUG"):
        self.logger = logging.getLogger(name=name)
        self.logger.setLevel(level)
        configure_logging()
        logging.getLogger("pika").setLevel(self.project_settings.get("PIKA_LOG_LEVEL", "WARNING"))

    def add_options(self, parser):
        ScrapyCommand.add_options(self, parser)
        parser.add_option(
            "-t",
            "--task_queue",
            type="str",
            dest="task_queue_name",
            help="Queue name to produce tasks",
            action="callback",
            callback=self.task_queue_option_callback,
        )
        parser.add_option(
            "-r",
            "--reply_to_queue",
            type="str",
            dest="reply_to_queue_name",
            help="Queue name to return replies",
            action="callback",
            callback=self.reply_to_queue_option_callback,
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
            "-c",
            "--chunk_size",
            type="int",
            default=Producer._DEFAULT_CHUNK_SIZE,
            dest="chunk_size",
            help="number of tasks to produce at one iteration",
        )

    def task_queue_option_callback(self, _option, opt, value, parser):
        if value is not None and len(str(value).strip()):
            self.task_queue_name = value
            setattr(parser.values, "task_queue_name", value)
        else:
            raise OptionValueError(f"Option {opt} has incorrect value provided")

    def reply_to_queue_option_callback(self, _option, _opt, value, parser):
        if value is not None and len(str(value).strip()):
            self.reply_to_queue_name = value
            setattr(parser.values, "reply_to_queue_name", value)

    def init_task_queue_name(self, opts):
        task_queue_name = getattr(opts, "task_queue_name", None)
        if task_queue_name is None:
            task_queue_name = self.task_queue_name
        if task_queue_name is None:
            raise NotImplementedError(
                "task queue name must be provided with options or override this method to return it"
            )
        self.task_queue_name = task_queue_name
        return task_queue_name

    def init_replies_queue_name(self, opts):
        reply_to_queue_name = getattr(opts, "reply_to_queue_name", None)
        if reply_to_queue_name is None:
            reply_to_queue_name = self.reply_to_queue_name
        self.reply_to_queue_name = reply_to_queue_name
        return reply_to_queue_name

    def init_db_connection_pool(self):
        """In case of using non mysql database or if pymysql is preferred this method must be overridden"""
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
        self.init_task_queue_name(opts)
        self.init_replies_queue_name(opts)
        self.mode = opts.mode
        self.chunk_size = opts.chunk_size

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
        reactor.callInThread(self.connect, parameters, self.task_queue_name)
        reactor.callLater(self.check_interact_ready_delay, self.produce_tasks)

    def produce_tasks(self, is_message_count_validated=False):
        if self._can_interact is False:
            """Wait until connection is ready to interaction"""
            reactor.callLater(self.check_interact_ready_delay, self.produce_tasks)
            return

        """check current queue ready messages count (queue size)"""
        if is_message_count_validated is False:
            cb = functools.partial(
                self.rmq_connection.get_ready_messages_count,
                self.task_queue_name,
                functools.partial(reactor.callFromThread, self.validate_queue_message_count),
            )
            self.rmq_connection.connection.ioloop.add_callback_threadsafe(cb)
            return

        """get chunk of records from db which represents tasks and produce to queue"""
        d = self.db_connection_pool.runInteraction(self.get_tasks_interaction, self.chunk_size)
        d.addCallback(self.process_tasks).addErrback(self.on_get_tasks_error)

    def validate_queue_message_count(self, message_count=None):
        delay_timeout = self._delay(message_count)
        reactor.callLater(delay_timeout, self.produce_tasks, True)

    def _delay(self, current_count=None) -> int:
        if current_count is None:
            return 60
        return {
            0 <= current_count < 5000: 0,
            5000 <= current_count < 15000: 15,
            15000 <= current_count < 30000: 300,
            30000 <= current_count < 100000: 3600,
            100000 <= current_count: 43200,
        }[True]

    def get_tasks_interaction(self, transaction, chunk_size=None):
        """If building task requires several queries to db or single query has extreme difficulty
        then this method could be overridden.
        In this case using of self.build_task_query_stmt method is not required
        and could be overridden with pass statement"""
        if chunk_size is None:
            chunk_size = self.chunk_size
        stmt = self.build_task_query_stmt(chunk_size)
        if isinstance(stmt, SQLAlchemyExecutable):
            stmt_compiled = stmt.compile(compile_kwargs={"literal_binds": True}, dialect=mysql.dialect())
            transaction.execute(str(stmt_compiled))
            # transaction.execute(str(stmt_compiled), stmt_compiled.params)
        else:
            transaction.execute(stmt)
        if chunk_size == 1:
            return transaction.fetchone()
        return transaction.fetchall()

    def on_get_tasks_error(self, failure):
        self.logger.error("failure: {}".format(failure))
        if failure.check(NotImplementedError):
            self.logger.critical("Required method is not implemented. Shutting down...")
            reactor.callLater(0, self.crawler_process._graceful_stop_reactor)
        if failure.check(OperationalError):
            if "1065" in failure.getErrorMessage():
                self.logger.error(
                    "Got empty query to DB. Incorrect implementation. Shutting down..."
                )
                reactor.callLater(0, self.crawler_process._graceful_stop_reactor)
        failure.trap(Exception)

    def update_task_interaction(self, transaction, db_task, status):
        """If updating task requires several queries to db or single query has extreme difficulty
        then this method could be overridden.
        In this case using of self.build_task_query_stmt method is not required
        and could be overridden with pass statement.
        In case when updating task in db is redundant
        then this method must be overridden with pass statement
        """
        stmt = self.build_task_update_stmt(db_task, status)
        if isinstance(stmt, SQLAlchemyExecutable):
            stmt_compiled = stmt.compile(compile_kwargs={"literal_binds": True})
            transaction.execute(str(stmt_compiled))
            # transaction.execute(str(stmt_compiled), stmt_compiled.params)
        else:
            transaction.execute(stmt)

    def build_task_query_stmt(self, chunk_size):
        """This method must returns sqlalchemy Executable or string that represents valid raw SQL select query

        stmt = select([DBModel]).where(
            DBModel.status == TaskStatusCodes.NOT_PROCESSED.value,
        ).order_by(DBModel.id.asc()).limit(chunk_size)
        return stmt
        """
        raise NotImplementedError

    def build_message_body(self, db_task):
        return dict(db_task)

    def build_task_update_stmt(self, db_task, status):
        """This method must returns sqlalchemy Executable or string that represents valid raw SQL update query

        return update(DBModel).where(DBModel.id == db_task['id']).values({'status': status})
        """
        raise NotImplementedError

    def process_tasks(self, rows):
        if rows is None or not len(rows):
            delay = self._delay(None)
            self.logger.info(f"DB is empty. waiting for {delay} seconds...")
            reactor.callLater(delay, self.produce_tasks, True)
            return
        if self.chunk_size == 1 and not isinstance(rows, list):
            rows = [rows]
        deferred_interactions = []
        for row in rows:
            msg_body = self.build_message_body(row)
            self._send_message(msg_body)
            deferred_update_task_interaction = self.db_connection_pool.runInteraction(
                self.update_task_interaction, row, TaskStatusCodes.IN_QUEUE.value
            )
            deferred_interactions.append(deferred_update_task_interaction)
        deferred_list = defer.DeferredList(deferred_interactions, consumeErrors=True)
        deferred_list.addCallback(self._on_task_update_completed).addErrback(self._on_task_update_error)

    def _on_task_update_completed(self, _result=None):
        if self.mode == Producer.CommandModes.ACTION.value:
            reactor.callLater(0, self.crawler_process._graceful_stop_reactor)
        elif self.mode == Producer.CommandModes.WORKER.value:
            reactor.callLater(0, self.produce_tasks)

    def _on_task_update_error(self, failure):
        self.logger.error("failure: {}".format(failure))
        failure.trap(Exception)

    def _send_message(self, msg_body):
        if not isinstance(msg_body, dict):
            raise ValueError("Built message body is not a dictionary")
        msg_body = self._convert_unserializable_values(msg_body)
        cb = functools.partial(
            self.rmq_connection.publish_message,
            message=json.dumps(msg_body),
            queue_name=self.task_queue_name,
            properties=pika.BasicProperties(
                content_type="application/json", delivery_mode=2, reply_to=self.reply_to_queue_name
            ),
        )
        self.rmq_connection.connection.ioloop.add_callback_threadsafe(cb)

    def _convert_unserializable_values(self, data):
        for key, val in data.items():
            if isinstance(val, dict):
                data[key] = self._convert_unserializable_values(val)
            elif isinstance(val, datetime.datetime):
                data[key] = int(val.timestamp())
            else:
                data[key] = val
        return data

    def set_connection_handle(self, connection):
        self.rmq_connection = connection
        self._can_interact = True

    def set_can_interact(self, can_interact):
        self._can_interact = can_interact

    def connect(self, parameters, queue_name):
        c = PikaSelectConnection(
            parameters,
            queue_name,
            owner=self,
            options={"enable_delivery_confirmations": True, "prefetch_count": 1,},
            is_consumer=False,
        )
        c.run()

    def run(self, args, opts):
        self.set_logger(self.__class__.__name__, self.project_settings.get("LOG_LEVEL"))
        reactor.callLater(0, self.execute, args, opts)
        reactor.run()
