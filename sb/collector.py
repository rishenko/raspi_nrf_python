import sys, time, threading, Queue, itertools
from util import Log
from sb.dto import RawSensorReadingDTO

class SensorDataCollector(object):
    _log = Log().buildLogger()

    def __init__(self, radio, queue):
        self._radio = radio
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
            rd = RawSensorReadingDTO(buffer, time.time())
            self._readingsQueue.put(rd)

            self._log.info("listenForData end")
