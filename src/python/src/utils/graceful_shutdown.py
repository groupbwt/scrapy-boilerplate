import logging
import signal
import sys


class GracefulShutdown:
    is_terminate_signal_received: bool = False

    # Singleton
    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, 'instance'):
            cls.instance = super().__new__(cls)
        return cls.instance

    def __init__(self, force_shutdown: bool = True):
        self.logger = logging.getLogger(name=self.__class__.__name__)
        signal.signal(signal.SIGINT, self.terminate_signal_handler)
        signal.signal(signal.SIGTERM, self.terminate_signal_handler)
        self.force_shutdown: bool = force_shutdown

    def terminate_signal_handler(self, signum: int, frame):
        name: str = signal.Signals(signum).name
        if self.force_shutdown:
            self.logger.warning(f'Received {name} signal, forcing unclean shutdown')
            sys.exit(0)

        if self.is_terminate_signal_received:
            self.logger.warning(f'Received {name} twice, forcing unclean shutdown')
            sys.exit(0)
        else:
            self.is_terminate_signal_received = True
            self.logger.warning(f'Received {name}, shutting down gracefully. Send again to force')
