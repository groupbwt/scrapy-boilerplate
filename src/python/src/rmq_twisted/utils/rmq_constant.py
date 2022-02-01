from pydantic import BaseModel, Field


class __CONSTANT(BaseModel):
    message_meta_name: str = Field('message_meta_name', const=True)
    init_request_meta_name: str = Field('init_request_meta_name', const=True)


RMQ_CONSTANT = __CONSTANT()
