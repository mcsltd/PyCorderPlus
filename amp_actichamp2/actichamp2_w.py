# -*- coding: utf-8 -*-
"""
Python wrapper for ActiChamp Windows library

ActiChamp_x86.dll (32-Bit) and ActiChamp_x64.dll (64-Bit)
PyCorderPlus ActiChamp Recorder

------------------------------------------------------------

Copyright (C) 2010, Brain Products GmbH, Gilching
Copyright (C) 2024, Medical Computer Systems Ltd


This file is part of PyCorderPlus
"""

import ctypes
import ctypes.wintypes
import _ctypes
import numpy as np
import time
import configparser
import platform
import os

# max integer
INT32_MAX = 2 ** 31 - 1

ADC_MAX = 0x7FFFFF

# required hardware DLL version
# CHAMP_VERSION = 0x080B0519          # 08.11.05.25 DLL
# CHAMP_VERSION = 0x090B0B07          # 09.11.11.07 DLL
# CHAMP_VERSION = 0x0A0B0C02          # 10.11.12.02 DLL
# CHAMP_VERSION = 0x0A0B0C17          # 10.11.12.23 DLL
# CHAMP_VERSION = 0x0A0B0C1D          # 10.11.12.29 DLL
# CHAMP_VERSION = 0x0B0C0A02          # 11.12.10.02 DLL
# CHAMP_VERSION = 0x110C0B10          # 17.12.11.16 DLL
# CHAMP_VERSION = 0x120D0710          # 18.13.07.16 DLL
# CHAMP_VERSION = 0x160D0B0E          # 22.13.11.14 DLL
# CHAMP_VERSION = 0x170E040F           # 23.14.04.15 DLL
# CHAMP_VERSION = 0x190E0804  # 25.14.08.04 DLL
CHAMP_VERSION = 0x1D13060B  # 29.19.6.11

# required firmware versions (board revision 4)
CHAMP_4_VERSION_CTRL = 0x040B041C  # 04.11.04.28 FX2 USB controller
CHAMP_4_VERSION_FPGA = 0x2C000000  # 44.00.00.00 FPGA
CHAMP_4_VERSION_DSP = 0x060B0519  # 06.11.05.25 MSP430

# required firmware versions (board revision 6)
CHAMP_6_VERSION_CTRL = 0x660F0609  # 102.15.06.09 FX2 USB controller
CHAMP_6_VERSION_FPGAM = 0x30000000  # 48.00.00.00 FPGA media controller
CHAMP_6_VERSION_FPGAC = 0x2D000000  # 45.00.00.00 FPGA carrier board
CHAMP_6_VERSION_DSP = 0x690E0A07  # 105.14.10.07  MSP430

# compensate constant trigger delay
CHAMP_COMPTRIGGER = False

# C error numbers
CHAMP_ERR_OK = 0  # Success (no errors)
CHAMP_ERR_HANDLE = -1  # Invalid handle (such handle not present now)
CHAMP_ERR_PARAM = -2  # Invalid function parameter(s)
CHAMP_ERR_FAIL = -3  # Function fail (internal error)
CHAMP_ERR_MONITORING = -4  # data rate monitoring failed
CHAMP_ERR_SUPPORT = -5  # function not supported

# ADC data filter enum
CHAMP_ADC_NATIVE = 0  # no ADC data filter
CHAMP_ADC_AVERAGING_2 = 1  # ADC data moving average filter by 2 samples

# ADC data decimation
CHAMP_DECIMATION_0 = 0  # no decimation
CHAMP_DECIMATION_2 = 2  # decimation by 2
CHAMP_DECIMATION_5 = 5  # decimation by 5
CHAMP_DECIMATION_10 = 10  # decimation by 10
CHAMP_DECIMATION_20 = 20  # decimation by 20
CHAMP_DECIMATION_50 = 50  # decimation by 50

# Mode enum
CHAMP_MODE_NORMAL = 0  # normal data acquisition
CHAMP_MODE_ACTIVE_SHIELD = 1  # data acquisition with ActiveShield
CHAMP_MODE_IMPEDANCE = 2  # impedance measure
CHAMP_MODE_TEST = 3  # test signal (square wave 200 uV, 1 Hz)
CHAMP_MODE_LED_TEST = 99  # active electrode LED test mode

# Mode text
CHAMP_Modes = {CHAMP_MODE_NORMAL: "acquisition",
               CHAMP_MODE_ACTIVE_SHIELD: "acquisition with shield",
               CHAMP_MODE_IMPEDANCE: "impedance measurement",
               CHAMP_MODE_TEST: "test signal",
               CHAMP_MODE_LED_TEST: "active electrode LED test"}

# actiChamp base sample rate enum
CHAMP_RATE_10KHZ = 0  # 10 kHz, all channels (default mode)
CHAMP_RATE_50KHZ = 1  # 50 kHz
CHAMP_RATE_100KHZ = 2  # 100 kHz, max 64 channels
# actiChamp base sample rate for extended settings enum
CHAMP_RATE_25KHZ = 10  # 25 kHz
CHAMP_RATE_5KHZ = 11  # 5 kHz
CHAMP_RATE_2KHZ = 12  # 2 kHz
CHAMP_RATE_1KHZ = 13  # 1 kHz
CHAMP_RATE_500HZ = 14  # 500 Hz
CHAMP_RATE_200HZ = 15  # 200 Hz

