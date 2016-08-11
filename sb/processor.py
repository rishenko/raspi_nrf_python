import json
import treq
import util
from util import Log, iter_except

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

    def __init__(self, queue):
        self._readingsQueue = queue
        self._uid = "uuid"
        self._transformer = NRF24DataTransformer(self._uid)
        self._dataParser = SensorDataParser(self._uid)
        self._buildProcessList()

    def _buildProcessList(self):
        self._processorList = []
        self._processorList.append(WebServiceProcessor(self._uid))
        self._processorList.append(DatabaseProcessor())

    @inlineCallbacks
    def processQueue(self):
        if self._readingsQueue.qsize() < 10:
            self._log.debug("queue size is less than 50")
            returnValue(False)

        queueIter = iter_except(self._readingsQueue.get_nowait, Queue.Empty)
        convertedDList = yield defer.execute(map, self.parseRawDatum, queueIter)

        resultingData = yield defer.gatherResults(convertedDList, consumeErrors=True)
        processorTasks = []
        for processor in self._processorList:
            d = processor.process(resultingData)
            processorTasks.append(d)

        returnValue(True)

    @inlineCallbacks
    def parseRawDatum(self, rawDatum):
        unicode = yield self._transformer.convertBufferToUnicode(rawDatum.buffer)
        readingDatum = yield self._dataParser.convertMessageToDictionary(unicode, rawDatum.time)
        returnValue(readingDatum)





class IProcessor(Interface):
    def process(messageList):
        """ process the data in the list """

# Broadcasts sensor data to any subscribers
@implementer(IProcessor)
class WebServiceProcessor(object):
    log = Log().buildLogger()

    #single reading: POST /api/devices/<device_id>/sensors/<sensor_id>/readings?api_key=<key>
    #multiple readings: POST /api/readings?api_key=<key>

    def __init__(self, uid):
        self._uid = uid

    @inlineCallbacks
    def process(self, messageList):
        """ convert messagelist into a post for a web service """
        yield defer.execute(self.log.debug, "process")


    def processSinglePost(self, postBody):
        self.log.debug(self._uid + ": postMessageToServer")
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
        self.log.debug(self._uid + ": processServerResponse")
        try:
            json = yield response.json();
            defer.execute(self._printResponse, json)
            returnValue(json)
        except Exception as err:
            self.log.error(err)

    def _printResponse(self, responseJson):
        jsonDump = json.dumps(responseJson, sort_keys=True, indent=4, separators=(',', ': '))
        #self.log.debug(self._uid + ": " + "Response: " + jsonDump)

#broacaster has a series of processing objects
#when a new datum is passed in, it creates a deferred list of those processing objects
#final processing for that datum is considered complete when all processors have completed
#^^^ is that necessary? Who cares if any fail?

#consider a queue for database stuff. We are inserting large amounts.
#need to queue up a batch instead of inserting all at once
#does the same apply to web requests? Should we be sending single
#requests for each device/sensor, or sending off a batch?
#the former means each item gets stored, the latter means
#far less CPU and network intensive operations
#which could be great for a Raspberry pi


# database holder for sensor
@implementer(IProcessor)
class DatabaseProcessor:
    log = Log().buildLogger()

    def __init__(self):
        self.dataToInsert = defer.DeferredQueue()

    @inlineCallbacks
    def process(self, dataList):
        """ process list into database transaction """
        #yield defer.execute(self.log.debug, "process")
        yield self.batchProcessSensorData(dataList)

    @inlineCallbacks
    def processSensorData(self, data):
        self.log.debug("processSensorData")
        try:
            conn = txpostgres.Connection()
            dml = 'insert into sensor (deviceid, name, sensorid, sensortype, value) values (%s, %s, %s, %s, %s)'
            values = (data['uuid'], 'deviceXname', 'sensorXid', data['sensor'], data['value'])

            self._conn = yield conn.connect('dbname=sensor user=pi password=Obelisk1 host=localhost')
            yield self._conn.runOperation(dml, values)
        except Exception as err:
            self.log.error(err)
        finally:
            self._conn.close()
            returnValue(True)


    @inlineCallbacks
    def batchProcessSensorData(self, list):
        self.log.debug("batchProcessSensorData")
        try:
            conn = txpostgres.Connection()
            connDef = yield conn.connect('dbname=sensor user=pi password=Obelisk1 host=localhost')
            results = yield conn.runInteraction(self._buildTransactionLoop, list)
            returnValue(results)
        except Exception as err:
            self.log.error(err)
        finally:
            conn.close()

    @inlineCallbacks
    def _buildTransactionLoop(self, cur, list):
        listOfExecutions = []
        for datum in list:
             dml = 'insert into sensor (deviceid, name, sensorid, sensortype, value)'
             dml += ' values (%s, %s, %s, %s, %s)'
             values = (datum.deviceId, 'deviceXname', 'sensorXid', datum.sensorId, datum.reading)

             yield cur.execute(dml, values)
        results = yield defer.gatherResults(listOfExecutions)
        returnValue(results)
