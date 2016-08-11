import sys, time, threading, Queue, itertools
from util import Log

class SensorDataCollector(object):
    _log = Log().buildLogger()

    def __init__(self, radio, reactor, queue):
        self._radio = radio
        self._reactor = reactor
        self._readingsQueue = queue

    def getReadings(self):
        return self._readingsQueue

    def listenForData(self):
        if self._radio.irqCheck():
            #self._log.debug("radio not available")
            return

        self._log.info("listenForData start")

        while self._radio.available(0):
            self._log.info("radio is available, processing")
            buffer = self._radio.readMessageToBuffer()
            rd = RawReadingDatum(buffer, time.time())
            self._readingsQueue.put(rd)

            self._log.info("listenForData end")

class RawReadingDatum(object):
    def __init__(self, buffer, time):
        self.buffer = buffer
        self.time = time
