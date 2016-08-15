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

    readingsQueue = Queue.Queue()
    globalLog.info("Queue created")

    collector = SensorDataCollector(radio, readingsQueue)
    globalLog.info("Collector created")

    processorList = []
    processorList.append(WebServiceProcessor())
    processorList.append(DatabaseProcessor())
    processor = SensorDataProcessor(readingsQueue, processorList)
    globalLog.info("DataPocessor created")

    collector.addConsumer(processor)

    radio.irqCallback(lambda _: reactor.callFromThread(collector.listenForData))

    #globalLog.info("About to start proecssor task")
    #loop = task.LoopingCall(processor.processQueue)
    #loop.start(5)

    globalLog.info("About to start the application server")

    reactor.suggestThreadPoolSize(20)
    reactor.addSystemEventTrigger("before", "shutdown", shutdown, radio)
    reactor.run()
