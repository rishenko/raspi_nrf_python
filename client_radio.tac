import threading, Queue
from sb import util, processor
from sb.network.receiving import ReceivingProtocolFactory, ReceivingProtocol
from sb.network.websocket import SensorDataClientFactory, SensorDataClientProtocol
from twisted.application import service, internet

from twisted.internet import reactor, task
from twisted.application import internet
from twisted.internet.endpoints import clientFromString
from sb.util import Log

from autobahn.twisted.websocket import connectWS

globalLog = Log().buildLogger()

globalLog.info("Building Processor")
dataProcessor = processor.SensorDataProcessor()
dataProcessor.addConsumer(processor.DatabaseProcessor(Queue.Queue()))
#dataProcessor.addConsumer(processor.WebServiceProcessor())

globalLog.info("Building Protocols and Factories")
recFactory = ReceivingProtocolFactory()
recFactory.addConsumer(dataProcessor) # processor consumes incoming socket data

wsFactory = SensorDataClientFactory("ws://echo.websocket.org")
dataProcessor.addConsumer(wsFactory) # WS consumes processed reading objs

globalLog.info("About to start the application server")
application = service.Application("radio server")
#internet.TCPClient('104.59.236.94', 1025, recFactory).setServiceParent(application)
#internet.TCPClient('192.168.1.68', 1025, recFactory).setServiceParent(application)
internet.TCPClient('192.168.1.148', 1025, recFactory).setServiceParent(application)
connectWS(wsFactory)

#Run with: twistd -noy client_radio.tac
