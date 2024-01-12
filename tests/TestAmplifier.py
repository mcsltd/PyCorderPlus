import unittest

from amp_actichamp.amplifier_actichamp import *


class TestAmplifier(unittest.TestCase):

    def setUp(self):
        self.obj_t = AMP_ActiChamp()
        self.obj_r = Receiver()
        # connect the transmitter to the receiver
        self.obj_t.add_receiver(self.obj_r)

    def test_0_get_data(self):
        # start amplifier
        self.obj_t.start()

        # attempt to receive data from the amplifier
        d = self.obj_r.get_data()
        while d is None:
            time.sleep(0.5)
            d = self.obj_r.get_data()

        self.obj_t.stop()
        self.obj_t.amp.close()
        self.assertIsNotNone(d)


if __name__ == "__main__":
    unittest.main()
