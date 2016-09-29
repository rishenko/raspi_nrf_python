import threading, queue
from sb import util, radio, collector, processor
from sb.radio import NRF24Radio
from sb.collector import SensorDataCollector
from sb.network.radio import NRFProtocolFactory, NRFProtocol
from twisted.application import service, internet

from twisted.internet import reactor, task
from sb.util import Log

globalLog = Log().buildLogger()

#handle shutting down all the things
def shutdown(radio):
    radio.end()
    globalLog.info("Finished shutting down the radio and GPIO.")

#if __name__ == "__main__":
globalLog.info("Starting up NRF24 radio")
radio = NRF24Radio()
collector = SensorDataCollector(radio)
globalLog.info("Collector created")

factory = NRFProtocolFactory()
collector.addConsumer(factory)

radio.irqCallback(lambda _: reactor.callFromThread(collector.listenForData))

globalLog.info("Setting server configuration properties.")
reactor.suggestThreadPoolSize(20)
reactor.addSystemEventTrigger("before", "shutdown", shutdown, radio)
reactor.callWhenRunning(radio.listen)

application = service.Application("radio server")

globalLog.info("About to start the application server")
internet.TCPServer(1025, factory, interface='192.168.1.68').setServiceParent(application)

#Run with: twistd -noy server_radio.tac
#For testing in P3, run python3 -m twisted.trial sb
