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

class SensorDataProcessor(object):
    _log = Log().buildLogger()

    QUEUE_SIZE=10

    def __init__(self, queue):
        self._readingsQueue = queue
        self._transformer = NRF24DataTransformer()
        self._dataParser = SensorDataParser()
        self._consumers = []

    @inlineCallbacks
    def processQueue(self):
        if self._readingsQueue.qsize() < self.QUEUE_SIZE:
            self._log.debug("queue size is less than " + str(self.QUEUE_SIZE))
            returnValue(False)

        queueIter = iter_except(self._readingsQueue.get_nowait, Queue.Empty)
        convertedDList = yield defer.execute(map, self.parseRawDatum, queueIter)
        resultingData = yield defer.gatherResults(convertedDList, consumeErrors=True)

        consumerTasks = []
        for consumer in self._consumers:
            d = consumer.consume(resultingData)
            consumerTasks.append(d)

        returnValue(consumerTasks)

    @inlineCallbacks
    def parseRawDatum(self, rawDatum):
        unicode = yield self._transformer.convertBufferToUnicode(rawDatum.buffer, rawDatum.getShortUUID())
        readingDatum = yield self._dataParser.convertMessageToDTO(unicode, rawDatum.time, rawDatum.getShortUUID())
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
            self._consumers.append(consumer)
        else:
            log.warn("can't add a None consumer")

    def removeConsumer(self, consumer):
        if consumer in self._consumers:
            self._consumers.remove(consumer)


# Handle the transformation of incoming data from NRF24 transceivers
class NRF24DataTransformer(object):
    log = Log().buildLogger()

    def convertBufferToUnicode(self, buffer, uuid):
        self.log.debug(uuid + ": convertBufferToUnicode")
        self.log.debug(uuid + ": Buffer: {buffer}", buffer=buffer)
        return "".join(self._convertSingleToUnicode(i, uuid) for i in buffer)

    def _convertSingleToUnicode(self, n, uuid):
            # Decode into standard unicode set
            if (n >= 32 and n <= 126):
                return chr(n)
            elif (n != 0):
                self.log.warn(uuid + ": character outside of unicode range: " + str(n));

            return ""

# Parse incoming sensor data into a dictionary of values
class SensorDataParser(object):
    log = Log().buildLogger()

    def convertMessageToDTO(self, message, timestamp, uuid):
        self.log.debug(uuid + ": convertMessageToDTO")
        return defer.execute(self._convertMessageToDTO, message, timestamp, uuid)

    def _convertMessageToDTO(self, message, timestamp, uuid):
        dto = None
        if message.count('::') > 1:
            words = message.split("::", 4) #only three words, so split to that, have the extra go away
            self.log.debug(uuid + ": split message: " + str(words))
            #deviceId, sensorId, reading, time, rawUuid
            dto = SensorReadingDTO(words[0], words[1], words[2], timestamp, uuid)
        return dto


class IProcessor(Interface):
    def process(messageList):
        """ process the data in the list """

# Broadcasts sensor data to any subscribers
@implementer(IProcessor)
class WebServiceProcessor(object):
    log = Log().buildLogger()

    #single reading: POST /api/devices/<device_id>/sensors/<sensor_id>/readings?api_key=<key>
    #multiple readings: POST /api/readings?api_key=<key>
    @inlineCallbacks
    def consume(self, readingDatum):
        """ convert messagelist into a post for a web service """
        yield self.batchProcessSensorData(resultingData)

    @inlineCallbacks
    def batchProcessSensorData(self, resultingData):
        self.log.debug("batchProcessSensorData")
        dtoL = []
        for dto in resultingData:
            dtoL.append(convertToDict(dto))
        try:
            resp = yield treq.post('https://httpbin.org/post',
                                   json.dumps(dtoL),
                                   headers={'Content-Type': ['application/json']},
                                   timeout=5)
            yield self.processResponses(resp)
            returnValue(resp)
        except Exception as err:
            self.log.error(err)


    def processSinglePost(self, postBody):
        self.log.debug("postMessageToServer")
        try:
            resp = yield treq.post('https://httpbin.org/post',
                                   json.dumps(postBody),
                                   headers={'Content-Type': ['application/json']},
                                   timeout=5)
            returnValue(resp)
        except Exception as err:
            self.log.error(err)


    @inlineCallbacks
    def processResponses(self, response):
        self.log.debug("processServerResponse")
        try:
            json = yield response.json();
            defer.execute(self._printResponse, json)
            returnValue(json)
        except Exception as err:
            self.log.error(err)

    def _printResponse(self, responseJson):
        jsonDump = json.dumps(responseJson, sort_keys=True, indent=4, separators=(',', ': '))
        self.log.debug("Response: " + jsonDump)

# database holder for sensor
@implementer(IProcessor)
class DatabaseProcessor:
    log = Log().buildLogger()

    def __init__(self):
        self.dataToInsert = defer.DeferredQueue()

    @inlineCallbacks
    def consume(self, readingDatum):
        """ process list into database transaction """
        #yield defer.execute(self.log.debug, "process")
        yield self.batchProcessSensorData([readingDatum])

    @inlineCallbacks
    def processSensorData(self, data):
        self.log.debug("processSensorData")
        try:
            conn = txpostgres.Connection()
            dml = 'insert into sensor (deviceid, name, sensorid, sensortype, value) values (%s, %s, %s, %s, %s)'
            values = (data['uuid'], 'deviceXname', 'sensorXid', data['sensor'], data['value'])

            conn = yield conn.connect('dbname=sensor user=pi password=Obelisk1 host=localhost')
            yield self._conn.runOperation(dml, values)
        except Exception as err:
            self.log.error(err)
        finally:
            conn.close()
            returnValue(True)


    @inlineCallbacks
    def batchProcessSensorData(self, list):
        self.log.debug("batchProcessSensorData")
        try:
            conn = txpostgres.Connection()
            connDef = yield conn.connect('dbname=sensor user=pi password=Obelisk1 host=localhost')
            results = yield conn.runInteraction(self._buildTransactionLoop, list)
            self.log.info("batch database results: " + str(results))
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
             values = (datum.deviceId, 'deviceXname', 'sensorXid', datum.sensorId, datum.reading)
             yield cur.execute(dml, values)
