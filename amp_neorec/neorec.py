import ctypes
import ctypes.wintypes
import _ctypes
import platform
import time
import numpy as np

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

# Mode text
NR_Modes = {
    NR_MODE_DATA: "acquisition",
    NR_MODE_IMPEDANCE: "impedance measurement"
}


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

# NeoRec amplifier models
NR_21 = 1902
NR_MINI = 1904
NR_CAP_1 = 1900
NR_CAP_2 = 1900
NR_Models = {
    NR_CAP_1: "NeoRec cap",
    NR_CAP_2: "NeoRec cap",
    NR_21: "NeoRec 21",
    NR_MINI: "NeoRec mini",
}

class AmpError(Exception):
    """
    Generic amplifier exception
    """
    def __init__(self, value, errornr=0):
        errortext = ""
        if errornr == NR_ERR_ID:
            errortext = "Invalid device ID"
        elif errornr == NR_ERR_FAIL:
            errortext = "Error while executing function"
        elif errornr == NR_ERR_PARAM:
            errortext = "Invalid parameter when calling a function"
        elif errornr == NR_ERR_OBTAINED:
            errortext = "Error when receiving service or feature"
        elif errornr == NR_ERR_SUPPORT:
            errortext = "Function is not supported"
        errortext = errortext + " :%i" % errornr
        if errornr != 0:
            self.value = "NeoRec: " + str(value) + " -> " + errortext
        else:
            self.value = "NeoRec: " + str(value)

    def __str__(self):
        return self.value


