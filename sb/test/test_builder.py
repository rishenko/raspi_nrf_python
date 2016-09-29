from twisted.internet import reactor, defer, task
from twisted.trial import unittest
import time, queue
from sb.processor import SensorDataProcessor, WebServiceProcessor, DatabaseProcessor, IProcessor
from sb.util import Log, iter_except
from sb.dto import RawSensorReadingDTO
import sb.test.builder as builder

class ProcessorTests(unittest.TestCase):
    def test_stringtoOrds(self):
        q = queue.Queue(maxsize=0)
        func = lambda ord: q.put(RawSensorReadingDTO(ord, time.time()))
        builder.buildRangedOrdLists(func, 10000, 4, 2, 86)
