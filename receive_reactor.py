import RPi.GPIO as GPIO
import uuid
import sys, threading, Queue, itertools
from threading import Thread
from zope.interface import Interface, implementer


from lib_nrf24 import NRF24
import spidev

from txpostgres import txpostgres
from twisted.python import util

from twisted.internet import reactor, task, defer, threads
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.logger import (
	Logger, textFileLogObserver, FilteringLogObserver, 
	LogLevel, LogLevelFilterPredicate
)

import json
import treq

# quick twisted logger builder
def buildLogger():
    LOG_LEVEL = LogLevel.debug
    observer = textFileLogObserver(sys.stdout)
    filteringObs = FilteringLogObserver(observer, 
                                    [LogLevelFilterPredicate(defaultLogLevel=LOG_LEVEL)])
    return filteringObs

globalLog = Logger(observer=buildLogger())

IRQ_PIN = 19
GPIO.setmode(GPIO.BCM)
GPIO.setup(IRQ_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP) 

pipes = [[0xE8, 0xE8, 0xF0, 0xF0, 0xE1], # writing address
         [0xF0, 0xF0, 0xF0, 0xF0, 0xE1]] # reading address - sensors write to this

# Extending the NRF24 library to encapsulate basic settings
class NRF24Radio(NRF24):
    log = Logger(observer=buildLogger())

    def __init__(self):
        super(NRF24Radio, self).__init__(GPIO, spidev.SpiDev()) 
        self.begin(0, 17)

        self.setPayloadSize(32)
        self.setChannel(0x76)
        self.setDataRate(NRF24.BR_1MBPS)
        self.setPALevel(NRF24.PA_MIN)

        self.setAutoAck(True)
        self.enableDynamicPayloads()
        self.enableAckPayload()

        self.openReadingPipe(1, pipes[1])
        self.printDetails()

    def listen(self):
        self.startListening()

    def readMessageToBuffer(self):
        receivedMessage = []
        #self.print_status(self.get_status())
        self.read(receivedMessage, self.getDynamicPayloadSize())
        return receivedMessage

class SensorDataCollector(object):
    _log = Logger(observer=buildLogger())

    def __init__(self, radio, reactor, queue):
        self._radio = radio
        self._reactor = reactor
	self._readingsQueue = queue

    def getReadings(self):
        return self._readingsQueue

    def listenForData(self):
        #if GPIO.input(IRQ_PIN) or not self._radio.available(0):
        #if not self._radio.available(0):
        if GPIO.input(IRQ_PIN):
	    #self._log.debug("radio not available")
            return

        self._log.info("listenForData start")

	while self._radio.available(0):
            self._log.info("radio is available, processing")
            buffer = self._radio.readMessageToBuffer()
 	    readingsQueue.put(buffer)

 	    #datum = DatumProcessor(buffer)
	    #datum.process()
            #self._log.info("finished creating a datum")

        self._log.info("listenForData end")

class SensorDataProcessor:
    _log = Logger(observer=buildLogger())

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

        self. _log.info("before map")
        queueIter = iter_except(self._readingsQueue.get_nowait, Queue.Empty)
        convertedDList = yield defer.execute(map, self.parseMessage, queueIter) 		
        self._log.info("after map")
        transformedMsgs = yield defer.gatherResults(convertedDList, consumeErrors=True) 
        self._log.info("after gather results")
        processorTasks = []
 	for processor in self._processorList:
  	    d = processor.process(transformedMsgs)
	    processorTasks.append(d)	

        returnValue(True)
     
    @inlineCallbacks
    def parseMessage(self, byteMessage):
        unicode = yield self._transformer.convertBufferToUnicode(byteMessage) 	
        jsonMessage = yield self._dataParser.convertMessageToDictionary(unicode)
        returnValue(jsonMessage)

class IProcessor(Interface):
    def process(messageList):
	""" process the data in the list """

class DatumProcessor(object):
    log = Logger(observer=buildLogger())

    def __init__(self, buffer):
        self._buffer = buffer
        self._uid = str(uuid.uuid1())[:13]
   
    @inlineCallbacks
    def process(self):
	self.log.info(self._uid + ": process start")
        try:
            wsProcessor = WebServiceProcessor(self._uid)
            sensorDb = SensorDatabase(self._uid) 

            # Process the incoming data from the radio

            # Convert the message to a format that can be sent elsewhere

            # Send the data to a remote server
            responses = yield wsProcessor.process(jsonMessage)
            #parsedResponses = wsProcessor.processResponses(responses)

            # Insert the data into the local db
	    dbResponse = sensorDb.processSensorData(jsonMessage)
        
	    self.log.info(self._uid + ": process end")
	    #returnValue(parsedResponses)
        except Exception as err:
  	    self.log.error(err)


