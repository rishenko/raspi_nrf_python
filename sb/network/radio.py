from sb.collector import SensorDataCollector
from twisted.internet.protocol import Factory
from twisted.protocols.basic import LineReceiver
from twisted.internet import reactor, defer
from twisted.internet.defer import inlineCallbacks, returnValue

class NRFProtocolFactory(Factory):
    def __init__(self):
        self._protocols = []

    def buildProtocol(self):
        protocol = NRFProtocol()
        self._protocols.append(protocol)
        return protocol

    @inlineCallbacks
    def consume(self, datum):
        yield self.broadcast(datum)

    @inlineCallbacks
    def broadcast(self, datum):
        results = yield [p.sendLine(str(datum)) for p in self._protocols]
        returnValue(results)

class NRFProtocol(LineReceiver):
    def connectionMade(self):
        self.sendLine("CONNECT OK")

    def connectionLost(self):
        """ alert the factory to a lost connection """

    def lineReceived(self):
        """ this can be expanded as new features are added """
        pass
