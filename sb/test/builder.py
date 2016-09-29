from random import randint

def buildRangedOrdLists(callback, count, maxDeviceId, maxSensorId, maxReading, separator="::"):
    for _ in range(0, count):
        deviceId = randint(1, maxDeviceId)
        sensorId = randint(1, maxSensorId)
        reading = randint(1, maxReading)
        ordlist = buildOrdList(deviceId, sensorId, reading, separator)
        callback(ordlist)

def buildOrdList(deviceId, sensorId, reading, separator="::"):
    msg = separator.join([str(deviceId), str(sensorId),  str(reading)])
    return list(msg.encode())