# sample rate frequency dictionary (amplifier DLL base frequencies available for the application)
# if you want to do the decimation and filtering in Python (amplifier_neorec.py) then
# set this value to True:
PythonDecimation = False
if PythonDecimation:
    sample_rate = {
        CHAMP_RATE_10KHZ: 10000.0,
        CHAMP_RATE_50KHZ: 50000.0,
        CHAMP_RATE_100KHZ: 100000.0
    }
else:
    sample_rate = {
        CHAMP_RATE_200HZ: 200.0, CHAMP_RATE_500HZ: 500.0, CHAMP_RATE_1KHZ: 1000.0,
        CHAMP_RATE_2KHZ: 2000.0, CHAMP_RATE_5KHZ: 5000.0,
        CHAMP_RATE_10KHZ: 10000.0, CHAMP_RATE_25KHZ: 25000.0,
        CHAMP_RATE_50KHZ: 50000.0, CHAMP_RATE_100KHZ: 100000.0
    }

# trigger delay dictionary (for constant trigger delay compensation)
trigger_delay = {
    CHAMP_RATE_200HZ: 1, CHAMP_RATE_500HZ: 1, CHAMP_RATE_1KHZ: 1,
    CHAMP_RATE_2KHZ: 1, CHAMP_RATE_5KHZ: 1,
    CHAMP_RATE_10KHZ: 1, CHAMP_RATE_25KHZ: 1,
    CHAMP_RATE_50KHZ: 1, CHAMP_RATE_100KHZ: 1}

# sample rate extended settings dictionary
# translate application base frequency to amplifier physical frequency
# 0=10kHz, 1=50kHz, 2=100kHz
sample_rate_settings = {
    CHAMP_RATE_200HZ: 0, CHAMP_RATE_500HZ: 0, CHAMP_RATE_1KHZ: 0,
    CHAMP_RATE_2KHZ: 0, CHAMP_RATE_5KHZ: 0,
    CHAMP_RATE_10KHZ: 0, CHAMP_RATE_25KHZ: 1,
    CHAMP_RATE_50KHZ: 1, CHAMP_RATE_100KHZ: 2}
# decimation values (rate = physical / decimation)
sample_rate_decimation = {
    CHAMP_RATE_200HZ: CHAMP_DECIMATION_50, CHAMP_RATE_500HZ: CHAMP_DECIMATION_20, CHAMP_RATE_1KHZ: CHAMP_DECIMATION_10,
    CHAMP_RATE_2KHZ: CHAMP_DECIMATION_5, CHAMP_RATE_5KHZ: CHAMP_DECIMATION_2,
    CHAMP_RATE_10KHZ: CHAMP_DECIMATION_0, CHAMP_RATE_25KHZ: CHAMP_DECIMATION_2,
    CHAMP_RATE_50KHZ: CHAMP_DECIMATION_0, CHAMP_RATE_100KHZ: CHAMP_DECIMATION_0}


class t_champSettings(ctypes.Structure):
    """ C amplifier settings
    """
    _pack_ = 1
    _fields_ = [("Mode", ctypes.c_int),  # mode of acquisition
                ("Rate", ctypes.c_int)]  # sample rate


class CHAMP_SETTINGS_EX(ctypes.Structure):
    """ C extended amplifier settings
    """
    _pack_ = 1
    _fields_ = [("Mode", ctypes.c_int),  # mode of acquisition
                ("Rate", ctypes.c_int),  # sample rate
                ("AdcFilter", ctypes.c_int),  # ADC data filter
                ("Decimation", ctypes.c_int)]  # ADC data decimation


class t_champProperty(ctypes.Structure):
    """ C amplifier properties
    """
    _pack_ = 1
    _fields_ = [("CountEeg", ctypes.c_uint),  # number of Eeg channels
                ("CountAux", ctypes.c_uint),  # number of Aux channels
                ("CountRef", ctypes.c_uint),    # numbers of Ref channels
                ("CountExG", ctypes.c_uint),    # numbers of ExG channels
                ("TriggersIn", ctypes.c_uint),  # numbers of input triggers
                ("TriggersOut", ctypes.c_uint),  # numbers of output triggers
                ("Rate", ctypes.c_float),  # sampling rate, Hz
                ("ResolutionEegRef", ctypes.c_float),  # EEG and REF amplitude scale coefficients, V/bit
                ("ResolutionAuxExG", ctypes.c_float),  # AUX and ExG amplitude scale coefficients, V/bit
                ("RangeEegRef", ctypes.c_float),  # EEG and REF input range peak-peak, V
                ("RangeAuxExG", ctypes.c_float)]  #  AUX and ExG input range peak-peak, V


class CHAMP_IMPEDANCE_SETUP(ctypes.Structure):
    """ C impedance settings
    """
    _pack_ = 1
    _fields_ = [("Good", ctypes.c_uint),  # Good level (green led indication), Ohm
                ("Bad", ctypes.c_uint),  # Bad level (red led indication), Ohm
                ("LedsDisable", ctypes.c_uint),  # Disable electrode's leds, if not zero
                ("TimeOut", ctypes.c_uint)]  # Impedance mode time-out (0 - 65535), sec


class t_champDataStatus(ctypes.Structure):
    """ C device data status
    """
    _pack_ = 1
    _fields_ = [("Samples", ctypes.c_uint),  # Total samples
                ("Errors", ctypes.c_uint),  # Total errors
                ("Rate", ctypes.c_float),  # Data rate, Hz
                ("Speed", ctypes.c_float)]  # Data speed, MB/s


