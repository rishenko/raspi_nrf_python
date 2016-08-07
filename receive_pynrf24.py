from nrf24 import NRF24
import time
import requests

pipes = [[0xE8, 0xE8, 0xF0, 0xF0, 0xE1], [0xF0, 0xF0, 0xF0, 0xF0, 0xE1]]

radio = NRF24()
#radio.begin(0, 8, 17, 18)
radio.begin(0, 0, 17, 18)
radio.setRetries(15,15)

radio.setPayloadSize(32)
radio.setChannel(0x76)

radio.setDataRate(NRF24.BR_250KBPS)
radio.setPALevel(NRF24.PA_MAX)

radio.setAutoAck(1)

#radio.setAutoAck(True)
radio.enableDynamicPayloads()
radio.enableAckPayload()

#radio.openWritingPipe(pipes[0])
radio.openReadingPipe(1, pipes[1])

radio.startListening()
radio.stopListening()

#time.sleep(50 / 1000)
radio.printDetails()

radio.startListening()

pipe = [0]

while(1):
    #while not radio.available(pipe, True):
    while not radio.available(pipe, False):
	radio.print_status(radio.get_status())
        time.sleep(10 / 1000)

    radio.print_status(radio.get_status())

    receivedMessage = []
    radio.read(receivedMessage) 
    print("Received: {}".format(receivedMessage))

#   print("Translating the receivedMessage into unicode characters")
    finalMessage = ""
    for n in receivedMessage:
        # Decode into standard unicode set
        if (n >= 32 and n <= 126):
            finalMessage += chr(n)

    print("Message: {}".format(finalMessage))
#SEND HTTP REQUESTS
    if finalMessage.count('::') > 0:
        words = finalMessage.split("::")
        print("split message: " + str(words))
        resp = requests.post('https://httpbin.org/post', data={'uuid':words[0], 'sensor':words[1], 'value':words[2]});
        print(resp.text);
