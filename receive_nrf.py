import RPi.GPIO as GPIO
from lib_nrf24 import NRF24
import time
import spidev
import requests

GPIO.setmode(GPIO.BCM)

pipes = [[0xE8, 0xE8, 0xF0, 0xF0, 0xE1], 
         [0xF0, 0xF0, 0xF0, 0xF0, 0xE1]]

radio = NRF24(GPIO, spidev.SpiDev())
radio.begin(0, 17)

radio.setPayloadSize(32)
radio.setChannel(0x76)
radio.setDataRate(NRF24.BR_1MBPS)
radio.setPALevel(NRF24.PA_MIN)

radio.setAutoAck(True)
radio.enableDynamicPayloads()
radio.enableAckPayload()

radio.openReadingPipe(1, pipes[1])
radio.printDetails()
radio.startListening()


while(1):
    start = time.time()
    while not radio.available(0):
        time.sleep(1 / 1000)
        if time.time() - start > 2:
            print("Timed out.")
            break
    receivedMessage = []
    radio.print_status(radio.get_status())
    radio.read(receivedMessage, radio.getDynamicPayloadSize())
#    print("Received: {}".format(receivedMessage))

#    print("Translating the receivedMessage into unicode characters")
    finalMessage = ""
    for n in receivedMessage:
        # Decode into standard unicode set
        if (n >= 32 and n <= 126):
            finalMessage += chr(n)

    print("Message: {}".format(finalMessage))
#SEND HTTP REQUESTS
#    if finalMessage.count('::') > 0:
#        words = finalMessage.split("::")
#        print("split message: " + str(words))
#        resp = requests.post('https://httpbin.org/post', data={'uuid':words[0], 'sensor':words[1], 'value':words[2]});
#        print(resp.text);
