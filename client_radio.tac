import threading, Queue
from sb import util, processor
from sb.network.receiving import ReceivingProtocolFactory, ReceivingProtocol
from twisted.application import service, internet

from twisted.internet import reactor, task
from twisted.application import internet
from twisted.internet.endpoints import clientFromString
from sb.util import Log

globalLog = Log().buildLogger()

#if __name__ == "__main__":
globalLog.info("Starting up NRF24 radio")
dataProcessor = processor.SensorDataProcessor()
dataProcessor.addConsumer(processor.DatabaseProcessor(Queue.Queue()))
globalLog.info("Collector created")

recFactory = ReceivingProtocolFactory()
recFactory.addConsumer(dataProcessor)

globalLog.info("About to start the application server")
application = service.Application("radio server")
internet.TCPClient('192.168.1.68', 1025, recFactory).setServiceParent(application)

#Run with: twistd -noy client_radio.tac