class CHAMP_SYSTEMTIME(ctypes.Structure):
    """ C system time struct
    """
    _pack_ = 1
    _fields_ = [('wYear', ctypes.wintypes.WORD),
                ('wMonth', ctypes.wintypes.WORD),
                ('wDayOfWeek', ctypes.wintypes.WORD),
                ('wDay', ctypes.wintypes.WORD),
                ('wHour', ctypes.wintypes.WORD),
                ('wMinute', ctypes.wintypes.WORD),
                ('wSecond', ctypes.wintypes.WORD),
                ('wMilliseconds', ctypes.wintypes.WORD)]


class CHAMP_MODULE_INFO(ctypes.Structure):
    """ C device and module info
    """
    _pack_ = 1
    _fields_ = [('Model', ctypes.c_uint),  # Model ID
                ('SerialNumber', ctypes.c_uint),  # Serial Number
                ('Date', CHAMP_SYSTEMTIME)]  # Production Date and Time


CHAMP_DEVICE_INFO = CHAMP_MODULE_INFO * 6  # index 0=device, index 1-5=modules


class t_champVersion(ctypes.Structure):
    """ C DLL, USB driver and firmware versions
    """
    _pack_ = 1
    _fields_ = [('DLL', ctypes.wintypes.DWORD),  # DLL version
                ('Driver', ctypes.wintypes.DWORD),  # USB driver version
                ('FPGA', ctypes.wintypes.DWORD),  # FPGA firmware version
                ('Firmware', ctypes.wintypes.DWORD)]  # MSP430 firmware version


class t_champVoltages(ctypes.Structure):
    """ C Amplifier voltages and temperature
    The voltages DVDD3, AVDD3, AVDD5 and REF are valid only during data acquisition
    """
    _pack_ = 1
    _fields_ = [
        ('VDC', ctypes.c_float),            # Power supply, V
        ('Temperature', ctypes.c_float),    # Temperature, degree Celsius
        ('DVDD3V3', ctypes.c_float),        # Digital 3.3, V
        ('DVDD2V5', ctypes.c_float),        # Digital 2.5, V
        ('DVDD1V8', ctypes.c_float),        # Digital 1.8, V
        ('DVDD1V35', ctypes.c_float),       # Digital 1.35, V
        ('DVDD1V0', ctypes.c_float),        # Digital 1.0, V
        ('AVDD5V0', ctypes.c_float)         # Analog 5.0, V
    ]


class t_champModules(ctypes.Structure):
    """ C Module control structure
    Bits:
    0 - AUX module
    1 - 5 - Main EEG modules (1 - 5)
    6 - 31 - Reserved
    """
    _pack_ = 1
    _fields_ = [('Present', ctypes.c_uint),  # Bits indicate that the module is present in hardware
                ('Enabled', ctypes.c_uint)]  # Bits indicate that the module is enabled for use


class CHAMP_PLL(ctypes.Structure):
    """ C PLL Parameters
    """
    _pack_ = 1
    _fields_ = [('PllExternal', ctypes.c_uint),  # if 1 - use External clock for PLL, if 0 - use Internal 48 MHz
                ('AdcExternal', ctypes.c_uint),  # if 1 - out External clock to ADC, if 0 - use PLL output
                ('PllFrequency', ctypes.c_uint),  # PLL frequency 10 MHz - 27 MHz (needs set if AdcExternal = 0), Hz
                ('PllPhase', ctypes.c_uint),  # Phase shift (hardware step 360 / 10 = 36), degrees
                ('Status', ctypes.c_uint)]  # PLL status (read only)


class AmpError(Exception):
    """
    Generic amplifier exception
    """

    def __init__(self, value, errornr=0):
        errortext = ""
        if errornr == CHAMP_ERR_HANDLE:
            errortext = "Invalid handle (device disconnected)"
        elif errornr == CHAMP_ERR_PARAM:
            errortext = "Invalid function parameter(s)"
        elif errornr == CHAMP_ERR_FAIL:
            errortext = "Function fail (internal error)"
        elif errornr == CHAMP_ERR_MONITORING:
            errortext = "Data rate mismatch"
        elif errornr == CHAMP_ERR_SUPPORT:
            errortext = "Function is not supported"
        errortext = errortext + " :%i" % errornr
        if errornr != 0:
            self.value = f"actiChamp: {str(value)} -> {errortext}"
        else:
            self.value = f"actiChamp: {str(value)}"

    def __str__(self):
        return self.value


class AmpVersion:
    def __init__(self):
        self.version = t_champVersion()
        self.boardRevision = 4

    def read(self, lib, device):
        """ read board dependent version infos from amplifier
        attention: the carrier board FPGA version (FPGAC) is only available if the acquisition is running.
        @param lib: DLL handle
        @param device: device handle
        @return: DLL result value
        """
        res = lib.champGetVersion(device, ctypes.byref(self.version))
        return res

    def isFpgaProgrammed(self):
        if self.boardRevision and self.version.FPGA == 0:
            return False
        return True

    def _getVersionString(self, rawversion):
        """ get readable version string from DWORD
        @param rawversion: raw version number from DLL
        @return: version string
        """
        # split version number
        version = ""
        for i in reversed(range(4)):
            version += "%02i" % ((rawversion >> i * 8) & 0xFF)
            if i:
                version += "."
        return version

    def info(self):
        """ get all amplifier firmware versions as string
        """
        # create version string for board revision 4
        version = "Version: DLL_%s, Driver_%s, FPGA_%s, Firmware_%s" % (
            self._getVersionString(self.version.DLL), self._getVersionString(self.version.Driver),
            self._getVersionString(self.version.FPGA), self._getVersionString(self.version.Firmware)
        )
        return version

    def DLL(self):
        """ get the DLL version
        """
        return self.version.DLL

    def revision(self):
        """ get the amplifier revision, depending on board revision
        """
        return 2


