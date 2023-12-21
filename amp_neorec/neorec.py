import ctypes
import ctypes.wintypes
import _ctypes
import platform
import time

# NeoRec base sample rate enum
NR_RATE_125HZ = 0
NR_RATE_250HZ = 1
NR_RATE_500HZ = 2
NR_RATE_1000HZ = 3

# sample rate freq. dictionary
sample_rate = {
    NR_RATE_125HZ: 125.0,
    NR_RATE_250HZ: 250.0,
    NR_RATE_500HZ: 500.0,
    NR_RATE_1000HZ: 1000.0,
}

# adc input rage in mV enum
NR_RANGE_mV150 = 0
NR_RANGE_mV300 = 1

# adc input dictionary
dynamic_range = {
    150.0: NR_RANGE_mV150,
    300.0: NR_RANGE_mV300
}

# C error numbers
NR_ERR_OK = 0  # Success (no errors)
NR_ERR_ID = -1  # Invalid id
NR_ERR_FAIL = -2  # Operation failed
NR_ERR_PARAM = -3  # Incorrect argument
NR_ERR_OBTAINED = -4  # Error receiving data from device
NR_ERR_SUPPORT = -5  # Function is not defined for the connected device

# program working mode enum
NR_MODE_DATA = 0
NR_MODE_IMPEDANCE = 1


class t_nb2Date(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ('Year', ctypes.c_uint16),
        ('Month', ctypes.c_uint8),
        ('Day', ctypes.c_uint8)
    ]


class t_nb2Information(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ('Model', ctypes.c_uint32),
        ('SerialNumber', ctypes.c_uint32),
        ('ProductionDate', t_nb2Date)
    ]


class t_nb2Property(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("Rate", ctypes.c_float),
        ("Resolution", ctypes.c_float),
        ("Range", ctypes.c_float)
    ]


class t_nb2DataStatus(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("Rate", ctypes.c_float),
        ("Speed", ctypes.c_float),
        ("Ratio", ctypes.c_float),
        ("Utilization", ctypes.c_float),
    ]


class t_nb2Possibility(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("ChannelsCount", ctypes.c_uint32),
        ("UserMemorySize", ctypes.c_uint32),
    ]


class t_nb2Settings(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ('DataRate', ctypes.c_uint8),
        ('InputRange', ctypes.c_uint8),
        ('EnabledChannels', ctypes.c_uint32)
    ]


class t_nb2Mode(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("Mode", ctypes.c_uint8)
    ]


class t_nb2EventSettings(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ('EnabledEvents', ctypes.c_uint16),
        ('ActivityThreshold', ctypes.c_uint16)
    ]


# channel names for NeoRec 21 and NeoRec21S devices
NR_NAME_CHANNEL_EEG21 = ["Fp1", "Fp2", "F3", "F4", "C3", "C4", "P3",
                         "P4", "O1", "O2", "F7", "F8", "T3", "T4",
                         "T5", "T6", "A1", "A2", "Fz", "Cz", "Pz"]

NR_NAME_CHANNEL_EEG21S = ["C4", "A2", "F8", "T6", "F4", "P4", "Fp2",
                          "O2", "Cz", "Pz", "Fz", "O1", "Fp1", "P3",
                          "F3", "T5", "F7", "A1", "C3", "T3", "T4"]


