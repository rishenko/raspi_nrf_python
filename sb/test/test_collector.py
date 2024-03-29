from twisted.internet import reactor, defer, task
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.trial import unittest
import queue
from sb.collector import SensorDataCollector
from sb.processor import SensorDataProcessor
from sb.util import Log, iter_except
import sb.test.builder as builder

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

from zope.interface import implementer

#@implementer(IProcessor)
class FakeProcessor(object):
    log = Log().buildLogger()

    @inlineCallbacks
    def consume(self, resultingData):
        yield defer.execute(str, resultingData)

class CollectorTests(unittest.TestCase):

    def test_SensorDataCollector(self):
        radio = FakeRadio(False, 5)
        collector = SensorDataCollector(radio)
        collector.listenForData()

    def test_SensorDataCollectorProcess(self):
        radio = FakeRadio(False, 5)
        collector = SensorDataCollector(radio)

        processor = SensorDataProcessor()
        processor.addConsumer(FakeProcessor())

        collector.addConsumer(processor)

        collector.listenForData()
