import sys, time, threading, queue, itertools
from sb.util import Log
from sb.dto import RawSensorReadingDTO
from twisted.internet import reactor, task, defer, threads
from twisted.internet.defer import inlineCallbacks, returnValue

class SensorDataCollector(object):
    _log = Log().buildLogger()

    def __init__(self, radio):
        self._radio = radio
        self._consumers = []

    @inlineCallbacks
    def listenForData(self):
        self._log.info("listenForData start")

        results = []
        while self._radio.available(0):
            self._log.info("radio is available - processing")
            buffer = self._radio.readMessageToBuffer()
            rd = RawSensorReadingDTO(buffer, time.time())
            results.append(self.produce(rd))

        self._log.info("listenForData end")
        yield defer.gatherResults(results, consumeErrors=True)

    @inlineCallbacks
    def produce(self, data):
        consumerDeferreds = [x.consume(data) for x in self._consumers]
        results = yield defer.gatherResults(consumerDeferreds, consumeErrors=True)
        returnValue(results)

    def addConsumer(self, consumer):
        if consumer is not None:
            self._consumers.append(consumer)
        else:
            log.warn("can't add a None consumer")

    def removeConsumer(self, consumer):
        if consumer in self._consumers:
            self._consumers.remove(consumer)
