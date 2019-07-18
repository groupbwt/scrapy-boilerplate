## -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
from sqlalchemy import create_engine
from sqlalchemy.exc import DataError, IntegrityError, InvalidRequestError
from sqlalchemy.orm import sessionmaker

from util import mysql_connection_string


class ${class_name}(object):
    def __init__(self):
        self.engine = create_engine(mysql_connection_string())

    def open_spider(self, spider):
        make_session = sessionmaker(bind=self.engine)
        self.session = make_session()

    def process_item(self, item, spider):
        # if isinstance(item, SampleItem):
        #     pass

        return item

    def close_spider(self, spider):
        self.session.close()
