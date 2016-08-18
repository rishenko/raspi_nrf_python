from twisted import service, interfaces

class NRF24EndpointService(service.Service, object):
    def __init__(self, endpoint, factory):
        self.endpoint = endpoint
        self.factory = factory
        self._waitingForPort = None


    def privilegedStartService(self):
        """
        Start listening on the endpoint.
        """
        service.Service.privilegedStartService(self)
        self._waitingForPort = self.endpoint.listen(self.factory)
        raisedNow = []
        def handleIt(err):
            if self._raiseSynchronously:
                raisedNow.append(err)
            elif not err.check(CancelledError):
                log.err(err)
        self._waitingForPort.addErrback(handleIt)
        if raisedNow:
            raisedNow[0].raiseException()

    def startService(self):
        """
        Start listening on the endpoint, unless L{privilegedStartService} got
        around to it already.
        """
        service.Service.startService(self)
        if self._waitingForPort is None:
            self.privilegedStartService()

@implementer(interfaces.IStreamServerEndpoint)
class NRF24ServerEndpoint(object):
    def __init__(self, reactor):
        self._reactor = reactor

    def listen(self, protocolFactory):
        return defer.execute(self.listenNRF)

    def listenNRF(self):
        p = NRF24Port()
        p.startListening()
        return p

@implementer(interfaces.IListeningPort)
class NRF24Port(object):
    def __init__(self, radio):
        self._radio = radio

    def startListening():
        """
        Start listening on this port.
        @raise CannotListenError: If it cannot listen on this port (e.g., it is
                                  a TCP port and it cannot bind to the required
                                  port number).
        """
        self._radio.listen()


    def stopListening():
        """
        Stop listening on this port.
        If it does not complete immediately, will return Deferred that fires
        upon completion.
        """
        self._radio.end()

    def getHost():
        """
        Get the host that this port is listening for.
        @return: An L{IAddress} provider.
        """