class NeoRec:
    def __init__(self):
        # get OS architecture (64-bit)
        self.x64 = ("64" in platform.architecture()[0])

        # set default values
        self.id = 0  # Device id
        self.connected = False  # Connected to amplifier
        self.running = False  # Data acquisition running
        self.readError = False  # an error occurred during data acquisition
        self.buffer = ctypes.create_string_buffer(10000 * 1024)  #: raw data transfer buffer

        self.properties = t_nb2Property()  # NeoRec property structure
        self.impbuffer = ctypes.create_string_buffer(1000)  #: impedance raw data transfer buffer

        # info has Model, SerialNumber, ProductionDate
        self.info = t_nb2Information()

        self.sampleCounterAdjust = 0  #: sample counter wrap around, HW counter is 32bit value but we need 64bit
        self.BlockingMode = True  #: read data in blocking mode

        # binning buffer for max. 100 samples with 21 channels with a datasize of int32 (4 bytes)
        self.binning_buffer = ctypes.create_string_buffer(100 * 21 * 4)  #: binning buffer
        self.binning = 1  #: binning size for buffer alignment
        self.binning_offset = 0  #: raw data buffer offset in bytes for binning

        # set default properties
        self.settings = t_nb2Settings()
        self.settings.DataRate = NR_RATE_500HZ  #: sampling rate
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
                self.lib = ctypes.windll.LoadLibrary(r"./amp_neorec/nb2mcs_x64.dll")
            else:
                self.lib = ctypes.windll.LoadLibrary(r"./amp_neorec/nb2mcs_x86.dll")
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
            # raise AmpError("library nb2mcs_x64.dll not available")
            return

        while not self.connected:
            # get the number of devices on the network
            c = self.lib.nb2GetCount()
            if c > 0:
                # get index device with number 1
                self.id = self.lib.nb2GetId(0)
                # open this device
                err = self.lib.nb2Open(self.id)
                if err == NR_ERR_OK:
                    self.connected = True

        # get information about open device
        err = self.lib.nb2GetInformation(self.id, ctypes.byref(self.info))
        if err != NR_ERR_OK:
            return False
        else:
            # get the NeoRec amp model and serial number
            self.model = self.info.Model
            self.sn = self.info.SerialNumber

        # get device properties
        err = self.lib.nb2GetProperty(self.id, ctypes.byref(self.properties))
        if err != NR_ERR_OK:
            return False

        return True

    def start(self):
        """
        Start data acquisition
        :return:
        """
        if self.running:
            return
        if self.id == 0:
            raise

        # start amplifier
        err = self.lib.nb2Start(self.id)
        if err != NR_ERR_OK:
            raise

        self.running = True
        self.readError = False
        self.sampleCounterAdjust = 0
        self.BlockTimer = time.process_time()
        pass

    def stop(self):
        """
        Stop data acquisition.
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
        Close hardware device.
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
        """
        Get base sampling rate ID and divider for the requested sampling rate
        @param samplingrate: requested sampling rate in Hz
        @return: base rate ID (-1 if not possible) and base rate divider
        """
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
        :param range: device base dynamic range
        :param force:
        """
        # not possible if device is already open or not necessary if rate or range has not changed
        if (self.id != 0 and rate == self.settings.DataRate and range == self.settings.InputRange) and not force:
            return
        # update sampling rate and get new configuration
        try:
            self.setup(
                mode=self.mode.Mode,
                rate=rate,
                range=range
            )
        except:
            pass


    def setup(self, mode, rate, range):
        """
        Prepare device for acquisition
        :param mode: device mode, one of NR_MODE_ values
        :param rate: device sampling rate, one of NR_RATE_ values
        :param range: device dynamic range, one of NR_RATE_ values
        :return: True if the amplifier setup was successful, False or not
        """
        # set amplifier settings
        self.settings.DataRate = rate
        self.settings.InputRanges = range

        # set amplifier mode
        self.mode.Mode = mode

        # transfer settings to amplifier
        err = self.lib.nb2SetDataSettings(self.id, ctypes.byref(self.settings))
        print("err", err)

        if err != NR_ERR_OK:
            return False

        # set event settings
        err = self.lib.nb2SetEventSettings(self.id, ctypes.byref(self.eset))
        print("err", err)

        if err != NR_ERR_OK:
            return False

        # transfer mode to amplifier
        err = self.lib.nb2SetMode(self.id, ctypes.byref(self.mode))
        print("err", err)
        if err != NR_ERR_OK:
            return False

        # if OK return true
        return True

    def read(self, indices, eegcount):
        """
        Read data from device
        :param indices: to select the requested channels from raw data stream
        :param eegcount: number of requested EEG channels
        :return:
        """
        if not self.running or (self.id == 0) or self.readError:
            return None, None

        # calculate data amount for an interval of
        interval = 0.05  # interval in [s]
        bytes_per_sample = (self.CountEeg + 1 + 1) * np.dtype(np.int32).itemsize
        requestedbytes = int(bytes_per_sample * sample_rate[self.settings.DataRate] * interval)

        t = time.process_time()

        # read data from device
        if not self.BlockingMode:
            bytesread = self.lib.nb2GetData(
                self.id,
                ctypes.byref(self.buffer, self.binning_offset),
                len(self.buffer) - self.binning_offset
            )
        else:
            bytesread = self.lib.nb2GetData(
                self.id,
                ctypes.byref(self.buffer, self.binning_offset),
                requestedbytes
            )

        # data available?
        if bytesread == 0:
            return None, None

        blocktime = (time.process_time() - self.BlockTimer)
        self.BlockTimer = time.process_time()
        # print str(blocktime) + " : " + str(bytesread)

        # print str(t-self.lastt) + " : " + str(bytesread)
        # self.lastt = t

        # check for device error
        if self.binning > 1:
            # align buffer to requested binning size
            total_bytes = bytesread + self.binning_offset
            # copy remainder from last read back to sample buffer
            ctypes.memmove(self.buffer, self.binning_buffer, self.binning_offset)
            # new remainder size
            remainder = int(((total_bytes / bytes_per_sample) % self.binning) * bytes_per_sample)
            # number of binning aligned samples
            binning_samples = int(total_bytes / bytes_per_sample / self.binning * self.binning)
            src_offset = int(binning_samples * bytes_per_sample)
            # copy new remainder to binning buffer
            ctypes.memmove(self.binning_buffer, ctypes.byref(self.buffer, src_offset), remainder)
            self.binning_offset = remainder

            # there must be at least one binning sample
            if binning_samples == 0:
                return None, None
            items = int(binning_samples * bytes_per_sample / np.dtype(np.int32).itemsize)
        else:
            items = int(bytesread / np.dtype(np.int32).itemsize)

        # channel order in buffer is S1CH1,S1CH2..S1CHn, S2CH1,S2CH2,..S2nCHn, ...
        x = np.fromstring(self.buffer, np.int32, items)
        # shape and transpose to 1st axis is channel and 2nd axis is sample
        samplesize = self.CountEeg + 1 + 1
        x.shape = (-1, samplesize)
        y = x.transpose()

        # extract the different channel types
        index = 0
        eeg = np.array(y[indices], np.float64)

        # get indices of disconnected electrodes (all values == ADC_MAX)
        # disconnected = np.nonzero(np.all(eeg == ADC_MAX, axis=1))
        disconnected = None  # not possible yet

        # extract and scale the different channel types
        eegscale = self.properties.Resolution * 1e6  # convert to µV
        eeg[index:eegcount] = eeg[index:eegcount] * eegscale
        index += eegcount

        # extract sample counter channel
        index += 1
        sctTemp = np.array(y[index:index + 1], np.uint32)

        # search for sample counter wrap around and adjust counter
        sct = np.array(sctTemp, np.uint64) + self.sampleCounterAdjust
        wrap = np.nonzero(sctTemp == 0)
        if (wrap[1].size > 0) and sct[0][0]:
            wrapIndex = wrap[1][0]
            adjust = np.iinfo(np.uint32).max + 1
            self.sampleCounterAdjust += adjust
            sct[:, wrapIndex:] += adjust

        d = []
        d.append(eeg)
        d.append(sct)
        return d, disconnected

    def getDeviceStatus(self):
        """
        Read status values from device
        @return: total samples, total errors, data rate and data speed as tuple
        """
        # there are no functions from the dll library to implement this function
        pass

    def readImpedances(self):
        """
        Get the electrode impedance values
        @return: list of impedance values for all EEG channels plus ground electrode in Ohm.
        """
        if not self.running or (self.id == 0):
            return None, None

        disconnected = None
        # read impedance data from device
        err = self.lib.nb2GetImpedance(
            self.id,
            ctypes.byref(self.impbuffer),
            len(self.impbuffer)
        )

        if err != NR_ERR_OK:
            # raise AmpError("failed to read impedance values", err)
            raise

        # if err2 == CHAMP_ERR_MONITORING:
        #     disconnected = CHAMP_ERR_MONITORING
        # if err == NR_ERR_FAIL:
        #     return None, None

        # channel order in buffer is CH1,CH2..CHn, GND
        items = self.CountEeg + 1
        return np.fromstring(self.impbuffer, np.uint32, items), disconnected


# if __name__ == "__main__":
#     obj = NeoRec()
#     print(obj.info.Model)
#     obj.open()
#     print(obj.info.Model)
