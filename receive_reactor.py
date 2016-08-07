import RPi.GPIO as GPIO
from lib_nrf24 import NRF24
import time
import spidev
import requests
from twisted.internet import reactor, task

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

def listenForData(radio):
    if not radio.available(0):
	return

    buffer = readMessageToBuffer()
    message = convertBufferToUnicode(buffer)
    jsonMessage = convertMessageToPostBody(message)
    response = postMessageToServer(jsonMessage)

def readMessageToBuffer():
    receivedMessage = []
    radio.print_status(radio.get_status())
    radio.read(receivedMessage, radio.getDynamicPayloadSize())
    #print("Received: {}".format(receivedMessage))
    return receivedMessage

def convertBufferToUnicode(buffer):
    #print("Translating the receivedMessage into unicode characters")
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
 
radio = NRF24Radio()
radio.listen()

loop = task.LoopingCall(listenForData, radio)
loop.start(1.0)
reactor.run()
