class RMQObject:
    def __init__(self, ack_callback, nack_callback):
        self.__ack_callback = ack_callback
        self.__nack_callback = nack_callback

    def __disable_callbacks(self):
        self.ack = lambda: None
        self.nack = lambda: None

    def ack(self):
        self.__ack_callback()
        self.__disable_callbacks()

    def nack(self):
        self.__nack_callback()
        self.__disable_callbacks()
