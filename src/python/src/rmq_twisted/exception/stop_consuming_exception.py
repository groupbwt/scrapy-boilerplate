class StopConsumingException(Exception):
    def __init__(self):
        super().__init__('stop consuming')
