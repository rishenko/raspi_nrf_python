import threading, Queue
from sb import util, radio, collector, processor
from sb.radio import NRF24Radio
from sb.collector import SensorDataCollector
from sb.processor import SensorDataProcessor, WebServiceProcessor, DatabaseProcessor

from twisted.internet import reactor, task
from sb.util import Log

globalLog = Log().buildLogger()

#handle shutting down all the things
def shutdown(radio):
    radio.end()
    globalLog.info("Finished shutting down the radio and GPIO.")

if __name__ == "__main__":
    globalLog.info("Startin up NRF24 radio")
    radio = NRF24Radio()
    radio.listen()

    collector = SensorDataCollector(radio)
    globalLog.info("Collector created")

    processor = SensorDataProcessor()
    processor.addConsumer(WebServiceProcessor())
    processor.addConsumer(DatabaseProcessor())

    collector.addConsumer(processor)

    radio.irqCallback(lambda _: reactor.callFromThread(collector.listenForData))

    globalLog.info("About to start the application server")

    reactor.suggestThreadPoolSize(20)
    reactor.addSystemEventTrigger("before", "shutdown", shutdown, radio)
    reactor.run()
