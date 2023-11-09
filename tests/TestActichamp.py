import numpy as np
import unittest
import time
from actichamp_w import ActiChamp


class TestActiChamp(unittest.TestCase):

    def setUp(self):
        self.amp = ActiChamp()

    def test_01_loadLib(self):
        """
        Сhecking DLL library loading.
        :return:
        """
        self.assertIsNotNone(self.amp.lib)

    def test_02_get_data(self):
        d = None
        self.amp.open()
        if self.amp.devicehandle != 0:
            self.amp.start()
            time.sleep(0.1)
            d, disconnected = self.amp.read(
                indices=np.array([0, 1]),
                eegcount=2,
                auxcount=0
            )
            self.amp.stop()
        self.amp.close()
        self.assertIsNotNone(d)


if __name__ == "__main__":
    unittest.main()
