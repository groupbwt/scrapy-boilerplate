from sqlalchemy import types


class DatetimeProcessor(types.TypeDecorator):
    impl = types.TIMESTAMP

    def literal_processor(self, dialect):
        def processor(value):
            return f"'{value}'"

        return processor
