
class RawSensorReadingDTO(object):
    __slots__ = ('buffer', 'time', 'uuid')
    def __init__(self, buffer, time, uuid=''):
        self.buffer = buffer
        self.time = time
        self.uuid = uuid

class SensorReadingDTO(object):
    __slots__ = ('deviceId', 'sensorId', 'reading', 'time', 'uuid')
    def __init__(self, deviceId, sensorId, reading, time, uuid=''):
        self.deviceId = deviceId
        self.sensorId = sensorId
        self.reading = reading
        self.time = time
        self.uuid = uuid
