from abc import ABC

from twisted.internet import reactor
from twisted.internet.defer import Deferred
from twisted.python.failure import Failure

from commands.base import BaseCommand


class BaseReactorCommand(BaseCommand, ABC):
    def execute(self, args: list, opts: list) -> Deferred:
        raise NotImplementedError

    def __execute(self, args: list, opts: list) -> Deferred:
        query: Deferred = self.execute(args, opts)
        query.addErrback(self.errback)
        query.addBoth(lambda _: reactor.stop())
        return query

    def errback(self, failure: Failure):
        self.logger.error(failure)

    def run(self, args: list, opts: list):
        reactor.callFromThread(self.__execute, args, opts)
        reactor.run()
