from typing import Union

from pika.adapters.twisted_connection import TwistedChannel
from pika.channel import Channel
from pika.spec import Basic, BasicProperties
from pydantic import BaseModel, Json, PrivateAttr, Extra


class BaseRMQMessage(BaseModel):
    channel: Union[Channel, TwistedChannel]
    deliver: Basic.Deliver
    basic_properties: BasicProperties
    body: Json

    # _rmq_connection: PikaSelectConnection = PrivateAttr()
    # _crawler: Crawler = PrivateAttr()
    _is_acknowledged_message: bool = PrivateAttr(False)

    class Config:
        arbitrary_types_allowed = True
        extra = Extra.forbid
