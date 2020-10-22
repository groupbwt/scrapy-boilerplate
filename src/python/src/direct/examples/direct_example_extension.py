from direct.extensions import DirectDBConnectionExtension
from database.models.test import Test
from sqlalchemy.sql.expression import Select, Update
from rmq.utils import TaskStatusCodes
from sqlalchemy.dialects.mysql import insert


class DirectExampleExtension(DirectDBConnectionExtension):

    def build_message_store_stmt(self, fetch_chunk):
        select = Select([Test]).where(Test.status == TaskStatusCodes.NOT_PROCESSED.value).limit(fetch_chunk)
        return select

    def build_task_save_stmt(self, item, status):

        insert_item = insert(Test).values({
            "id": item["id"],
            "status": status,
            "title": item["title"],
            "page": item["page"]
        })
        insert_odcu = insert_item.on_duplicate_key_update({
            "id": insert_item.inserted.id,
            "status": insert_item.inserted.status,
            "title": insert_item.inserted.title,
            "page": insert_item.inserted.page,
        })

        return insert_odcu

    def build_task_update_status_stmt(self, item, status):
        update = Update(Test).values({"status": status}).where(Test.id == item["id"])
        return update

