import unittest
from actichamp_w import ActiChamp


class TestActiChamp(unittest.TestCase):

    def setUp(self):
        self.amp = ActiChamp()

    def test_loadLib(self):
        self.assertIsNotNone(self.amp.lib)


if __name__ == "__main__":
    unittest.main()