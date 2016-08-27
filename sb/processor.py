import json
import treq
import util
from util import Log, iter_except, convertToDict
import Queue
from sb.dto import SensorReadingDTO, RawSensorReadingDTO

from txpostgres import txpostgres
from twisted.python import util
from twisted.internet import reactor, task, defer, threads
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.logger import (
    Logger, textFileLogObserver, FilteringLogObserver,
    LogLevel, LogLevelFilterPredicate
)
from zope.interface import Interface, implementer


class QueueDataProcessor(object):

    def __init__(self, queue, processSize=20):
        self._readingsQueue = queue
        self._processSize = processSize
        self._counter = -1

    @inlineCallbacks
    def consume(self, readingDatum):
        self._readingsQueue.put_nowait(readingDatum)
        if (self.readyToProcess()):
            yield self.processQueue()

    @inlineCallbacks
    def processQueue(self):
        """ implement """

    def readyToProcess(self):
        self._counter += 1
        if (self._counter > self._processSize):
            self._counter = 0
            return True
        else:
            return False


class SensorDataProcessor(object):
    _log = Log().buildLogger()

    def __init__(self):
        self._transformer = NRF24DataTransformer()
        self._dataParser = SensorDataParser()
        self._consumers = []

    @inlineCallbacks
    def parseRawDatum(self, rawDatum):
        unicode = yield self._transformer.convertBufferToUnicode(rawDatum.buffer)
        readingDatum = yield self._dataParser.convertMessageToDTO(unicode, rawDatum)
        returnValue(readingDatum)

    @inlineCallbacks
    def consume(self, readingDatum):
        processedDatum = yield self.parseRawDatum(readingDatum)
        yield self.produce(processedDatum)

    @inlineCallbacks
    def produce(self, data):
        consumerDeferreds = yield [x.consume(data) for x in self._consumers]
        results = yield defer.gatherResults(consumerDeferreds, consumeErrors=True)
        returnValue(results)

    def addConsumer(self, consumer):
        if consumer is not None:
            self._log.info("adding a consumer: " + str(consumer.__class__))
            self._consumers.append(consumer)
        else:
            self._log.warn("can't add a None consumer")

    def removeConsumer(self, consumer):
        if consumer in self._consumers:
            self._consumers.remove(consumer)


# Handle the transformation of incoming data from NRF24 transceivers
class NRF24DataTransformer(object):
    log = Log().buildLogger()

    def convertBufferToUnicode(self, buffer):
        return "".join(self._convertSingleToUnicode(i) for i in buffer)

    def _convertSingleToUnicode(self, n):
        # Decode into standard unicode set
        if (n >= 32 and n <= 126):
            return chr(n)
        elif (n != 0):
            self.log.warn("character outside of unicode range: " + str(n))

        return ""

# Parse incoming sensor data into a dictionary of values


class SensorDataParser(object):
    log = Log().buildLogger()

    def convertMessageToDTO(self, message, datum):
        self.log.debug(datum.uuid + ": convertMessageToDTO")
        return defer.execute(self._convertMessageToDTO, message, datum)

    def _convertMessageToDTO(self, message, datum):
        dto = None
        if message.count('::') > 1:
            # only three words, so split to that, have the extra go away
            words = message.split("::", 4)
            self.log.debug(datum.uuid + ": split message: " + str(words))
            #deviceId, sensorId, reading, time, rawUuid
            dto = SensorReadingDTO(words[0], words[1], words[
                                   2], datum.time, datum.uuid)
        return dto


class IProcessor(Interface):

    def process(messageList):
        """ process the data in the list """

# Broadcasts sensor data to any subscribers


@implementer(IProcessor)
class WebServiceProcessor(object):
    log = Log().buildLogger()

    # single reading: POST /api/devices/<device_id>/sensors/<sensor_id>/readings?api_key=<key>
    # multiple readings: POST /api/readings?api_key=<key>
    @inlineCallbacks
    def consume(self, readingDatum):
        self.log.info("consuming a datum")
        """ convert messagelist into a post for a web service """
        yield self.processSinglePost(readingDatum)

    @inlineCallbacks
    def batchProcessSensorData(self, resultingData):
        self.log.debug("batchProcessSensorData")
        dtoL = []
        for dto in resultingData:
            dtoL.append(convertToDict(dto))
        try:
            resp = yield treq.post('https://httpbin.org/post',
                                   json.dumps(dtoL),
                                   headers={
                                       'Content-Type': ['application/json']},
                                   timeout=5)
            yield self.processResponses(resp)
            returnValue(resp)
        except Exception as err:
            self.log.error(err)

    def processSinglePost(self, postBody):
        self.log.info("postMessageToServer")
        try:
            resp = yield treq.post('https://httpbin.org/post',
                                   json.dumps(postBody),
                                   headers={
                                       'Content-Type': ['application/json']},
                                   timeout=5)
            self.log.debug(str(resp))
            returnValue(resp)
        except Exception as err:
            self.log.error(err)

    @inlineCallbacks
    def processResponses(self, response):
        self.log.debug("processServerResponse")
        try:
            json = yield response.json()
            defer.execute(self._printResponse, json)
            returnValue(json)
        except Exception as err:
            self.log.error(err)

    def _printResponse(self, responseJson):
        jsonDump = json.dumps(responseJson, sort_keys=True,
                              indent=4, separators=(',', ': '))
        self.log.debug("Response: " + jsonDump)

# database holder for sensor


@implementer(IProcessor)
class DatabaseProcessor(QueueDataProcessor):
    log = Log().buildLogger()

    def __init__(self, queue, processSize=20):
        self.dataToInsert = defer.DeferredQueue()
        super(DatabaseProcessor, self).__init__(queue, processSize)

    @inlineCallbacks
    def processQueue(self):
        queueIter = iter_except(self._readingsQueue.get_nowait, Queue.Empty)
        results = yield self.batchProcessSensorData(queueIter)
        returnValue(results)

    @inlineCallbacks
    def processSensorData(self, data):
        self.log.debug("processSensorData")
        try:
            conn = txpostgres.Connection()
            dml = 'insert into sensor (deviceid, name, sensorid, sensortype, value) values (%s, %s, %s, %s, %s)'
            values = (data.deviceId, 'deviceXname',
                      'sensorXid', data.sensorId, data.reading)

            conn = yield conn.connect('dbname=sensor user=pi password=Obelisk1 host=localhost')
            yield conn.runOperation(dml, values)
        except Exception as err:
            self.log.error(err)
        finally:
            conn.close()

    @inlineCallbacks
    def batchProcessSensorData(self, list):
        self.log.debug("batchProcessSensorData")
        try:
            conn = txpostgres.Connection()
            connDef = yield conn.connect('dbname=sensor user=pi password=Obelisk1 host=localhost')
            results = yield conn.runInteraction(self._buildTransactionLoop, list)
            self.log.info("batch database insertion")
            returnValue(results)
        except Exception as err:
            self.log.error(err)
        finally:
            conn.close()

    @inlineCallbacks
    def _buildTransactionLoop(self, cur, list):
        for datum in list:
            dml = 'insert into sensor (deviceid, name, sensorid, sensortype, value)'
            dml += ' values (%s, %s, %s, %s, %s)'
            values = (datum.deviceId, 'deviceXname',
                      'sensorXid', datum.sensorId, datum.reading)
            yield cur.execute(dml, values)
