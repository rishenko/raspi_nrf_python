from twisted.internet import reactor, defer, task
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.trial import unittest
import time, Queue
from sb.processor import SensorDataProcessor, WebServiceProcessor, DatabaseProcessor, IProcessor
from sb.util import Log, iter_except
from sb.dto import RawSensorReadingDTO
import sb.test.builder as builder

from zope.interface import implementer

class FakeProcessor(object):
    log = Log().buildLogger()

    @inlineCallbacks
    def consume(self, resultingData):
        yield defer.execute(str, resultingData)

class ProcessorTests(unittest.TestCase):

    def buildRawSensorReadingDTOs(self, queue, count=5):
        log = Log().buildLogger()
        func = lambda ord: queue.put(RawSensorReadingDTO(ord, time.time()))
        builder.buildRangedOrdLists(func, 10000, 4, 2, 86)

    def test_SensorDataProcessor(self):
        queue = Queue.Queue()
        self.buildRawSensorReadingDTOs(queue, 50)

        processor = SensorDataProcessor()
        processor.addConsumer(FakeProcessor())
        #processor.addConsumer(WebServiceProcessor())
        #processor.addConsumer(DatabaseProcessor())
        iq = iter_except(queue.get_nowait, Queue.Empty)
        [processor.consume(datum) for datum in iq]
