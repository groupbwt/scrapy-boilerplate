from twisted.internet import reactor

from . import BaseCommand


class BaseReactorCommand(BaseCommand):
    def execute(self, args: list, opts: list):
        raise NotImplementedError

    def run(self, args: list, opts: list):
        reactor.callFromThread(self.execute, args, opts)
        reactor.callFromThread(reactor.stop)
        reactor.run()
