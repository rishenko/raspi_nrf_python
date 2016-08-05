from zope.interface import implementer
from twisted.internet.protocol import Factory
from twisted.internet.protocol import Protocol
from twisted.internet import interfaces, defer, error, fdesc, threads

import RPi.GPIO as GPIO
from lib_nrf24 import NRF24
import time
import spidev

@implementer(interfaces.IStreamServerEndpoint)
class RF24ReaderEndpoint(object):
    _radio = NRF24(GPIO, spidev.SpiDev())

    def __init__(self, reactor):
        GPIO.setmode(GPIO.BCM)
	pipes = [[0xE8, 0xE8, 0xF0, 0xF0, 0xE1], [0xF0, 0xF0, 0xF0, 0xF0, 0xE1], [0xF0, 0xF0, 0xF0, 0xF0, 0xE2]]

	_radio.begin(0, 17)

	_radio.setPayloadSize(32)
	_radio.setChannel(0x76)
	_radio.setDataRate(NRF24.BR_1MBPS)
	_radio.setPALevel(NRF24.PA_MIN)

	_radio.setAutoAck(True)
	_radio.enableDynamicPayloads()
	_radio.enableAckPayload()

	_radio.openReadingPipe(1, pipes[1])
	_radio.openReadingPipe(2, pipes[2])
	_radio.printDetails()

def listen(self, rf24ProtocolFactory):
	_radio.startListening()