# Handle the transformation of incoming data from NRF24 transceivers
class NRF24DataTransformer(object):
    log = Logger(observer=buildLogger())

    def __init__(self, uid):
        self._uid = uid

    def convertBufferToUnicode(self, buffer):
        self.log.debug(self._uid + ": convertBufferToUnicode")
	self.log.debug(self._uid + ": Buffer: {buffer}", buffer=buffer)
        return defer.execute(self._convertBufferToUnicode, buffer)

    def _convertBufferToUnicode(self, buffer):
        unicodeText = ""
        for n in buffer:
            # Decode into standard unicode set
            if (n >= 32 and n <= 126):
            #if (n <= 256):
                unicodeText += chr(n)
            elif (n != 0):
                self.log.warn(self._uid + ": character outside of unicode range: " + str(n));	

        self.log.debug("message received: " + unicodeText)
        return unicodeText


# Parse incoming sensor data into a dictionary of values
class SensorDataParser(object):
    log = Logger(observer=buildLogger())

    def __init__(self, uid):
	self._uid = uid

    def convertMessageToDictionary(self, message):
        self.log.debug(self._uid + ": convertMessageToPostBody")
        return defer.execute(self._convertMessageToDictionary, message)

    def _convertMessageToDictionary(self, message):
        if message.count('::') > 0:
            words = message.split("::")
            self.log.debug(self._uid + ": split message: " + str(words))
            data = {'uuid':words[0], 'sensor':words[1], 'value':words[2]}
        return data


# Broadcasts sensor data to any subscribers
@implementer(IProcessor)
class WebServiceProcessor(object):
    log = Logger(observer=buildLogger())

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
	finally:
	    returnValue(True)

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
    log = Logger(observer=buildLogger())
    dataToInsert = defer.DeferredQueue()

    @inlineCallbacks
    def process(self, messageList):
	""" process list into database transaction """
	#yield defer.execute(self.log.debug, "process")
        yield self.batchProcessSensorData(messageList)         
 
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
        for data in list:
             dml = 'insert into sensor (deviceid, name, sensorid, sensortype, value)'
             dml += ' values (%s, %s, %s, %s, %s)'
             values = (data['uuid'], 'deviceXname', 'sensorXid', data['sensor'], data['value']) 

             yield cur.execute(dml, values)
        results = yield defer.gatherResults(listOfExecutions) 
        returnValue(results)


# IRQ trigger, though not used
# def gpioEventTrigger(channel, reactor, controller):
#    globalLog.info("***IRQ trigger called on channel " + str(channel))
#    reactor.callFromThread(controller.listenForData) 

def iter_except(func, exception, first=None):
    """ Call a function repeatedly until an exception is raised.

    Converts a call-until-exception interface to an iterator interface.
    Like builtins.iter(func, sentinel) but uses an exception instead
    of a sentinel to end the loop.

    Examples:
        iter_except(functools.partial(heappop, h), IndexError)   # priority queue iterator
        iter_except(d.popitem, KeyError)                         # non-blocking dict iterator
        iter_except(d.popleft, IndexError)                       # non-blocking deque iterator
        iter_except(q.get_nowait, Queue.Empty)                   # loop over a producer Queue
        iter_except(s.pop, KeyError)                             # non-blocking set iterator

    """
    try:
        if first is not None:
            yield first()            # For database APIs needing an initial cast to db.first()
        while 1:
            yield func()
    except exception:
        pass


#handle shutting down all the things
def shutdown(radio):
    radio.end()
    GPIO.cleanup()
    globalLog.info("Finished shutting down the radio and GPIO.")

if __name__ == "__main__":
    radio = NRF24Radio()
    radio.listen()

    globalLog.info("About to start program loop")
    readingsQueue = Queue.Queue()
    globalLog.info("Queue created")

    controller = SensorDataCollector(radio, reactor, readingsQueue)
    globalLog.info("Collector created")

    processor = SensorDataProcessor(readingsQueue)
    globalLog.info("DataPocessor created")

    loop = task.LoopingCall(controller.listenForData)
    globalLog.info("LC 1 created")
    loop.start(.05)
    globalLog.info("LC 1 started")

    loop = task.LoopingCall(processor.processQueue)
    globalLog.info("LC 2 created")
    loop.start(5)
    globalLog.info("LC 2 started")

    globalLog.info("Loop has started, going to run reactor")

    reactor.suggestThreadPoolSize(20)
    reactor.addSystemEventTrigger("before", "shutdown", shutdown, radio)
    reactor.run()
