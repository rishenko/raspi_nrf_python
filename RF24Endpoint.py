from zope.interface import implementer
from twisted.internet.protocol import Factory
from twisted.internet.protocol import Protocol
from twisted.internet import interfaces, defer, error, fdesc, threads, reactor, protocol

import RPi.GPIO as GPIO
from lib_nrf24 import NRF24
import time
import spidev

@implementer(interfaces.IStreamServerEndpoint)
class RF24ReaderEndpoint(object):

    def __init__(self, reactor):
        self._reactor = reactor

        GPIO.setmode(GPIO.BCM)
	pipes = [[0xE8, 0xE8, 0xF0, 0xF0, 0xE1], [0xF0, 0xF0, 0xF0, 0xF0, 0xE1]]

        self._radio = NRF24(GPIO, spidev.SpiDev())
	self._radio.begin(0, 17)

	self._radio.setPayloadSize(32)
	self._radio.setChannel(0x76)
	self._radio.setDataRate(NRF24.BR_1MBPS)
	self._radio.setPALevel(NRF24.PA_MIN)

	self._radio.setAutoAck(True)
	self._radio.enableDynamicPayloads()
	self._radio.enableAckPayload()

	self._radio.openReadingPipe(1, pipes[1])
	#_radio.openReadingPipe(2, pipes[2])
	self._radio.printDetails()

    def listen(self, rf24ProtocolFactory):
        return defer.execute(rfCallable, 
    			     rf24ProtocolFactory,
			     self._radio,
			     pipe)

def rfCallable(factory, radio, pipe):
    rf24 = RF24ListeningPort(radio, factory) 
    rf24.startListening()
    return rf24

@implementer(interfaces.ITransport)
class RF24Transport:
    def __init__(self, protocol):
        self._proto = protocol

@implementer(interfaces.IListeningPort)
class RF24ListeningPort:
    def __init__(self, radio, factory):
        self._radio = radio
        self._factory = factory

    def startListening(self):
        _radio.startListening()     

#    def doRead(self):
        

class RF24ServerFactory(Factory):
    def __init__(self, radio):
        self._radio = radio 

    def buildProtocol(self):
       return RF24Protocol(self._radio)
    

class RF24Protocol(protocol.Protocol):
    def __init__(self, radio):
        self._radio = radio

    #def makeConnection(self, transport):
    #    protocol.Protocol.makeConnection(self, transport)

    def dataReceived(self, data):
        receivedMessage = []
        radio.print_status(radio.get_status())
        radio.read(receivedMessage, radio.getDynamicPayloadSize())
#       print("Received: {}".format(receivedMessage))

#       print("Translating the receivedMessage into unicode characters")
        finalMessage = ""
        for n in receivedMessage:
            # Decode into standard unicode set
            if (n >= 32 and n <= 126):
                finalMessage += chr(n)        

        self.transport.write(finalMessage)

endpoint = RF24ReaderEndpoint(reactor)
#endpoint.listen(RF24Factory())
reactor.run()
