from twisted.internet import reactor, defer, task
from twisted.trial import unittest
import Queue
from sb.collector import SensorDataCollector
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

class CollectorTests(unittest.TestCase):

    def test_SensorDataCollector(self):
        radio = FakeRadio(False, 5)
        queue = Queue.Queue()
        collector = SensorDataCollector(radio, queue)
        collector.listenForData()
        self.assertEquals(collector.getReadings().qsize(), 5)
        for item in iter_except(queue.get_nowait, Queue.Empty):
            print(str(item.__dict__))
