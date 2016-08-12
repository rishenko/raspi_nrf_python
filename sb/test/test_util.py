from sb.util import convertToDict, Log
from twisted.trial import unittest

class SimpleDTO(object):
    def __init__(self):
        self.a = "a"
        self.b = "b"
        self.c = "c"

class UtilTests(unittest.TestCase):
    log = Log().buildLogger()

    def test_convertToDict(self):
        dtoDict = convertToDict(SimpleDTO())
        self.assertEquals(dtoDict, {'a':'a', 'c':'c', 'b':'b'})
