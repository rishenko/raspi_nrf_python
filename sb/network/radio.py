from sb.collector import SensorDataCollector
from twisted.internet.protocol import Factory
from twisted.protocols.basic import LineReceiver
from twisted.internet import reactor, defer
from twisted.internet.defer import inlineCallbacks, returnValue

from sb.util import Log
import json

class NRFProtocolFactory(Factory):
    log = Log().buildLogger()

    def __init__(self):
        self._protocols = []

    def buildProtocol(self, address):
        protocol = NRFProtocol(self)
        self._protocols.append(protocol)
        self.log.info("building a protocol for: " + str(address))
        return protocol

    @inlineCallbacks
    def consume(self, datum):
        yield self.broadcast(datum)

    @inlineCallbacks
    def broadcast(self, datum):
        self.log.debug("broadcasting")
        results = yield [p.sendLine(self.datumToString(datum).encode()) for p in self._protocols]
        returnValue(results)

    def datumToString(self, datum):
        msg = json.dumps(datum, default=lambda d: d.json_serialize())
        return str(msg).replace(" ", "")

class NRFProtocol(LineReceiver):
    log = Log().buildLogger()

    def __init__(self, factory):
        self.factory = factory

    def connectionMade(self):
        self.log.info("connected")
        self.sendLine("CONNECT OK".encode())

    def connectionLost(self, reason):
        """ alert the factory to a lost connection """
        self.factory._protocols.remove(self)
        self.log.info("connection lost: " + str(reason))

    def lineReceived(self):
        """ this can be expanded as new features are added """
        pass
