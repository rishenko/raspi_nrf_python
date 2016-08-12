from sb.dto import UUID_DTO
from twisted.trial import unittest


class FakeDTO(UUID_DTO):
    def __init__(self, val1, uuid=None):
        super(FakeDTO, self).__init__(uuid)
        self.val1 = val1

class ProcessorTests(unittest.TestCase):

    def testUUIDTokenNoUUIDArg(self):
        dto = FakeDTO("value")
        self.assertEqual(dto.val1, "value")
        self.assertEqual(len(dto.getUUID()), 32)
        self.assertEqual(len(dto.getShortUUID()), 13)

    def testUUIDTokenWithUUIDArg(self):
        dto = FakeDTO("value", "uuid-val")
        self.assertEqual(dto.val1, "value")
        self.assertEqual(dto.getUUID(), "uuid-val")
        self.assertEqual(dto.getShortUUID(), "uuid-val")
        print(dto.getShortUUID())
