"""
Python wrapper for NeoRec Windows library

ActiChamp_x86.dll (32-Bit) and ActiChamp_x64.dll (64-Bit)
PyCorderPlus NeoRec Recorder

------------------------------------------------------------

Copyright (C) 2024, Medical Computer Systems Ltd


This file is part of PyCorderPlus
"""

import ctypes
import ctypes.wintypes
import _ctypes
import platform
import time
import numpy as np

NR_VERSION = 0x1000053820000  # 1.0.21378.0 DLL

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

# performance mode


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

# Performance mode
NR_BOOST_MAXIMUM = 0
NR_BOOST_OPTIMUM = 1

# Dithering mode
NR_DITHERING_MAXIMUM = 0
NR_DITHERING_MEDIUM = 1
NR_DITHERING_MINIMUM = 1
NR_DITHERING_OFF = 3


class t_nb2Version(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ('Dll', ctypes.c_uint64),
        ('Firmware', ctypes.c_uint64)
    ]


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


class t_nb2Adjusment(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("Boost", ctypes.c_uint8),
        ("Dithering", ctypes.c_uint8),
    ]


class t_nb2BatteryProperties(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("Capacity", ctypes.c_uint16),
        ("Level", ctypes.c_uint16),  # /10 %
        ("Voltage", ctypes.c_uint16),
        ("Current", ctypes.c_int16),  # mA
        ("Temperature", ctypes.c_int16)
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


class AmpVersion:
    def __init__(self):
        self.version = t_nb2Version()

    def read(self, lib, idx):
        """
        Get information about Firmware and DLL
        :param lib: DLL handle
        :param idx: Connected device ID
        :return: result of receiving data
        """
        res = lib.nb2GetVersion(idx, ctypes.byref(self.version))
        return res

    def info(self):
        """
        Get all amplifier firmware versions as string
        :return: str
        """
        if self.version.Dll != 0 and self.version.Firmware != 0:
            info = f" DLL: {self._getVersionPrettyStringDll(self.version.Dll)} " \
                   f"Firmware: {self._getVersionPrettyStringFirmware(self.version.Firmware)}"
        else:
            info = ""
        return info

    def _getVersionPrettyStringFirmware(self, firmwareversion):
        """
        converts the firmware version to a string
        :param firmwareversion:
        :return: str
        """
        version = str((firmwareversion >> 48) % 0x10000) + '.' \
                  + str((firmwareversion >> 32) % 0x10000) + '.' \
                  + str(firmwareversion % 0x100000000)
        return version

    def _getVersionPrettyStringDll(self, dllversion):
        """
        converts the DLL version to a string
        :param dllversion:
        :return: str
        """
        version = str((dllversion >> 48) % 0x10000) + '.' + str((dllversion >> 32) % 0x10000) + '.' + str(
            (dllversion >> 16) % 0x10000) + '.' + str(dllversion % 0x10000)
        return version

    def DLL(self):
        """ get the DLL version
        """
        return self.version.Dll


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
        self.deviceinfo = t_nb2Information()

        # info about DLL, firmware
        self.ampversion = AmpVersion()

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

        # set default adjusment
        self.adjusment = t_nb2Adjusment()
        self.adjusment.Boost = NR_BOOST_OPTIMUM
        self.adjusment.Dithering = NR_DITHERING_MINIMUM

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

    def reset(self):
        """
        What to do if the connection to the amplifier is lost
        :return:
        """
        self.connected = False  # Connected to amplifier
        self.running = False  # Data acquisition running
        self.readError = False  # an error occurred during data acquisition

        self.close()

        # reload NeoRec windows library
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
                raise AmpError("failed to open library (nb2mcs_x64.dll)")
            else:
                raise AmpError("failed to open library (nb2mcs_x86.dll)")

        # initialization library resources
        res = self.lib.nb2ApiInit()
        if res != NR_ERR_OK:
            AmpError("can't initialize library resources")

    def open(self):
        """
        Open the hardware device
        @return res: result of opening the device
        """
        if self.running:
            return

        if self.lib is None:
            raise AmpError("library nb2mcs_x64.dll not available")

        # get the number of devices on the network
        cnt = self.lib.nb2GetCount()

        if cnt > 0:
            # get index device with number 1
            self.id = self.lib.nb2GetId(0)

            try:
                # open this device
                err = self.lib.nb2Open(self.id)
                if err == NR_ERR_OK:
                    self.connected = True
            except:
                self.connected = False
        return self.connected

    def getDeviceInformation(self):
        """
        Getting information about a connected device
        :return: Model, Serial Number
        """
        if self.lib is None:
            raise AmpError("library nb2mcs.dll not available")

        if not self.connected:
            raise AmpError("device is not open")

        # get and check DLL version
        self.ampversion.read(self.lib, self.id)
        if self.ampversion.DLL() != NR_VERSION:
            raise AmpError("wrong NeoRec DLL version (%X / %X)" % (self.ampversion.DLL(),
                                                                   NR_VERSION))

        # get information about open device
        err = self.lib.nb2GetInformation(self.id, ctypes.byref(self.deviceinfo))
        if err != NR_ERR_OK:
            return None, None

        # get device properties
        err = self.lib.nb2GetProperty(self.id, ctypes.byref(self.properties))
        if err != NR_ERR_OK:
            return None, None

        # get device possibility
        pos = t_nb2Possibility()
        err = self.lib.nb2GetPossibility(self.id, ctypes.byref(pos))
        if err != NR_ERR_OK:
            return None, None

        self.CountEeg = pos.ChannelsCount
        return self.deviceinfo.Model, self.deviceinfo.SerialNumber

    def start(self):
        """
        Start data acquisition
        :return:
        """
        if self.running:
            return
        if self.id == 0:
            raise AmpError("device not open")

        # start amplifier
        err = self.lib.nb2Start(self.id)
        if err != NR_ERR_OK:
            raise AmpError("failed to start device", err)

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
        if not self.connected:
            raise AmpError("device not open")
        err = self.lib.nb2Stop(self.id)
        if err != NR_ERR_OK:
            raise AmpError("failed to stop device", err)

    def close(self):
        """
        Close hardware device.
        """
        if self.lib is None:
            raise AmpError("library nb2mcs_x64.dll not available")

        if self.id != 0:
            if self.running:
                self.stop()

        # close NeoRec
        err = self.lib.nb2Close(self.id)
        if err == NR_ERR_OK:
            self.id = 0
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

    def readConfiguration(self, rate, range, boost, force=False):
        """
        Update device sampling rate, dymamic range and get new configuration
        @param rate: device base sampling rate
        :param range: device base dynamic range
        :param boost: device base performance mode
        :param force:
        """
        # No need to update if the settings have not changed
        if (rate == self.settings.DataRate and
                range == self.settings.InputRange and
                boost == self.adjusment.Boost and not force):
            return

        # update sampling rate and get new configuration
        try:
            self.setup(
                mode=self.mode.Mode,
                rate=rate,
                range=range,
                boost=boost
            )
        except:
            pass

    def setup(self, mode, rate, range, boost):
        """
        Prepare device for acquisition
        :param mode: device mode, one of NR_MODE_ values
        :param rate: device sampling rate, one of NR_RATE_ values
        :param range: device dynamic range, one of NR_RANGE_ values
        :param boost: device performance mode, one of NR_BOOST_ values
        :return: result of command execution, connection
        """

        # set amplifier settings
        self.settings.DataRate = rate
        self.settings.InputRanges = range

        # set amplifier mode
        self.mode.Mode = mode

        # set amplifier performance mode
        self.adjusment.Boost = boost

        connected = True
        # If the amplifier is not connected, then simply updated the parameters in the settings
        if not self.connected:
            return NR_ERR_OK, connected

        if mode == NR_MODE_IMPEDANCE:
            err = self.lib.nb2SetImpedanceFrequency(self.id, int(sample_rate[mode]))
            if err != NR_ERR_OK:
                connected = False
                return err, connected

        # transfer adjusment to amplifier
        err = self.lib.nb2SetAdjustment(self.id, ctypes.byref(self.adjusment))
        if err != NR_ERR_OK:
            connected = False
            return err, connected

        # transfer settings to amplifier
        err = self.lib.nb2SetDataSettings(self.id, ctypes.byref(self.settings))
        if err != NR_ERR_OK:
            connected = False
            return err, connected

        # set event settings
        err = self.lib.nb2SetEventSettings(self.id, ctypes.byref(self.eset))
        if err != NR_ERR_OK:
            connected = False
            return err, connected

        # transfer mode to amplifier
        err = self.lib.nb2SetMode(self.id, ctypes.byref(self.mode))
        if err != NR_ERR_OK:
            connected = False
            return err, connected

        return err, connected

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

    def getDeviceInfoString(self):
        """
        Return device info as string
        """
        info = "NeoRec"

        if self.deviceinfo.Model != 0 and self.deviceinfo.SerialNumber != 0:
            if self.deviceinfo.Model not in NR_Models:
                raise AmpError("unidentified NeoRec amplifier model")
            info += f" {NR_Models[self.deviceinfo.Model]} ({self.deviceinfo.Model}) SN: {self.deviceinfo.SerialNumber}"
        else:
            info += " n.a.\n"
        # get DLL, firmware versions
        info += self.ampversion.info() + "\n"
        return info

    def getDeviceStatus(self):
        """
        Read status values from device
        :return: Rate, Speed, Ratio, BLE Utilization
        """
        if self.lib is None:
            raise AmpError("library nb2mcs_x64.dll not available")
        if self.id == 0:
            raise AmpError("device is not open")
        if not self.connected:
            raise AmpError("device is not connected")

        status = t_nb2DataStatus()  # Rate, Speed, Ratio, BLE Utilization

        err = self.lib.nb2GetDataStatus(self.id, ctypes.byref(status))
        if err != NR_ERR_OK:
            return 0, 0, 0, 0
        return status.Utilization, status.Rate, status.Ratio, status.Speed

    def getBatteryInfo(self):
        """
        Read the amplifier battery information
        :return:
        """
        if self.lib is None:
            raise AmpError("library nb2mcs_x64.dll not available")

        if self.id == 0:
            connected = False
            return 0, connected

        battery = t_nb2BatteryProperties()
        connected = True

        # get amplifier battery info
        err = self.lib.nb2GetBattery(self.id, ctypes.byref(battery))
        if err != NR_ERR_OK:
            connected = False
            return 0, connected

        level = battery.Level / 10  # in percentage, %
        return level, connected

    def readImpedances(self):
        """
        Get the electrode impedance values
        @return: list of impedance values for all EEG channels plus ground electrode in Ohm.
        """
        if self.lib is None:
            raise AmpError("library nb2mcs_x64.dll not available")
        if self.id == 0:
            raise AmpError("device is not open")
        if not self.connected:
            raise AmpError("device is not connected")

        connected = True

        # read impedance data from device
        err = self.lib.nb2GetImpedance(
            self.id,
            ctypes.byref(self.impbuffer),
            len(self.impbuffer)
        )

        if err != NR_ERR_OK:
            connected = False
            return err, connected

        # channel order in buffer is CH1,CH2..CHn, GND
        items = self.CountEeg + 1
        return np.fromstring(self.impbuffer, np.uint32, items), connected

# if __name__ == "__main__":
#     obj = NeoRec()
#     print(obj.info.Model)
#     obj.open()
#     print(obj.info.Model)