class NeoRec:
    def __init__(self):
        # get OS architecture (64-bit)
        self.x64 = ("64" in platform.architecture()[0])

        self.id = 0  # Device id

        self.open_ble = False  # BLE device connected
        self.running = False  # Data acquisition running
        self.model = None

        # info has Model, SerialNumber, ProductionDate
        self.info = t_nb2Information()

        # set default properties
        self.settings = t_nb2Settings()
        self.settings.DataRate = NR_RATE_125HZ  #: sampling rate
        self.settings.InputRange = NR_RANGE_mV150  #: input range
        self.settings.EnabledChannels = 0x001FFFFF  #: enabled channels

        # set default mode
        self.mode = t_nb2Mode()  #: NeoRecCap settings mode structure
        self.mode.Mode = NR_MODE_DATA

        # set event settings
        self.eset = t_nb2EventSettings()
        self.eset.EnabledEvents = 0x003F
        self.eset.ActivityThreshold = 0

        self.CountEeg = 21
        self.CountAux = 0

        # load NeoRec windows library
        self.lib = None
        self.loadLib()

    def loadLib(self):
        """
        Load windows library
        """
        # load NeoRec 64 bit windows library
        try:
            # unload existing library
            if self.lib is not None:
                _ctypes.FreeLibrary(self.lib._handle)
                # load/reload library
            if self.x64:
                path = r"C:\Users\andmo\OneDrive\Desktop\my-dev-work\PyCorderPlus\amp_neorec\nb2mcs.dll"
                self.lib = ctypes.windll.LoadLibrary(path)
        except:
            self.lib = None
            if self.x64:
                # raise AmpError("failed to open library (ActiChamp_x64.dll)")
                pass

        # initialization library resources
        res = self.lib.nb2ApiInit()
        if res != NR_ERR_OK:
            # AmpError("can't initialize library resources")
            pass

    def open(self):
        """
        Open the hardware device
        @return res: result of opening the device
        """
        if self.running:
            return
        if self.lib is None:
            # raise AmpError("library nb2mcs.dll not available")
            return

        while not self.open_ble:
            # get the number of devices on the network
            c = self.lib.nb2GetCount()
            if c > 0:
                # get index device with number 1
                self.id = self.lib.nb2GetId(0)
                # open this device
                err = self.lib.nb2Open(self.id)
                if err != NR_ERR_OK:
                    self.open_ble = True

        # get information about open device
        err = self.lib.nb2GetInformation(self.id, ctypes.byref(self.info))

        if err != NR_ERR_OK:
            pass

        return err

    def stop(self):
        """
        Stop data acquisition
        """
        if not self.running:
            return
        self.running = False
        if self.id is None:
            # raise AmpError("device not open")
            pass
        err = self.lib.nb2Stop(self.id)
        if err != NR_ERR_OK:
            # raise AmpError("failed to stop device", err)
            pass

    def close(self):
        """
        Close hardware device
        """
        if self.lib is None:
            # raise AmpError("library ActiChamp_x86.dll not available")
            return

        if self.id != 0:

            if self.running:
                self.stop()

            err = self.lib.nb2Close(self.id)

            if err == NR_ERR_OK:
                self.lib.nb2ApiDone()

    def getSamplingRateBase(self, samplingrate):
        ''' Get base sampling rate ID and divider for the requested sampling rate
        @param samplingrate: requested sampling rate in Hz
        @return: base rate ID (-1 if not possible) and base rate divider
        '''
        mindiv = 100000
        base = -1
        div = 1
        for sr in sample_rate:
            div = sample_rate[sr] / samplingrate
            if int(div) == div:
                if div < mindiv:
                    mindiv = div
                    base = sr
        if base >= 0:
            div = int(sample_rate[base] / samplingrate)
        return base, div

    def getDynamicRangeBase(self, range):
        """
        Get base sampling rate ID and divider for the requested sampling rate
        :param range: Numeric range value
        :return range number in the dictionary
        """
        base = -1
        if range in dynamic_range:
            base = dynamic_range[range]
        return base

    def readConfiguration(self, rate, range, force=False):
        """
        Update device sampling rate, dymamic range and get new configuration
        @param rate: device base sampling rate
        :param force:
        :param range:
        """
        # not possible if device is already open or not necessary if rate or range has not changed
        if (self.id != 0 or rate == self.settings.DataRate or range == self.settings.InputRange) and not force:
            return
        # update sampling rate and get new configuration
        try:
            self.setup(self.mode.Mode, rate, range)
        except:
            pass

        try:
            self.close()
        except:
            pass

    def setup(self, mode, rate, range):
        """
        Prepare device for acquisition
        :param mode: device mode, one of NR_MODE_ values
        :param rate: device sampling rate, one of NR_RATE_ values
        :param range: device dynamic range, one of NR_RATE_ values
        """


        # set amplifier settings
        self.settings.DataRate = rate
        self.settings.InputRanges = range
        # transfer settings to amplifier
        err = self.lib.nb2SetDataSettings(self.id, ctypes.byref(self.settings))

        if err != NR_ERR_OK:
            pass

        # set event settings
        err = self.lib.nb2SetEventSettings(self.id, ctypes.byref(self.eset))

        if err != NR_ERR_OK:
            pass

        # set amplifier mode
        self.mode.Mode = mode
        # transfer mode to amplifier
        err = self.lib.nb2SetMode(self.id, ctypes.byref(self.mode))

        if err != NR_ERR_OK:
            pass

# if __name__ == "__main__":
#     obj = NeoRec()
#     print(obj.info.Model)
#     obj.open()
#     print(obj.info.Model)
