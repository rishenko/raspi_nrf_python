import json

class RawSensorReadingDTO(object):
    __slots__ = ('buffer', 'time', 'uuid')
    def __init__(self, buffer, time, uuid=''):
        self.buffer = buffer
        self.time = time
        self.uuid = uuid

    def json_serialize(self):
        return {'buffer':self.buffer,'time':self.time,'uuid':self.uuid}

    @staticmethod
    def json_deserialize(jsonStr):
        data = json.loads(jsonStr)
        return RawSensorReadingDTO(data['buffer'], data['time'], data['uuid'])

class SensorReadingDTO(object):
    __slots__ = ('deviceId', 'sensorId', 'reading', 'time', 'uuid')
    def __init__(self, deviceId, sensorId, reading, time, uuid=''):
        self.deviceId = deviceId
        self.sensorId = sensorId
        self.reading = reading
        self.time = time
        self.uuid = uuid

    def json_serialize(self):
        return {'deviceId':self.deviceId,'sensorId':self.sensorId,
                'reading':self.reading,'time':self.time,'uuid':self.uuid}

    @staticmethod
    def json_deserialize(jsonStr):
        data = json.loads(jsonStr)
        return SensorReadingDTO(data['deviceId'], data['sensorId'],
                                data['reading'], data['time'], data['uuid'])
