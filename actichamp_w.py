# -*- coding: utf-8 -*-
"""
Python wrapper for ActiChamp Windows library

ActiChamp_x86.dll (32-Bit) and ActiChamp_x64.dll (64-Bit)
PyCorder ActiChamp Recorder

------------------------------------------------------------

Copyright (C) 2010, Brain Products GmbH, Gilching

This file is part of PyCorder

PyCorder is free software: you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 3
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with PyCorder. If not, see <http://www.gnu.org/licenses/>.

------------------------------------------------------------

@author: Norbert Hauser
@version: 1.0
"""

import ctypes
import ctypes.wintypes
import _ctypes
import numpy as np
import time
import configparser
import platform

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
CHAMP_VERSION = 0x190E0804  # 25.14.08.04 DLL

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
# if you want to do the decimation and filtering in Python (amplifier.py) then
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


class CHAMP_SETTINGS(ctypes.Structure):
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


class CHAMP_PROPERTIES(ctypes.Structure):
    """ C amplifier properties
    """
    _pack_ = 1
    _fields_ = [("CountEeg", ctypes.c_uint),  # number of Eeg channels
                ("CountAux", ctypes.c_uint),  # number of Aux channels
                ("TriggersIn", ctypes.c_uint),  # numbers of input triggers
                ("TriggersOut", ctypes.c_uint),  # numbers of output triggers
                ("Rate", ctypes.c_float),  # sampling rate, Hz
                ("ResolutionEeg", ctypes.c_float),  # EEG amplitude scale coefficients, V/bit
                ("ResolutionAux", ctypes.c_float),  # AUX amplitude scale coefficients, V/bit
                ("RangeEeg", ctypes.c_float),  # EEG input range peak-peak, V
                ("RangeAux", ctypes.c_float)]  # AUX input range peak-peak, V


class CHAMP_IMPEDANCE_SETUP(ctypes.Structure):
    """ C impedance settings
    """
    _pack_ = 1
    _fields_ = [("Good", ctypes.c_uint),  # Good level (green led indication), Ohm
                ("Bad", ctypes.c_uint),  # Bad level (red led indication), Ohm
                ("LedsDisable", ctypes.c_uint),  # Disable electrode's leds, if not zero
                ("TimeOut", ctypes.c_uint)]  # Impedance mode time-out (0 - 65535), sec


class CHAMP_DATA_STATUS(ctypes.Structure):
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


class CHAMP_VERSION_INFO(ctypes.Structure):
    """ C DLL, USB driver and firmware versions
    """
    _pack_ = 1
    _fields_ = [('DLL', ctypes.wintypes.DWORD),  # DLL version
                ('USBDRV', ctypes.wintypes.DWORD),  # USB driver version
                ('USBCTRL', ctypes.wintypes.DWORD),  # USB controller firmware version
                ('FPGA', ctypes.wintypes.DWORD),  # FPGA firmware version
                ('DSP', ctypes.wintypes.DWORD)]  # MSP430 firmware version


class CHAMP_VERSION_INFO_EXT(ctypes.Structure):
    """ C DLL, USB driver and firmware versions for board revision 6
    """
    _pack_ = 1
    _fields_ = [('DLL', ctypes.wintypes.DWORD),  # DLL version
                ('USBDRV', ctypes.wintypes.DWORD),  # USB driver version
                ('USBCTRL', ctypes.wintypes.DWORD),  # USB controller firmware version
                ('FPGAM', ctypes.wintypes.DWORD),  # Media converter FPGA firmware version
                ('DSP', ctypes.wintypes.DWORD),  # MSP430 firmware version
                ('FPGAC', ctypes.wintypes.DWORD)]  # Carrier board FPGA firmware version


class CHAMP_VOLTAGES(ctypes.Structure):
    """ C Amplifier voltages and temperature
    The voltages DVDD3, AVDD3, AVDD5 and REF are valid only during data acquisition
    """
    _pack_ = 1
    _fields_ = [('VDC', ctypes.c_float),  # Power supply, [V]
                ('V3', ctypes.c_float),  # Internal 3.3, [V]
                ('TEMP', ctypes.c_float),  # Temperature, degree Celsius
                ('DVDD3', ctypes.c_float),  # Digital 3.3, [V]
                ('AVDD3', ctypes.c_float),  # Analog 3.3, [V]
                ('AVDD5', ctypes.c_float),  # Analog 5.0, [V]
                ('REF', ctypes.c_float)]  # Reference 2.048, [V]


class CHAMP_MODULES(ctypes.Structure):
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
        pass


class ActiChamp:
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
        self.modulestate = CHAMP_MODULES()  #: actiCHamp module connection state structure
        self.properties = CHAMP_PROPERTIES()  #: actiCHamp property structure
        self.settings = CHAMP_SETTINGS()  #: actiCHamp settings structure
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
        self.binning_buffer = ctypes.create_string_buffer(100 * 170 * 4)  #: binning buffer
        self.binning = 1  #: binning size for buffer alignment
        self.binning_offset = 0  #: raw data buffer offset in bytes for binning

        self.sampleCounterAdjust = 0  #: sample counter wrap around, HW counter is 32bit value but we need 64bit
        self.BlockingMode = True  #: read data in blocking mode
        self.EmulationMode = False  #: emulate hardware

        # set default properties
        self.properties.CountEeg = 32
        self.properties.CountAux = 8
        self.properties.TriggersIn = 8
        self.properties.TriggersOut = 8
        self.properties.Rate = 10000.0
        self.properties.ResolutionEeg = 4.88e-08
        self.properties.ResolutionAux = 2.98e-07
        self.properties.RangeEeg = 0.819
        self.properties.RangeAux = 5.0

        # load ActiChamp 32 or 64 bit windows library
        self.lib = None
        self.loadLib()

        # get and check DLL version
        self.ampversion.read(self.lib, self.devicehandle)
        if self.ampversion.DLL() != CHAMP_VERSION:
            raise AmpError("wrong ActiChamp DLL version (%X / %X)" % (self.ampversion.DLL(),
                                                                      CHAMP_VERSION))

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
            # unload existing library
            if self.lib is not None:
                _ctypes.FreeLibrary(self.lib._handle)
                # load/reload library
            if self.x64:
                self.lib = ctypes.windll.LoadLibrary("ActiChamp_x64.dll")
                self.lib.champOpen.restype = ctypes.c_uint64
            else:
                self.lib = ctypes.windll.LoadLibrary("ActiChamp_x86.dll")
        except:
            self.lib = None
            if self.x64:
                raise AmpError("failed to open library (ActiChamp_x64.dll)")
            else:
                raise AmpError("failed to open library (ActiChamp_x86.dll)")
