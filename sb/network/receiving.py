from sb.collector import SensorDataCollector
from twisted.internet.protocol import ClientFactory
from twisted.protocols.basic import LineReceiver
from twisted.internet import reactor, defer
from twisted.internet.defer import inlineCallbacks, returnValue
from sb import dto

from sb.util import Log
import ast

class ReceivingProtocolFactory(ClientFactory):
    log = Log().buildLogger()

    def __init__(self):
        self._protocols = []
        self._consumers = []

    def buildProtocol(self, address):
        protocol = ReceivingProtocol(self)
        self._protocols.append(protocol)
        self.log.info("building a protocol for: " + str(address))
        return protocol

    def clientConnectionLost(self, connector, reason):
        """If we get disconnected, reconnect to server."""
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        self.log.info("connection failed:" + str(reason))

    @inlineCallbacks
    def consume(self, datum):
        self.log.debug("consuming new data")
        results = yield [c.consume(datum) for c in self._consumers]
        returnValue(results)

    def addConsumer(self, consumer):
        if consumer is not None:
            self.log.info("added a consumer: " + str(consumer.__class__))
            self._consumers.append(consumer)
        else:
            log.warn("can't add a None consumer")

    def removeConsumer(self, consumer):
        if consumer in self._consumers:
            self._consumers.remove(consumer)
            log.info("removed a consumer: " + str(consumer.__class__))


class ReceivingProtocol(LineReceiver):
    log = Log().buildLogger()

    def __init__(self, factory):
        self.factory = factory

    def connectionMade(self):
        self.log.info("connected")

    def connectionLost(self, reason):
        """ alert the factory to a lost connection """
        self.factory._protocols.remove(self)
        self.log.info("connection lost: " + str(reason))

    def lineReceived(self, line):
        if (line == 'CONNECT OK'):
            return
        self.produce(line)

    @inlineCallbacks
    def produce(self, data):
        datum = yield self.convertToDatum(data)
        yield self.factory.consume(datum)

    @inlineCallbacks
    def convertToDatum(self, strDatum):
        reading = yield defer.execute(dto.RawSensorReadingDTO.json_deserialize, strDatum)
        returnValue(reading)
