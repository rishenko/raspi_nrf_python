from nrf24 import NRF24
from util import Log

from twisted.internet import reactor, task, defer, threads
from twisted.internet.defer import inlineCallbacks, returnValue


# Extending the NRF24 library to encapsulate basic settings
class NRF24Radio(NRF24):
    log = Log().buildLogger()
    IRQ_PIN = 19

    def __init__(self, GPIO, spidev):
        self._GPIO = GPIO
        pipes = [[0xE8, 0xE8, 0xF0, 0xF0, 0xE1], # writing address
                 [0xF0, 0xF0, 0xF0, 0xF0, 0xE1]] # reading address - sensors write to this

        self._GPIO.setmode(self._GPIO.BCM)
        self._GPIO.setup(IRQ_PIN, self._GPIO.IN, pull_up_down=self._GPIO.PUD_UP)

        super(NRF24Radio, self).__init__(self._GPIO, spidev.SpiDev())
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

    def irqCheck():
        return self._GPIO.input(IRQ_PIN)

    def readMessageToBuffer(self):
        receivedMessage = []
        #self.print_status(self.get_status())
        self.read(receivedMessage, self.getDynamicPayloadSize())
        return receivedMessage

# Handle the transformation of incoming data from NRF24 transceivers
class NRF24DataTransformer(object):
    log = Log().buildLogger()

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
    log = Log().buildLogger()

    def __init__(self, uid):
        self._uid = uid

    def convertMessageToDictionary(self, message, timestamp):
        self.log.debug(self._uid + ": convertMessageToPostBody")
        return defer.execute(self._convertMessageToDictionary, message, timestamp)

    def _convertMessageToDictionary(self, message, timestamp):
        if message.count('::') > 1:
            words = message.split("::")
            self.log.debug(self._uid + ": split message: " + str(words))
        #deviceId, sensorId, reading, time
        datum = ReadingDatum(words[0], words[1], words[2], timestamp)
        return datum

class RawReadingDatum(object):
    def __init__(self, buffer, time):
        self.buffer = buffer
        self.time = time


class ReadingDatum(object):
    def __init__(self, deviceId, sensorId, reading, time):
        self.deviceId = deviceId
        self.sensorId = sensorId
        self.reading = reading
        self.time = time
