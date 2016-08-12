from twisted.internet import reactor, defer, task
from twisted.trial import unittest
import time, Queue
from sb.processor import SensorDataProcessor, WebServiceProcessor, DatabaseProcessor
from sb.util import Log, iter_except
from sb.dto import RawSensorReadingDTO
import sb.test.builder as builder

class ProcessorTests(unittest.TestCase):


    def buildRawSensorReadingDTOs(self, queue, count=5):
        log = Log().buildLogger()
        func = lambda ord: queue.put(RawSensorReadingDTO(ord, time.time()))
        builder.buildRangedOrdLists(func, 100, 4, 2, 86)

    def test_SensorDataProcessor(self):
        queue = Queue.Queue()
        self.buildRawSensorReadingDTOs(queue, 50)
        self._processorList = []
        self._processorList.append(WebServiceProcessor())
        #self._processorList.append(DatabaseProcessor())

        processor = SensorDataProcessor(queue, self._processorList)

        reactor.callWhenRunning(processor.processQueue)
        reactor.run()
