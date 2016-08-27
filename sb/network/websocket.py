from twisted.internet import reactor, defer
from twisted.internet.defer import inlineCallbacks, returnValue

from twisted.internet.protocol import ReconnectingClientFactory
from autobahn.twisted.websocket import WebSocketClientFactory, \
    WebSocketClientProtocol, \
    connectWS

from sb.util import Log
import ast
import json

class SensorDataClientProtocol(WebSocketClientProtocol):
    log = Log().buildLogger()

    def __init__(self, factory):
        WebSocketClientProtocol.__init__(self)
        self.factory=factory

    def onOpen(self):
        self.log.info("connection successful")

    def onMessage(self, payload, isBinary):
        if not isBinary:
            self.log.info("Text message received");

class SensorDataClientFactory(ReconnectingClientFactory, WebSocketClientFactory):
    log = Log().buildLogger()

    def __init__(self, url):
        WebSocketClientFactory.__init__(self, url)
        self._protocols=[]

    protocol = SensorDataClientProtocol

    # http://twistedmatrix.com/documents/current/api/twisted.internet.protocol.ReconnectingClientFactory.html
    #
    maxDelay = 10
    maxRetries = 5

    def startedConnecting(self, connector):
        self.log.info('Started to connect.')

    def clientConnectionLost(self, connector, reason):
        self.log.info('Lost connection. Reason: {}'.format(reason))
        ReconnectingClientFactory.clientConnectionLost(self, connector, reason)

    def clientConnectionFailed(self, connector, reason):
        self.log.info('Connection failed. Reason: {}'.format(reason))
        ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)

    def buildProtocol(self, address):
        protocol = SensorDataClientProtocol(self)
        self._protocols.append(protocol)
        self.log.info("building a protocol for: " + str(address))
        return protocol

    @inlineCallbacks
    def consume(self, datum):
        yield self.broadcast(datum)

    @inlineCallbacks
    def broadcast(self, datum):
        self.log.debug("broadcasting")
        results = yield [p.sendMessage(self.datumToString(datum)) for p in self._protocols]
        returnValue(results)

    def datumToString(self, datum):
        msg = json.dumps(datum, default=lambda d: d.json_serialize())
        return str(msg).replace(" ", "")
