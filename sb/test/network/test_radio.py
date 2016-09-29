from twisted.internet import reactor, defer, task
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.trial import unittest
from twisted.test import proto_helpers
import queue
from sb.collector import SensorDataCollector
from sb.processor import SensorDataProcessor
from sb.util import Log, iter_except
import sb.test.builder as builder
from sb.network.radio import NRFProtocol, NRFProtocolFactory

class FakeRadio(object):

    def __init__(self, irqCheckRes, availableCountMax):
        self._irqCheckRes = irqCheckRes
        self._availableCountMax = availableCountMax
        self._availableCount = 0

    def irqCheck(self):
        return self._irqCheckRes

    def available(self, pipe):
        result = self._availableCount < self._availableCountMax
        self._availableCount += 1
        return result

    def readMessageToBuffer(self):
        buffer = builder.buildOrdList(1, 2, self._availableCount)
        return buffer;

class TestNRFFactory(unittest.TestCase):
    def setUp(self):
        self.radio = FakeRadio(False, 10)
        self.collector = SensorDataCollector(self.radio)
        self.factory = NRFProtocolFactory()
        self.collector.addConsumer(self.factory)

        self.tr = proto_helpers.StringTransport()
        self.proto = self.factory.buildProtocol("127.0.0.1")
        self.proto.makeConnection(self.tr)

    def test_broadcast(self):
        self.collector.listenForData()
        print(self.tr.value())
        self.assertTrue(self.tr.value().decode().startswith("CONNECT OK\r\n"))
        print(self.tr.value())
