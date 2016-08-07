import RPi.GPIO as GPIO
import uuid

from lib_nrf24 import NRF24
import spidev

from twisted.internet import reactor, task, defer
from twisted.internet.defer import inlineCallbacks, returnValue

import json
import treq

GPIO.setmode(GPIO.BCM)
pipes = [[0xE8, 0xE8, 0xF0, 0xF0, 0xE1], 
         [0xF0, 0xF0, 0xF0, 0xF0, 0xE1]]

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

@inlineCallbacks
def listenForData(radio):
    if not radio.available(0):
        return

    uid = str(uuid.uuid1())
    print(uid + ": listenForData start")

    # Process the incoming data from the radio
    buffer = yield readMessageToBuffer(radio, uid)
    message = yield convertBufferToUnicode(buffer, uid)

    # Convert the message to a format that can be sent elsewhere
    jsonMessage = yield convertMessageToPostBody(message, uid)
    response = yield postMessageToServer(jsonMessage, uid)

    # Process the response back from the remote server
    yield processServerResponse(response, uid)

    print(uid + ": listenForData end")

def readMessageToBuffer(radio, uid):
    print(uid + ": readMessageToBuffer")
    d = defer.Deferred()
    receivedMessage = []
    radio.print_status(radio.get_status())
    radio.read(receivedMessage, radio.getDynamicPayloadSize())
    print("Received: {}".format(receivedMessage))

    d.callback(receivedMessage)
    return d

def convertBufferToUnicode(buffer, uid):
    print(uid + ": convertBufferToUnicode")
    unicodeText = ""
    for n in buffer:
        # Decode into standard unicode set
        if (n >= 32 and n <= 126):
            unicodeText += chr(n)
    return unicodeText

def convertMessageToPostBody(message, uid):
    print(uid + ": convertMessageToPostBody")
    data = {}
    if message.count('::') > 0:
        words = message.split("::")
        print("split message: " + str(words))
        data = {'uuid':words[0], 'sensor':words[1], 'value':words[2]}
    return data

@inlineCallbacks
def postMessageToServer(postBody, uid):
    print(uid + ": postMessageToServer")
    resp = yield treq.post('https://httpbin.org/post',
                           json.dumps(postBody),
                           headers={'Content-Type': ['application/json']}) 
    returnValue(resp)

def processServerResponse(response, uid):
    print(uid + ": processServerResponse")
    response.json().addCallback(printResponse, uid)

def printResponse(responseJson, uid):
    print(uid + ": printResponse")
    print(uid + ": " + "Response: " + json.dumps(responseJson, sort_keys=True,
                                    indent=4, separators=(',', ': ')))

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
