from twisted.internet import reactor, defer, task
from twisted.trial import unittest
import Queue
from sb.processor import SensorDataProcessor

class ProcessorTests(unittest.TestCase):

    def testSensorDataProcessor(self):
        queue = Queue.Queue()
        processor = SensorDataProcessor(queue)
