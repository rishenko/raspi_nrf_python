import RPi.GPIO as GPIO
import uuid
import sys

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

GPIO.setmode(GPIO.BCM)
pipes = [[0xE8, 0xE8, 0xF0, 0xF0, 0xE1], # writing address
         [0xF0, 0xF0, 0xF0, 0xF0, 0xE1]] # reading address - sensors write to this

def irqTest(data):
    globalLog.info("***IRQ PINGED*** " + str(data))

GPIO.setup(19, GPIO.IN, pull_up_down=GPIO.PUD_UP) 

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
    log = Logger(observer=buildLogger())

    def __init__(self, radio):
        self._radio = radio

    def listenForData(self):
        if GPIO.input(19):
            print('Input was HIGH')
        else:
            print('Input was LOW')
        if GPIO.input(19) or not self._radio.available(0):
	    self.log.info("radio not available")
            return

        self.log.info("listenForData start")
	while self._radio.available(0):
            self.log.info("radio is still available, processing")
            uid = str(uuid.uuid1())[:13]

            buffer = self._radio.readMessageToBuffer()

 	    datum = DatumProcessor(uid, buffer)
	    datum.process()

        self.log.info("listenForData end")

class DatumProcessor(object):
    log = Logger(observer=buildLogger())

    def __init__(self, uid, buffer):
        self._uid = uid
        self._buffer = buffer
   
    @inlineCallbacks
    def process(self):
        if GPIO.input(17):
            print('Input was HIGH')
        else:
            print('Input was LOW')
	self.log.info(self._uid + ": process start")
        transformer = NRF24DataTransformer(self._uid)
        sensorDataParser = SensorDataParser(self._uid)
        dataBroadcaster = SensorDataBroadcaster(self._uid)

        # Process the incoming data from the radio
        message = yield transformer.convertBufferToUnicode(self._buffer)

        # Convert the message to a format that can be sent elsewhere
        jsonMessage = yield sensorDataParser.convertMessageToDictionary(message)

        # Process the response back from the remote server
        responses = yield dataBroadcaster.broadcast(jsonMessage)
        parsedResponses = yield dataBroadcaster.processResponses(responses)

        sensorDb = SensorDatabase() 
	dbResponse = sensorDb.processSensorData(jsonMessage)
        
	self.log.info(self._uid + ": process end")
	returnValue(parsedResponses)

# Handle the transformation of incoming data from NRF24 transceivers
class NRF24DataTransformer(object):
    log = Logger(observer=buildLogger())

    def __init__(self, uid):
        self._uid = uid

    def convertBufferToUnicode(self, buffer):
        self.log.debug(self._uid + ": convertBufferToUnicode")
	self.log.debug(self._uid+ ": Buffer: {buffer}", buffer=buffer)
	def bufferTranslator(buffer):
            unicodeText = ""
            for n in buffer:
                # Decode into standard unicode set
                if (n >= 32 and n <= 126):
                    unicodeText += chr(n)
                elif (n != 0):
	            self.log.warn(self._uid + ": character outside of unicode range: " + str(n));	
	    return unicodeText
        return defer.execute(bufferTranslator, buffer)

# Parse incoming sensor data into a dictionary of values
class SensorDataParser(object):
    log = Logger(observer=buildLogger())

    def __init__(self, uid):
	self._uid = uid

    def convertMessageToDictionary(self, message):
        self.log.debug(self._uid + ": convertMessageToPostBody")
        def splitter(message):
            if message.count('::') > 0:
                words = message.split("::")
                self.log.debug(self._uid + ": split message: " + str(words))
                data = {'uuid':words[0], 'sensor':words[1], 'value':words[2]}
            return data
        return defer.execute(splitter, message)

# Broadcasts sensor data to any subscribers
class SensorDataBroadcaster(object):
    log = Logger(observer=buildLogger())

    def __init__(self, uid):
        self._uid = uid

    @inlineCallbacks
    def broadcast(self, postBody):
        self.log.debug(self._uid + ": postMessageToServer")
        resp = yield treq.post('https://httpbin.org/post',
                               json.dumps(postBody),
                               headers={'Content-Type': ['application/json']},
			       timeout=5) 
        returnValue(resp)

    @inlineCallbacks
    def processResponses(self, response):
        self.log.debug(self._uid + ": processServerResponse")
        json = yield response.json();
	defer.execute(self._printResponse, json)
        returnValue(json)

    def _printResponse(self, responseJson):
        jsonDump = json.dumps(responseJson, sort_keys=True, indent=4, separators=(',', ': ')) 
        #self.log.debug(self._uid + ": " + "Response: " + jsonDump)

class SensorDatabase:
    log = Logger(observer=buildLogger())

    def __init__(self):
        conn = txpostgres.Connection()
        self._def = conn.connect('dbname=sensor user=pi password=Obelisk1 host=localhost')
	self._conn = conn

    def processSensorData(self, data):
        dml = 'insert into sensor (deviceid, name, sensorid, sensortype, value) values (%s, %s, %s, %s, %s)'
        values = (data['uuid'], 'deviceXname', 'sensorXid', data['sensor'], data['value']) 
	self._def.addCallback(lambda _: self._conn.runOperation(dml, values))
	self._def.addCallback(lambda _: self._conn.close())
	self._def.addErrback(self.log.error)


#handle shutting down all the things
def shutdown(radio):
    radio.end()
    GPIO.cleanup()
 
#class InterruptHandler:
#    def __init__(self, controller, reactor):
#        self._controller = controller
#        self._reactor = reactor

def gpioEventTrigger(channel):
    reactor.callFromThread(controller.listenForData) 

def gpioKickoff():
    GPIO.add_event_detect(19, GPIO.FALLING,
                              callback=gpioEventTrigger,
                              bouncetime=300)


radio = NRF24Radio()
radio.listen()

globalLog.info("About to start program loop")
controller = SensorDataCollector(radio)

def main():

    #irqHandler = InterruptHandler(controller, reactor)
    loop = task.LoopingCall(controller.listenForData)
    loop.start(.05)

    gpioKickoff()

    #globalLog.info("Interrupt trigger has started, going to run reactor")
    #globalLog.info("Loop has started, going to run reactor")
    #reactor.addSystemEventTrigger("before", "shutdown", shutdown, radio)
    #reactor.callFromThread(gpioKickoff)
    reactor.run()

if __name__ == "__main__":
    main()
