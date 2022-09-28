import json
from sqlalchemy import types


class JsonProcessor(types.TypeDecorator):
    impl = types.JSON

    def literal_processor(self, dialect):
        def processor(value):
            if isinstance(value, str):
                serialized = value
            else:
                serialized = json.dumps(value)
            serialized = serialized.replace("'", "")
            return f"'{serialized}'"

        return processor
