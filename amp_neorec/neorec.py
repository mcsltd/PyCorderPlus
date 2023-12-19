import ctypes
import ctypes.wintypes
import _ctypes
import platform


class NeoRec:
    def __init__(self):
        # get OS architecture (32/64-bit)
        self.x64 = ("64" in platform.architecture()[0])

        # load NeoRec windows library
        self.lib = None
        self.loadLib()

    def loadLib(self):
        """
        Load windows library
        """
        # load ActiChamp 32 or 64 bit windows library
        try:
            # unload existing library
            if self.lib is not None:
                _ctypes.FreeLibrary(self.lib._handle)
                # load/reload library
            if self.x64:
                self.lib = ctypes.windll.LoadLibrary("amp_neorec/nb2mcs.dll")
        except:
            self.lib = None
            if self.x64:
                # raise AmpError("failed to open library (ActiChamp_x64.dll)")
                pass

    pass


if __name__ == "__main__":
    obj = NeoRec()
