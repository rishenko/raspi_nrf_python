import RPi.GPIO as GPIO
import uuid
import sys

from lib_nrf24 import NRF24
import spidev

from twisted.internet import reactor, task, defer, threads
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.logger import (
	Logger, textFileLogObserver, FilteringLogObserver, 
	LogLevel, LogLevelFilterPredicate
)

import json
import treq

observer = textFileLogObserver(sys.stdout)
filteringObs = FilteringLogObserver(observer, 
                                    [LogLevelFilterPredicate(defaultLogLevel=LogLevel.debug)])
log = Logger(observer=filteringObs)

GPIO.setmode(GPIO.BCM)
pipes = [[0xE8, 0xE8, 0xF0, 0xF0, 0xE1], # writing address
         [0xF0, 0xF0, 0xF0, 0xF0, 0xE1]] # reading address - sensors write to this

# Extending the NRF24 library to encapsulate basic settings
class NRF24Radio(NRF24):
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
        self.print_status(self.get_status())
        self.read(receivedMessage, self.getDynamicPayloadSize())
        return receivedMessage

class SensorAggregationController:
    def __init__(self, radio):
        self._radio = radio

    def listenForData(self):
        if not self._radio.available(0):
            return

        uid = str(uuid.uuid1())
        log.debug(uid + ": listenForData start")

        buffer = self._radio.readMessageToBuffer()

 	datum = SensorDatumProcessor(uid, buffer)
	datum.process()

        log.debug(uid + ": listenForData end")

class SensorDatumProcessor:
    def __init__(self, uid, buffer):
        self._uid = uid
        self._buffer = buffer
   
    @inlineCallbacks
    def process(self):
        transformer = NRF24ReceiverTransform(self._uid)
        sensorDataParser = SensorDataParser(self._uid)
        dataBroadcaster = SensorDataBroadcaster(self._uid)

        # Process the incoming data from the radio
        message = yield transformer.convertBufferToUnicode(self._buffer)

        # Convert the message to a format that can be sent elsewhere
        jsonMessage = yield sensorDataParser.convertMessageToPostBody(message)

        # Process the response back from the remote server
        responses = yield dataBroadcaster.broadcast(jsonMessage)
        parsedResponses = yield dataBroadcaster.processResponses(responses)

	returnValue(parsedResponses)

# Handle the transformation of incoming data from NRF24 transceivers
class NRF24ReceiverTransform:
    def __init__(self, uid):
        self._uid = uid

    def convertBufferToUnicode(self, buffer):
        log.debug(self._uid + ": convertBufferToUnicode")
	log.debug("Buffer: {buffer}", buffer=buffer)
	def bufferTranslator(buffer):
            unicodeText = ""
            for n in buffer:
                # Decode into standard unicode set
                if (n >= 32 and n <= 126):
                    unicodeText += chr(n)
	    return unicodeText
        return defer.execute(bufferTranslator, buffer)

# Parse incoming sensor data into a dictionary of values
class SensorDataParser:
    def __init__(self, uid):
	self._uid = uid

    def convertMessageToPostBody(self, message):
        log.debug(self._uid + ": convertMessageToPostBody")
        def splitter(message):
            if message.count('::') > 0:
                words = message.split("::")
                log.debug(self._uid + ": split message: " + str(words))
                data = {'uuid':words[0], 'sensor':words[1], 'value':words[2]}
            return data
        return defer.execute(splitter, message)

class SensorDataBroadcaster:
    def __init__(self, uid):
        self._uid = uid

    @inlineCallbacks
    def broadcast(self, postBody):
        log.debug(self._uid + ": postMessageToServer")
        resp = yield treq.post('https://httpbin.org/post',
                               json.dumps(postBody),
                               headers={'Content-Type': ['application/json']}) 
        returnValue(resp)

    @inlineCallbacks
    def processResponses(self, response):
        log.debug(self._uid + ": processServerResponse")
        json = yield response.json();
	defer.execute(self._printResponse, json)
        returnValue(json)

    def _printResponse(self, responseJson):
        log.debug(self._uid + ": " + "Response: " + json.dumps(responseJson, sort_keys=True,
                                                        indent=4, separators=(',', ': ')))

def shutdown(radio):
    radio.end()
 
def main():
    radio = NRF24Radio()
    radio.listen()

    log.info("About to start program loop")
    controller = SensorAggregationController(radio)
    loop = task.LoopingCall(controller.listenForData)
    loop.start(0)

    log.info("Loop has started, going to run reactor")
    reactor.addSystemEventTrigger("before", "shutdown", shutdown, radio)
    reactor.run()

if __name__ == "__main__":
    main()