class ActiChamp2:
    """
    ActiChamp hardware object (Python wrapper for actiCHamp Windows DLL)
    """

    def __init__(self):
        """
        Constructor
        """
        # get OS architecture (32/64-bit)
        self.x64 = ("64" in platform.architecture()[0])

        # set default values
        self.devicehandle = 0
        self.ampversion = AmpVersion()  #: actiCHamp version info structure
        self.deviceinfo = CHAMP_DEVICE_INFO()  #: actiCHamp device info structure
        self.modulestate = t_champModules()  #: actiCHamp module connection state structure
        self.properties = t_champProperty()  #: actiCHamp property structure
        self.settings = t_champSettings()  #: actiCHamp settings structure
        self.settings.Rate = CHAMP_RATE_10KHZ  #: sampling rate
        self.settings.Mode = CHAMP_MODE_NORMAL  #: acquisition mode
        self.running = False  #: data acquisition running
        self.buffer = ctypes.create_string_buffer(10000 * 1024)  #: raw data transfer buffer
        self.impbuffer = ctypes.create_string_buffer(1000)  #: impedance raw data transfer buffer
        self.readError = False  #: an error occurred during data acquisition
        self.activeShieldGain = 5  #: default active shield gain
        self.enablePllConfiguration = False  #: enable the PLL configuration option
        self.PllExternal = 0  #: use external input for the PLL

        # binning buffer for max. 100 samples with 170 channels with a datasize of int32 (4 bytes)
        self.binning_buffer = ctypes.create_string_buffer(100 * 171 * 4)  #: binning buffer
        self.binning = 1  #: binning size for buffer alignment
        self.binning_offset = 0  #: raw data buffer offset in bytes for binning

        self.sampleCounterAdjust = 0  #: sample counter wrap around, HW counter is 32bit value but we need 64bit
        self.BlockingMode = True  #: read data in blocking mode
        self.EmulationMode = False  #: emulate hardware

        # set default properties
        self.properties.CountEeg = 32
        self.properties.CountAux = 8
        self.properties.CountRef = 1
        self.properties.CountExG = 2
        self.properties.TriggersIn = 8
        self.properties.TriggersOut = 8
        self.properties.Rate = 10000.0
        self.properties.ResolutionEegRef = 4.88e-08
        self.properties.ResolutionAuxExG = 2.98e-07
        self.properties.RangeEegRef = 0.819
        self.properties.RangeAuxExG = 5.0

        # load ActiChamp 32 or 64 bit windows library
        self.lib = None
        self.loadLib()

        # get and check DLL version
        self.ampversion.read(self.lib, self.devicehandle)


        if self.ampversion.DLL() != CHAMP_VERSION:
            pass
            # print(f"{self.ampversion.DLL()}")
            # raise AmpError("wrong ActiChamp DLL version (%X / %X)" % (self.ampversion.DLL(),
            #                                                           CHAMP_VERSION))

        # try to open device and get device properties
        try:
            # get hardware properties
            self.open()
            self.getDeviceInfo()
        except:
            pass

        try:
            self.close()
        except:
            pass

    def loadLib(self):
        """
        Load windows library
        """
        # load ActiChamp 32 or 64 bit windows library
        try:
            path = os.path.dirname(os.path.abspath(__file__))
            # unload existing library
            if self.lib is not None:
                _ctypes.FreeLibrary(self.lib._handle)
                # load/reload library
            if self.x64:
                path += r"\ActiChamp2_x64.dll"
                self.lib = ctypes.windll.LoadLibrary(path)
                self.lib.champOpen.restype = ctypes.c_uint64
            else:
                raise AmpError("The current system bit depth is not supported")
        except:
            self.lib = None
            if self.x64:
                raise AmpError("failed to open library (ActiChamp2_x64.dll)")
            else:
                raise AmpError("The current system bit depth is not supported")

    def open(self):
        """
        Open the hardware device and get a device handle and device properties
        """
        if self.running:
            return
        if self.lib is None:
            raise AmpError("library ActiChamp2_x64.dll not available")

        # check if device hardware is available
        self._resetDeviceProperties()

        if self.lib.champGetCount() == 0:
            raise AmpError("hardware not available")

        retry = 3
        while retry > 0:

            # open the first available device
            if self.x64:
                self.devicehandle = ctypes.c_uint64(self.lib.champOpen(0))
            else:
                raise AmpError("The current system bit depth is not supported")

            if self.devicehandle.value == 0:
                self.devicehandle = 0
                raise AmpError("failed to open device")

            # get device version info
            err = self.ampversion.read(self.lib, self.devicehandle)
            if err != CHAMP_ERR_OK:
                self.close()
                raise AmpError("failed to get device version info", err)

            # check if fpga loaded successfully
            if not self.ampversion.isFpgaProgrammed():
                self.lib.champClose(self.devicehandle)
                self.devicehandle = 0
                retry -= 1
                if retry == 0:
                    raise AmpError("failed to open device")
            else:
                retry = 0

        # get device module connection info
        self.modulestate.Enabled = 0
        self.modulestate.Present = 0
        self.lib.champGetModules(self.devicehandle, ctypes.byref(self.modulestate))

        # get device properties
        self.lib.champGetProperty(self.devicehandle, ctypes.byref(self.properties))

    def _resetDeviceProperties(self):
        """
        Set channel count to zero
        """
        self.properties.CountEeg = 0
        self.properties.CountAux = 0
        self.properties.CountRef = 0
        self.properties.CountExG = 0
        self.properties.TriggersIn = 0
        self.properties.TriggersOut = 0

    def getDeviceInfo(self):
        """
        Read ID, serial number and production date from device and all connected modules
        """
        if self.devicehandle == 0 or self.running or self.getEmulationMode() != 0:
            return

        # reset the info structure
        self.deviceinfo = CHAMP_DEVICE_INFO()

        # power up device
        self.setup(CHAMP_MODE_NORMAL, CHAMP_RATE_10KHZ, 1)
        self.start()

        # read the amplifier extended versions to get the carrier board FPGA version also
        # self.ampversion.readext(self.lib, self.devicehandle)

        # get infos from device
        module = -1
        for info in self.deviceinfo:
            # get device info
            if module == -1:
                self.lib.champFactoryDeviceProductionGet(self.devicehandle, ctypes.byref(info))
            else:
                self.lib.champFactoryModuleProductionGet(self.devicehandle, module, ctypes.byref(info))
            module += 1

        # power down device
        self.stop()

    def start(self):
        """
        Start data acquisition
        """
        if self.running:
            return
        if self.devicehandle == 0:
            raise AmpError("device not open")

        # start amplifier
        err = self.lib.champStart(self.devicehandle)
        if err != CHAMP_ERR_OK:
            raise AmpError("failed to start device", err)

        # read the amplifier extended versions to get the carrier board FPGA version also
        # self.ampversion.readext(self.lib, self.devicehandle)

        # get infos from device
        self.deviceinfo = CHAMP_DEVICE_INFO()  # reset the info structure
        module = -1
        for info in self.deviceinfo:
            # get device info
            if module == -1:
                self.lib.champFactoryDeviceProductionGet(self.devicehandle, ctypes.byref(info))
            else:
                self.lib.champFactoryModuleProductionGet(self.devicehandle, module, ctypes.byref(info))
            module += 1

        self.running = True
        self.readError = False
        self.sampleCounterAdjust = 0
        self.BlockTimer = time.process_time()

        # try to set the PLL input
        self.setPllInput()

        # reset signal generator
        self.DummySignals = []

    def close(self):
        """
        Close hardware device
        """
        if self.lib is None:
            raise AmpError("library ActiChamp2_x64.dll not available")
        if self.devicehandle != 0:
            if self.running:
                try:
                    self.stop()
                except:
                    pass
            self.lib.champClose(self.devicehandle)
        self.devicehandle = 0

    def stop(self):
        """
        Stop data acquisition
        """
        if not self.running:
            return
        self.running = False
        if self.devicehandle == 0:
            raise AmpError("device not open")
        err = self.lib.champStop(self.devicehandle)
        if err != CHAMP_ERR_OK:
            raise AmpError("failed to stop device", err)

    def getEmulationMode(self):
        """
        Lookup emulation and PLL configuration flag in INI file
        @return: number of modules if in emulation mode, else 0
        """
        emulation = 0
        modules = 0
        try:
            ini = configparser.ConfigParser()
            filename = os.path.dirname(os.path.abspath(__file__))
            if self.x64:
                filename += r"\ActiChamp2_x64.dll.ini"
            else:
                raise AmpError("The current system bit depth is not supported")

            if len(ini.read(filename)) > 0:
                emulation = ini.getint("Main", "Emulation")
                if emulation != 0:
                    modules = int(ini.getint("Emulation", "Model") / 32)
                try:
                    self.enablePllConfiguration = ini.getint("Main", "EnablePllConfiguration") != 0
                except:
                    self.enablePllConfiguration = False
        except:
            modules = 0
        self.EmulationMode = (modules > 0)
        return modules

    def setup(self, mode, rate, binning):
        """
        Prepare device for acquisition
        @param mode: device mode, one of CHAMP_MODE_ values
        @param rate: device sampling rate, one of CHAMP_RATE_ values
        @param binning: sampling rate divider to align read buffer to requested binning size
        """
        # LED test is done in normal recording mode
        if mode == CHAMP_MODE_LED_TEST:
            self.settings.Mode = CHAMP_MODE_NORMAL
        else:
            self.settings.Mode = mode
        self.settings.Rate = rate
        self.binning = int(binning)
        self.binning_offset = 0
        if self.devicehandle == 0:
            raise AmpError("device not open")

        # setup amplifier
        ex_settings = self._get_settings_ex(self.settings)

        # limit the number of modules (1xEEG + AUX) if sampling rate is 100KHz
        if self.settings.Rate == CHAMP_RATE_100KHZ:
            self.modulestate.Enabled = self.modulestate.Present & 0x03
        # limit the number of modules (2xEEG + AUX) if sampling rate is 50KHz
        elif self.settings.Rate == CHAMP_RATE_50KHZ:
            self.modulestate.Enabled = self.modulestate.Present & 0x07
        # limit the number of modules (4xEEG + AUX) if sampling rate is 25KHz
        elif self.settings.Rate == CHAMP_RATE_25KHZ:
            self.modulestate.Enabled = self.modulestate.Present & 0x1F
        # enable all present modules if sampling rate is below 25KHz
        else:
            self.modulestate.Enabled = self.modulestate.Present

        # start impedance measurement always with 10KHz
        if ex_settings.Mode == CHAMP_MODE_IMPEDANCE:
            ex_settings.Rate = CHAMP_RATE_10KHZ
            ex_settings.Decimation = CHAMP_DECIMATION_0

        # enable modules
        err = self.lib.champSetModules(self.devicehandle, ctypes.byref(self.modulestate))
        if err != CHAMP_ERR_OK:
            raise AmpError("failed to setup module selection", err)

        # setup device
        err = self.lib.champSetSettingsEx(self.devicehandle, ctypes.byref(ex_settings))
        if err != CHAMP_ERR_OK:
            raise AmpError("failed to setup device", err)

        # set active shield gain
        gain = ctypes.c_uint(self.activeShieldGain)  # 1-100, default = 100
        err = self.lib.champSetActiveShieldGain(self.devicehandle, gain)
        if err != CHAMP_ERR_OK:
            raise AmpError("failed to set active shield gain", err)

        # get device properties
        self._resetDeviceProperties()
        self.lib.champGetProperty(self.devicehandle, ctypes.byref(self.properties))

        # create constant trigger delay compensation buffer
        trgdelay = trigger_delay[self.settings.Rate]
        self.trgdelaybuf = np.zeros(trgdelay, np.uint32) + 0xFFFF

    def read(self, indices, eegcount, auxcount, exgcount, refcount):
        """
        Read data from device
        @param indices: to select the requested channels from raw data stream
        @param eegcount: number of requested EEG channels
        @param auxcount: number of requested AUX channels
        @param exgcount: number of requested EXG channels
        @param refcount: number of requested REF channels
        @return: list of np arrays for channel data, trigger channel and sample counter,
                 indices of disconnected channels
        """
        if not self.running or (self.devicehandle == 0) or self.readError:
            return None, None

        # calculate data amount for an interval of
        interval = 0.05  # interval in [s]
        bytes_per_sample = (self.properties.CountEeg + self.properties.CountAux + self.properties.CountRef + self.properties.CountExG + 1 + 1 + 1) * np.dtype(np.int32).itemsize
        requestedbytes = int(bytes_per_sample * sample_rate[self.settings.Rate] * interval)

        t = time.process_time()

        # read data from device
        if not self.BlockingMode:
            bytesread = self.lib.champGetData(self.devicehandle,
                                              ctypes.byref(self.buffer, self.binning_offset),
                                              len(self.buffer) - self.binning_offset)
        else:
            bytesread = self.lib.champGetDataBlocking(self.devicehandle,
                                                      ctypes.byref(self.buffer, self.binning_offset),
                                                      requestedbytes)

        blocktime = (time.process_time() - self.BlockTimer)
        self.BlockTimer = time.process_time()

        # print(str(blocktime) + " : " + str(bytesread))
        # print(str(t-self.lastt) + " : " + str(bytesread))
        # self.lastt = t

        # check for device error
        if bytesread < 0:
            if bytesread == CHAMP_ERR_MONITORING:
                return None, CHAMP_ERR_MONITORING
            self.readError = True  # block next read access, until acquisition is restarted
            raise AmpError("failed to read data from device", bytesread)

        # data available?
        if bytesread == 0:
            return None, None

        if self.binning > 1:
            # align buffer to requested binning size
            total_bytes = bytesread + self.binning_offset
            # copy remainder from last read back to sample buffer
            ctypes.memmove(self.buffer, self.binning_buffer, self.binning_offset)
            # new remainder size
            remainder = ((total_bytes / bytes_per_sample) % self.binning) * bytes_per_sample
            # number of binning aligned samples
            binning_samples = total_bytes / bytes_per_sample / self.binning * self.binning
            src_offset = binning_samples * bytes_per_sample
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
        x = np.frombuffer(self.buffer, dtype=np.int32, count=items)

        # shape and transpose to 1st axis is channel and 2nd axis is sample
        samplesize = self.properties.CountEeg + self.properties.CountAux + self.properties.CountRef + self.properties.CountExG + 1 + 1 + 1
        x.shape = (-1, samplesize)
        y = x.transpose()

        # extract the different channel types
        index = 0
        eeg = np.array(y[indices], np.float64)

        # get indices of disconnected electrodes (all values == ADC_MAX)
        # disconnected = np.nonzero(np.all(eeg == ADC_MAX, axis=1))
        disconnected = None  # not possible yet

        # extract and scale the different channel types
        eegscale = self.properties.ResolutionEegRef * 1e6  # convert to µV
        eeg[index:eegcount] = eeg[index:eegcount] * eegscale
        index += eegcount

        auxscale = self.properties.ResolutionAuxExG * 1e6  # convert to µV
        eeg[index:index + auxcount] = eeg[index:index + auxcount] * auxscale
        index += auxcount

        refscale = self.properties.ResolutionEegRef * 1e6 # convert to µV
        eeg[index:index + refcount] = eeg[index:index + refcount] * refscale
        index += refcount

        exgscale = self.properties.ResolutionAuxExG * 1e6  # convert to µV
        eeg[index:index + exgcount] = eeg[index:index + exgcount] * exgscale

        # extract trigger channel
        index = self.properties.CountEeg + self.properties.CountAux + self.properties.CountRef + self.properties.CountExG
        trg = np.array(y[index:index + 1], np.uint32)

        # compensate constant trigger delay
        if CHAMP_COMPTRIGGER:
            dsize = len(trg[0])
            temp = np.append(self.trgdelaybuf, trg[0], 0)
            trg[0] = temp[:dsize]
            self.trgdelaybuf = temp[dsize:]

        # extract sample counter channel
        index += 2
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
        d.append(trg)
        d.append(sct)
        return d, disconnected

    def _get_settings_ex(self, settings):
        ''' Prepare extended settings (rate, decimation and filter)
        @param settings: amplifier base settings
        @return: extended settings
        '''
        csext = CHAMP_SETTINGS_EX()
        csext.Mode = settings.Mode
        csext.Rate = sample_rate_settings[settings.Rate]
        csext.Decimation = sample_rate_decimation[settings.Rate]
        csext.AdcFilter = CHAMP_ADC_AVERAGING_2
        return csext

    def getDeviceInfoString(self):
        """
        Return device info as string
        """
        emulation = self.getEmulationMode()
        if emulation != 0:
            info = "actiCHamp Simulation Mode, %i Module(s)\n" % emulation
        else:
            info = ""
            for n in range(0, len(self.deviceinfo)):
                if n == 0:
                    info += "actiCHamp "
                else:
                    info += "Module %i  " % (n)
                if self.deviceinfo[n].Date.wYear == 0:
                    info += "n.a."
                else:
                    info += "(%i) SN: %08i" % (self.deviceinfo[n].Model,
                                               self.deviceinfo[n].SerialNumber)
                    if n == 0:
                        info += " Rev. %i" % self.ampversion.revision()
                info += "\n"
        # get firmware versions
        info += self.ampversion.info() + "\n"
        return info

    def setPllInput(self):
        """
        Set the PLL input either to external or internal
        """
        if self.devicehandle == 0 or not self.hasPllOption() or self.getEmulationMode() != 0:
            return

        PllParamters = CHAMP_PLL()
        PllParamters.PllExternal = self.PllExternal
        PllParamters.AdcExternal = 0
        PllParamters.PllFrequency = 25600000
        PllParamters.PllPhase = 0

        err = self.lib.champSetPll(self.devicehandle, ctypes.byref(PllParamters))
        if err != CHAMP_ERR_OK:
            raise AmpError("failed to set PLL parameters\nPLL frequency: %d, Status: %d" % (
                PllParamters.PllFrequency, PllParamters.Status), err)

    def hasPllOption(self):
        """
        The PLL option is available for Rev. 3 amplifiers only and has to be enabled in the INI file
        """
        return self.enablePllConfiguration

    def getBatteryVoltage(self):
        """ Read the amplifier battery voltages
        @return: state (0=ok, 1=critical, 2=bad) and voltage
        """
        faultyVoltages = []
        voltages = t_champVoltages()
        # voltages.VDC = 0.0
        if self.devicehandle == 0:
            return 0, voltages, faultyVoltages

        # get amplifier voltages
        err = self.lib.champGetVoltages(self.devicehandle, ctypes.byref(voltages))
        if err != CHAMP_ERR_OK:
            time.sleep(0.005)
            err = self.lib.champGetVoltages(self.devicehandle, ctypes.byref(voltages))
            if err != CHAMP_ERR_OK:
                if self.running:
                    return 2, voltages, faultyVoltages
                else:
                    return 0, voltages, faultyVoltages

        # check battery voltage
        state = 0
        if voltages.VDC < 5.6:
            state = 1
        if voltages.VDC < 5.3:
            state = 2
        # check other voltages
        # 'V3' Internal 3.3, [V]
        # 'DVDD3' Digital 3.3, [V]
        # 'AVDD3' Analog 3.3, [V]
        # 'AVDD5' Analog 5.0, [V]
        # 'REF'   Reference 2.048, [V]
        if self.running:
            targets = [("DVDD3V3", 3.3), ("DVDD2V5", 3.0), ("DVDD1V8", 1.8), ("DVDD1V35", 1.35), ("DVDD1V0", 1.0), ("AVDD5V0", 5.0)]
            # if self.deviceinfo[0].SerialNumber == 11020001:
            #     targets = [("V3", 3.3), ("DVDD3", 2.2), ("AVDD3", 3.3), ("AVDD5", 5.0), ("REF", 2.048)]
            for idx, target in targets:
                u = getattr(voltages, idx)
                if u < 0.9 * target or u > 1.1 * target:
                    faultyVoltages.append("%s=%.1fV" % (idx, u))

        return state, voltages, faultyVoltages

    @staticmethod
    def getSamplingRateBase(samplingrate):
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

    def LedTest(self, step):
        """ Toggle active electrode LEDs
        @param step: 0 = switch off all electrode LEDs, reset index
                     1 = set next electrode to green
                     2 = set next electrode to red
                     11 = set all electrodes to green
                     12 = set all electrodes to red
        @return: TRUE if last electrode index reached
        """
        ledcount = self.properties.CountEeg + 1
        led_array = (ctypes.c_int * ledcount)()
        led_array[:] = [0] * len(led_array)
        if step == 0:
            self.LED_index = 0
            self.lib.champSetElectrodes(self.devicehandle, None, 0)
            return True
        elif step == 1:
            led_array[self.LED_index] = 1
            self.LED_index += 1
        elif step == 2:
            led_array[self.LED_index] = 2
            self.LED_index += 1
        elif step == 11:
            led_array[:] = [1] * len(led_array)
            self.LED_index = 0
        elif step == 12:
            led_array[:] = [2] * len(led_array)
            self.LED_index = 0
        err = self.lib.champSetElectrodes(self.devicehandle, led_array, ctypes.sizeof(led_array))
        if err != CHAMP_ERR_OK:
            raise AmpError("failed to set electrode LEDs", err)
        if self.LED_index >= len(led_array):
            self.LED_index = 0
        return self.LED_index == 0

    def getDeviceStatus(self):
        ''' Read status values from device
        @return: total samples, total errors, data rate and data speed as tuple
        '''
        if self.devicehandle == 0:
            return 0, 0, 0, 0
        status = t_champDataStatus()
        err = self.lib.champGetDataStatus(self.devicehandle, ctypes.byref(status))
        if err != CHAMP_ERR_OK:
            raise AmpError("failed to read device status", err)
        return status.Samples, status.Errors, status.Rate, status.Speed

    def readConfiguration(self, rate, force=False):
        """ Update device sampling rate and get new configuration
        @param rate: device base sampling rate
        """
        # not possible if device is already open or not necessary if rate has not changed
        if (self.devicehandle != 0 or rate == self.settings.Rate) and not force:
            return
        # update sampling rate and get new configuration
        try:
            self.open()
            self.setup(self.settings.Mode, rate, self.binning)
        except:
            pass

        try:
            self.close()
        except:
            pass

    def setEmulationMode(self, modules):
        ''' Set/Reset emulation flag in INI file
        @param modules: number of modules to emulate, 0= no emulation
        '''
        # not possible if device is already open
        if self.devicehandle != 0:
            return

        # write new settings to INI file
        ini = configparser.ConfigParser()
        filename = os.path.dirname(os.path.abspath(__file__))
        if self.x64:
            filename += r"\ActiChamp_x64.dll.ini"
        else:
            filename += r"\ActiChamp_x86.dll.ini"

        if len(ini.read(filename)) > 0:
            if modules > 0:
                channels = modules * 32
                ini.set("Main", "Emulation", "1")
                ini.set("Emulation", "Model", repr(channels))
            else:
                ini.set("Main", "Emulation", "0")
            fp = open(filename, "w")
            ini.write(fp)
            fp.close()
        else:
            raise AmpError("INI file %s not found" % filename)

        # reload the DLL
        self.loadLib()
        # get new configuration
        try:
            self.open()
            self.getDeviceInfo()
            self.setup(self.settings.Mode, self.settings.Rate, self.binning)
        except:
            pass

        try:
            self.close()
        except:
            pass

    def readImpedances(self):
        """
        Get the electrode impedance values
        @return: list of impedance values for all EEG channels plus ground electrode in Ohm.
        """
        if not self.running or (self.devicehandle == 0):
            return None, None

        disconnected = None
        # read impedance data from device
        err = self.lib.champImpedanceGetData(self.devicehandle,
                                             ctypes.byref(self.impbuffer),
                                             len(self.impbuffer))

        # dummy read data from device
        err2 = self.lib.champGetData(self.devicehandle,
                                     ctypes.byref(self.buffer),
                                     len(self.buffer))

        if err2 == CHAMP_ERR_MONITORING:
            disconnected = CHAMP_ERR_MONITORING

        if err == CHAMP_ERR_FAIL:
            return None, None

        if err != CHAMP_ERR_OK:
            raise AmpError("failed to read impedance values", err)

        # channel order in buffer is CH1,CH2..CHn, GND
        items = self.properties.CountEeg + 1
        return np.frombuffer(self.impbuffer, np.uint32, items), disconnected

    def setImpedanceRange(self, good, bad):
        """ set ActiCap impedance range
        @param good: impedance value for green LED in Ohm
        @param bad: impedance value for red LED in Ohm
        """
        if self.devicehandle == 0:
            return
        imp_settings = CHAMP_IMPEDANCE_SETUP()
        imp_settings.Good = int(good)
        imp_settings.Bad = int(bad)
        imp_settings.LedsDisable = 0
        imp_settings.TimeOut = 5
        err = self.lib.champImpedanceSetSetup(self.devicehandle, ctypes.byref(imp_settings))
        if err != CHAMP_ERR_OK:
            raise AmpError("failed to set LED impedance range", err)

    def setTrigger(self, trigger):
        """ set trigger output
        @param trigger: trigger values to set 8-bit outputs (bits 0 - 7).
        """
        if self.devicehandle == 0:
            return

        # 8-bit inputs (bits 0 - 7) + 8-bit outputs (bits 8 - 15) + 16 MSB reserved bits.
        trigger = (trigger & 0xFF) << 8
        ct_trigger = ctypes.c_uint(trigger)
        err = self.lib.champSetTriggers(self.devicehandle, ct_trigger)
        if err != CHAMP_ERR_OK:
            raise AmpError("failed to set trigger output", err)

    def setButtonLed(self, period, dutyCycle):
        """ Control MyButton LED via pulse-width modulation
        @param period:  cycle period in [ms]
        @param dutyCycle: duty cycle in [%], 0%=always off, 100%=always on
        """
        if self.devicehandle == 0:
            return
        dutyCycle = max(min(dutyCycle, 100), 0)  # limit to 0-100%
        period = max(min(period, 10000), 1)  # limit to 1-10000ms

        # use a fixed period for on/off
        if dutyCycle == 0 or dutyCycle == 100:
            period = 10

        # convert to C variables
        cPeriod = ctypes.c_uint(period)
        cDutyCycle = ctypes.c_uint(dutyCycle)

        # set LED
        err = self.lib.champSetMyButtonLed(self.devicehandle, cPeriod, cDutyCycle)
        if err != CHAMP_ERR_OK:
            raise AmpError("failed to set MyButton LED", err)

