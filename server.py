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

    controller = SensorDataCollector(radio, readingsQueue)
    globalLog.info("Collector created")

    processorList = []
    processorList.append(WebServiceProcessor())
    processorList.append(DatabaseProcessor())
    processor = SensorDataProcessor(readingsQueue, processorList)
    globalLog.info("DataPocessor created")

    globalLog.info("About to start collector task")
    loop = task.LoopingCall(controller.listenForData)
    loop.start(.05)

    globalLog.info("About to start proecssor task")
    loop = task.LoopingCall(processor.processQueue)
    loop.start(5)

    globalLog.info("About to start the application server")

    reactor.suggestThreadPoolSize(20)
    reactor.addSystemEventTrigger("before", "shutdown", shutdown, radio)
    reactor.run()