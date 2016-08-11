import Adafruit_GPIO as GPIO
import spidev
import threading, Queue
from sb import util, radio, collector, processor

from twisted.internet import reactor, task
from sb.util import Log

globalLog = Log.buildLogger()

#handle shutting down all the things
def shutdown(radio):
    radio.end()
    GPIO.cleanup()
    globalLog.info("Finished shutting down the radio and GPIO.")

if __name__ == "__main__":
    globalLog.info("Startin up NRF24 radio")
    radio = NRF24Radio(GPIO, spidev)
    radio.listen()

    readingsQueue = Queue.Queue()
    globalLog.info("Queue created")

    controller = SensorDataCollector(radio, reactor, readingsQueue)
    globalLog.info("Collector created")

    processor = SensorDataProcessor(readingsQueue)
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
