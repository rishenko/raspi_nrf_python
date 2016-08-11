import Adafruit_GPIO.GPIO as GPIO
from nrf24 import NRF24
from util import Log

from twisted.internet import reactor, task, defer, threads
from twisted.internet.defer import inlineCallbacks, returnValue

# Extending the NRF24 library to encapsulate basic settings
class NRF24Radio(NRF24):
    log = Log().buildLogger()
    IRQ_PIN = 19

    def __init__(self):
        self._gpio = GPIO.get_platform_gpio()
        pipes = [[0xE8, 0xE8, 0xF0, 0xF0, 0xE1], # writing address
                 [0xF0, 0xF0, 0xF0, 0xF0, 0xE1]] # reading address - sensors write to this

        self._gpio.setup(NRF24Radio.IRQ_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        super(NRF24Radio, self).__init__()
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

    def irqCheck(self):
        return self._gpio.input(NRF24Radio.IRQ_PIN)

    def readMessageToBuffer(self):
        receivedMessage = []
        #self.print_status(self.get_status())
        self.read(receivedMessage, self.getDynamicPayloadSize())
        return receivedMessage


class ReadingDatum(object):
    def __init__(self, deviceId, sensorId, reading, time):
        self.deviceId = deviceId
        self.sensorId = sensorId
        self.reading = reading
        self.time = time
