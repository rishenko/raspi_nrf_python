from random import randint

def buildRangedOrdLists(callback, count, maxDeviceId, maxSensorId, maxReading, separator="::"):
    for _ in range(0, count):
        deviceId = randint(1, maxDeviceId)
        sensorId = randint(1, maxSensorId)
        reading = randint(1, maxReading)
        ordlist = buildOrdList(deviceId, sensorId, reading, separator)
        callback(ordlist)

def buildOrdList(deviceId, sensorId, reading, separator="::"):
    deviceIdL = stringToOrds(deviceId)
    sensorIdL = stringToOrds(sensorId)
    readingL = stringToOrds(reading)
    sepL = stringToOrds(separator)
    buffer = deviceIdL + sepL + sensorIdL + sepL + readingL +  [0]
    return buffer

def stringToOrds(message):
    return map(ord, list(str(message)))
