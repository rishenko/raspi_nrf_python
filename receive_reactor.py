import RPi.GPIO as GPIO
from lib_nrf24 import NRF24
import time
import spidev
import requests
from twisted.internet import reactor, task, defer
from twisted.internet.defer import inlineCallbacks, returnValue

GPIO.setmode(GPIO.BCM)
pipes = [[0xE8, 0xE8, 0xF0, 0xF0, 0xE1], [0xF0, 0xF0, 0xF0, 0xF0, 0xE1], [0xF0, 0xF0, 0xF0, 0xF0, 0xE2]]

class NRF24Radio(NRF24):
    def __init__(self):
        super(NRF24Radio, self).__init__(GPIO, spidev.SpiDev()) 
	#self._radio = NRF24(GPIO, spidev.SpiDev())
	self.begin(0, 17)

	self.setPayloadSize(32)
	self.setChannel(0x76)
	self.setDataRate(NRF24.BR_1MBPS)
	self.setPALevel(NRF24.PA_MIN)

	self.setAutoAck(True)
	self.enableDynamicPayloads()
	self.enableAckPayload()

	self.openReadingPipe(1, pipes[1])
	self.openReadingPipe(2, pipes[2])
	self.printDetails()

    def listen(self):
	self.startListening()

@inlineCallbacks
def listenForData(radio):
    if not radio.available(0):
	return

    buffer = yield readMessageToBuffer(radio)
    message = yield convertBufferToUnicode(buffer)
    jsonMessage = yield convertMessageToPostBody(message)
    response = yield postMessageToServer(jsonMessage)
    

def readMessageToBuffer(radio):
    d = defer.Deferred()
    receivedMessage = []
    radio.print_status(radio.get_status())
    #print("Received: {}".format(receivedMessage))
    radio.read(receivedMessage, radio.getDynamicPayloadSize())
    d.callback(receivedMessage)
    return d

def convertBufferToUnicode(buffer):
    unicodeText = ""
    for n in buffer:
        # Decode into standard unicode set
        if (n >= 32 and n <= 126):
            unicodeText += chr(n)
    return unicodeText

def convertMessageToPostBody(message):
    data = {}
    if message.count('::') > 0:
        words = message.split("::")
        print("split message: " + str(words))
        data = {'uuid':words[0], 'sensor':words[1], 'value':words[2]}
    return data

def postMessageToServer(postBody):
    resp = requests.post('https://httpbin.org/post', data=postBody);
    print(resp.text);
    return resp

def shutdown(radio):
    radio.end()
 
def main():
    radio = NRF24Radio()
    radio.listen()

    print("About to start program loop")
    loop = task.LoopingCall(listenForData, radio)
    loop.start(0)

    print("Loop has started, going to run reactor")
    reactor.addSystemEventTrigger("before", "shutdown", shutdown, radio)
    reactor.run()

if __name__ == "__main__":
    main()
