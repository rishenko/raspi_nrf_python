import uuid

class UUID_DTO(object):
    _uuid=None
    def __init__(self, uuidVal=None):
        if uuidVal == None:
            self._uuid = uuid.uuid1().hex
        else:
            self._uuid = uuidVal

    def getUUID(self):
        return self._uuid

    def getShortUUID(self):
        return self._uuid[:13]

class RawSensorReadingDTO(UUID_DTO):
    def __init__(self, buffer, time, uuid=None):
        super(RawSensorReadingDTO, self).__init__(uuid)
        self.buffer = buffer
        self.time = time

class SensorReadingDTO(UUID_DTO):
    def __init__(self, deviceId, sensorId, reading, time, uuid=None):
        super(SensorReadingDTO, self).__init__(uuid)
        self.deviceId = deviceId
        self.sensorId = sensorId
        self.reading = reading
        self.time = time

    # Convert objects to a dictionary of their representation
    def convert_to_builtin_type(obj):
        d = {}
        d.update(obj.__dict__)
        return d
