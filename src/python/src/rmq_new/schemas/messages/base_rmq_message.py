import functools
import logging
from typing import Callable

from pika.channel import Channel
from pika.spec import Basic, BasicProperties
from pydantic import BaseModel, Json, PrivateAttr, Extra

from rmq.connections import PikaSelectConnection

logger = logging.getLogger(name='BaseRmqMessage')


class BaseRmqMessage(BaseModel):
    channel: Channel
    deliver: Basic.Deliver
    basic_properties: BasicProperties
    body: Json

    _rmq_connection: PikaSelectConnection = PrivateAttr()
    _is_acknowledged_message: bool = PrivateAttr(False)

    def __init__(self, **data):
        if '_rmq_connection' in data:
            self._rmq_connection = data.pop('_rmq_connection')
        super().__init__(**data)

    def ack(self):
        if self._is_acknowledged_message is False:
            self._is_acknowledged_message = True

            ack_function: Callable = functools.partial(
                self._rmq_connection.acknowledge_message, delivery_tag=self.deliver.delivery_tag
            )
            self._rmq_connection.connection.ioloop.add_callback_threadsafe(ack_function)
            logger.info(f'ACK message with delivery tag {self.deliver.delivery_tag}')

    def nack(self) -> None:
        if self._is_acknowledged_message is False:
            self._is_acknowledged_message = True

            nack_function: Callable = functools.partial(
                self._rmq_connection.negative_acknowledge_message, delivery_tag=self.deliver.delivery_tag
            )
            self._rmq_connection.connection.ioloop.add_callback_threadsafe(nack_function)
            logger.info(f'NACK message with delivery tag {self.deliver.delivery_tag}')

    class Config:
        arbitrary_types_allowed = True
        extra = Extra.forbid
