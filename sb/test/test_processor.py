from twisted.internet import reactor, defer, task
from twisted.trial import unittest
import time, Queue
from sb.processor import SensorDataProcessor, WebServiceProcessor, DatabaseProcessor, IProcessor
from sb.util import Log, iter_except
from sb.dto import RawSensorReadingDTO
import sb.test.builder as builder

from zope.interface import implementer

@implementer(IProcessor)
class FakeProcessor(object):
    log = Log().buildLogger()

    def __init__(self, reactor):
        self._reactor = reactor

    def process(self, resultingData):
        self._reactor.stop()

class ProcessorTests(unittest.TestCase):

    def buildRawSensorReadingDTOs(self, queue, count=5):
        log = Log().buildLogger()
        func = lambda ord: queue.put(RawSensorReadingDTO(ord, time.time()))
        builder.buildRangedOrdLists(func, 10000, 4, 2, 86)

    def test_SensorDataProcessor(self):
        queue = Queue.Queue()
        self.buildRawSensorReadingDTOs(queue, 50)
        self._processorList = []
        self._processorList.append(FakeProcessor(reactor))
        #self._processorList.append(WebServiceProcessor())
        #self._processorList.append(DatabaseProcessor())

        processor = SensorDataProcessor(queue, self._processorList)

        reactor.callWhenRunning(processor.processQueue)
        reactor.run()
