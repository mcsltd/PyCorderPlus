# -*- coding: utf-8 -*-
"""
Acquisition Module

PyCorderPlus ActiChamp Recorder

------------------------------------------------------------

Copyright (C) 2010, Brain Products GmbH, Gilching
Copyright (C) 2024, Medical Computer Systems Ltd


This file is part of PyCorderPlus
"""
import time
from operator import itemgetter

import numpy as np
from scipy import signal
from PyQt6.QtWidgets import (QFrame,
                             QApplication,
                             QLabel,
                             QGridLayout,
                             QSpacerItem,
                             QSizePolicy,
                             QComboBox,
                             QRadioButton,
                             QGroupBox)
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QFont

from amp_actichamp2.actichamp2_w import ActiChamp2, CHAMP_MODE_NORMAL, CHAMP_MODE_ACTIVE_SHIELD, CHAMP_MODE_IMPEDANCE, \
    CHAMP_MODE_TEST, CHAMP_Modes, CHAMP_MODE_LED_TEST, CHAMP_ERR_MONITORING
from modbase import *

from res import frmActiChampOnline

# enable active shielding mode
AMP_SHIELD_MODE = False

# allow multiple reference channels
AMP_MULTIPLE_REF = True

# hide the reference channel(s), works only without separate montage module
AMP_HIDE_REF = True

# no channel selection within amplifier module, for use with an separate montage module.
AMP_MONTAGE = False

'''
------------------------------------------------------------
AMPLIFIER MODULE
------------------------------------------------------------
'''


class AMP_ActiChamp2(ModuleBase):
    """ ActiChamp EEG amplifier module
    """

    def __init__(self, *args, **keys):
        """ Constructor
        """
        super().__init__(self, name="Amplifier", **keys)

        # XML parameter version
        # 1: initial version
        # 2: input device container added
        # 3: PLL external input
        self.xmlVersion = 3

        # create hardware object
        self.amp = ActiChamp2()  #: amplifier hardware object

        # set default channel configuration
        self.max_eeg_channels = 160  #: number of EEG channels for max. HW configuration
        self.max_aux_channels = 8  #: number of AUX channels for max. HW configuration
        self.max_exg_channels = 2  #: number of ref channels for max. HW configuration
        self.max_ref_channels = 1  #: number of exg channels for max. HW configuration
        self.channel_config = EEG_DataBlock.get_default_properties(
            eeg=self.max_eeg_channels, aux=self.max_aux_channels, exg=self.max_exg_channels, ref=self.max_ref_channels)
        self.recording_mode = CHAMP_MODE_NORMAL

        # create dictionary of possible sampling rates
        self.sample_rates = []
        for rate in [100000.0, 50000.0, 25000.0, 10000.0, 5000.0, 2000.0, 1000.0, 500.0, 200.0]:
            base, div = self.amp.getSamplingRateBase(rate)
            if base >= 0:
                self.sample_rates.append({'rate': str(int(rate)), 'base': base, 'div': div, 'value': rate})

        self.sample_rate = self.sample_rates[7]
        self.binning = self.sample_rate['div']
        self.binningoffset = 0

        # set default data block
        self._create_all_channel_selection()

        # date and time of acquisition start
        self.start_time = datetime.datetime.now()

        # online configuration pane
        self.online_cfg = _OnlineCfgPane(self)
        self.online_cfg.modeChanged.connect(self._online_mode_changed)

        # impedance interval timer
        self.impedance_timer = time.process_time()

        # batter check interval timer and last voltage warning string
        self.battery_timer = time.process_time()
        self.voltage_warning = ""

        # skip the first received data blocks
        self.skip_counter = 5
        self.blocking_counter = 0

        # reset hardware error counter and acquisition time out
        self.initialErrorCount = -1
        self.acquisitionTimeoutCounter = 0
        self.test_counter = 0

    def get_online_configuration(self):
        """
        Get the online configuration pane
        """
        return self.online_cfg

    def get_configuration_pane(self):
        """ Get the configuration pane if available.
        Qt widgets are not reusable, so we have to create it every time
        """
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        # read amplifier configuration
        self.amp.readConfiguration(self.sample_rate['base'], force=True)
        self.update_receivers()
        QApplication.restoreOverrideCursor()
        # create configuration pane
        if AMP_MONTAGE:
            # config = _ConfigurationPane(self)
            config = _DeviceConfigurationPane(self)
            pass
        else:
            config = _DeviceConfigurationPane(self)
        config.dataChanged.connect(self._configuration_changed)
        config.emulationChanged.connect(self._emulation_changed)
        config.rateChanged.connect(self._samplerate_changed)
        return config

    def _samplerate_changed(self, index):
        """
        SIGNAL from configuration pane if sample rate has changed
        """
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        self.sample_rate = self.sample_rates[index]
        self.update_receivers()
        QApplication.restoreOverrideCursor()

    def _configuration_changed(self):
        """
        SIGNAL from configuration pane if values has changed
        """
        self.update_receivers()

    def _emulation_changed(self, index):
        """
        SIGNAL from configuration pane if emulation mode has changed
        """
        try:
            self.amp.setEmulationMode(index)
        except Exception as e:
            self.send_exception(e)
        self.update_receivers()

    def _online_mode_changed(self, new_mode):
        """
        SIGNAL from online configuration pane if recording mode has changed
        """
        if self.amp.running:
            if not self.stop():
                self.online_cfg.updateUI(self.recording_mode)
                return

        if new_mode >= 0:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            self.recording_mode = new_mode
            self.start()
            QApplication.restoreOverrideCursor()

    def _create_all_channel_selection(self):
        """ Create index arrays of all available channels and prepare EEG_DataBlock
        """
        # get all eeg channel indices
        mask = lambda x: (x.group == ChannelGroup.EEG) and (x.input <= self.amp.properties.CountEeg)
        eeg_map = np.array(list(map(mask, self.channel_config)))
        self.eeg_indices = np.nonzero(eeg_map)[0]      # indices of all eeg channels
        self.property_indices = self.eeg_indices

        # get all aux channel indices
        mask = lambda x: (x.group == ChannelGroup.AUX) and (x.input <= self.amp.properties.CountAux)
        aux_map = np.array(list(map(mask, self.channel_config)))
        self.aux_indices = np.nonzero(aux_map)[0]   # indices of all aux channels
        self.property_indices = np.append(self.property_indices, self.aux_indices)

        # get all exg channel indices
        mask = lambda x: (x.group == ChannelGroup.EXG) and (x.input <= self.amp.properties.CountExG)
        exg_map = np.array(list(map(mask, self.channel_config)))
        self.exg_indices = np.nonzero(exg_map)[0]  # indices of all aux channels
        self.property_indices = np.append(self.property_indices, self.exg_indices)

        # get all ref channel indices
        mask = lambda x: (x.group == ChannelGroup.REF) and (x.input <= self.amp.properties.CountRef)
        ref_map = np.array(list(map(mask, self.channel_config)))
        self.ref_indices = np.nonzero(ref_map)[0]  # indices of ref channel
        self.property_indices = np.append(self.property_indices, self.ref_indices)

        # adjust AUX indices to the actual available EEG channels
        self.aux_indices -= (self.max_eeg_channels - self.amp.properties.CountEeg)
        self.exg_indices -= (self.max_eeg_channels - self.amp.properties.CountEeg - self.amp.properties.CountExG)
        self.ref_indices -= (self.max_eeg_channels - self.amp.properties.CountEeg - self.amp.properties.CountExG - self.amp.properties.CountRef)

        self.channel_indices = np.hstack((self.eeg_indices, self.aux_indices, self.exg_indices, self.ref_indices))

        # create a new data block based on channel selection
        self.eeg_data = EEG_DataBlock(eeg=len(self.eeg_indices), aux=len(self.aux_indices),
                                      exg=len(self.exg_indices), ref=len(self.ref_indices))
        self.eeg_data.channel_properties = copy.deepcopy(self.channel_config[self.property_indices])
        self.eeg_data.sample_rate = self.sample_rate['value']

        # reset the reference channel indices
        self.ref_index = np.array([])  # indices of reference channel(s)
        self.eeg_data.ref_channel_name = ""
        self.ref_remove_index = self.ref_index

        # prepare recording mode and antialiasing filters
        self._prepare_mode_and_filters()

    def _prepare_mode_and_filters(self):
        # translate recording modes
        if (self.recording_mode == CHAMP_MODE_NORMAL) or (self.recording_mode == CHAMP_MODE_ACTIVE_SHIELD):
            self.eeg_data.recording_mode = RecordingMode.NORMAL
        elif self.recording_mode == CHAMP_MODE_IMPEDANCE:
            self.eeg_data.recording_mode = RecordingMode.IMPEDANCE
        elif self.recording_mode == CHAMP_MODE_TEST:
            self.eeg_data.recording_mode = RecordingMode.TEST

        # down sampling
        self.binning = self.sample_rate['div']
        self.binningoffset = 0

        # design anti-aliasing filter for down sampling
        # it's an Nth order lowpass Butterworth filter from scipy
        # signal.filter_design.butter(N, Wn, btype='low')
        # N = filter order, Wn = cut-off frequency / nyquist frequency
        # f_nyquist = f_in / 2
        # f_cutoff = f_in / rate_divider * filter_factor
        # Wn = f_cutoff / f_nyquist = f_in / rate_divider * filter_factor / f_in * 2
        # Wn = 1 / rate_divider * 2 * filter_factor
        filter_order = 4
        filter_factor = 0.333
        rate_divider = self.binning
        Wn = 1.0 / rate_divider * 2.0 * filter_factor
        self.aliasing_b, self.aliasing_a = signal.butter(N=filter_order, Wn=Wn, btype='low')
        zi = signal.lfiltic(self.aliasing_b, self.aliasing_a, (0.0,))
        self.aliasing_zi = np.resize(zi, (len(self.channel_indices), len(zi)))

        # define which channels contains which impedance values
        self.eeg_data.eeg_channels[:, :] = 0
        if self.eeg_data.recording_mode == RecordingMode.IMPEDANCE:
            self.eeg_data.eeg_channels[self.eeg_indices, ImpedanceIndex.DATA] = 1
            self.eeg_data.eeg_channels[self.eeg_indices, ImpedanceIndex.GND] = 1

    def setDefault(self):
        """ Set all module parameters to default values
        """
        emulation_mode = self.amp.getEmulationMode() > 0
        self.sample_rate = self.sample_rates[7]  # 500Hz sample rate
        for channel in self.channel_config:
            channel.isReference = False
            if channel.group == ChannelGroup.EEG:
                channel.enable = True  # enable all EEG channels
                if (channel.input == 1) and not emulation_mode:
                    channel.isReference = True  # use first channel as reference
            else:
                channel.enable = False  # disable all AUX channels
        self._set_default_filter()
        self.update_receivers()

    def stop(self, force=False):
        """ Stop data acquisition
        @param force: force stop without query
        @return: True, if stop was accepted by attached modules
        """
        # ask attached modules for acceptance
        if not force:
            if not self.query("Stop"):
                return False
        # stop it
        ModuleBase.stop(self)
        return True

    def process_event(self, event):
        """
        Handle events from attached receivers
        @param event: ModuleEvent
        """
        # Command events
        if event.type == EventType.COMMAND:
            # check for new impedance color range values
            if event.info == "ImpColorRange":
                good, bad = event.cmd_value

                if self.recording_mode == CHAMP_MODE_IMPEDANCE:
                    self._thLock.acquire()
                    try:
                        self.amp.setImpedanceRange(good * 1000, bad * 1000)
                        self._thLock.release()
                    except Exception as e:
                        self._thLock.release()
                        self.send_exception(e, severity=ErrorSeverity.NOTIFY)

            # check for stop command
            if event.info == "Stop":
                if event.cmd_value == "force":
                    self.stop(force=True)
                else:
                    self.stop()

            # check for recording start command
            if event.info == "StartRecording":
                self._online_mode_changed(CHAMP_MODE_NORMAL)

            # check for impedance start command
            if event.info == "StartImpedance":
                self._online_mode_changed(CHAMP_MODE_IMPEDANCE)

            # check for trigger out command
            if event.info == "TriggerOut":
                self._thLock.acquire()
                try:
                    self.amp.setTrigger(event.cmd_value)
                    self._thLock.release()
                except Exception as e:
                    self._thLock.release()
                    self.send_exception(e, severity=ErrorSeverity.NOTIFY)

            # check for button LED command
            # cmd_value is a tuple with period and duty cycle
            if event.info == "SetLED":
                self._thLock.acquire()
                try:
                    self.amp.setButtonLed(event.cmd_value[0], event.cmd_value[1])
                    self._thLock.release()
                except Exception as e:
                    self._thLock.release()
                    self.send_exception(e, severity=ErrorSeverity.NOTIFY)

            # check for acitve shield gain command
            # cmd_value is the gain from 1 to 100
            if event.info == "SetShieldGain":
                self._thLock.acquire()
                self.amp.activeShieldGain = event.cmd_value
                self._thLock.release()

        # Error events
        if event.type == EventType.ERROR or event.type == EventType.LOG:
            # add device status info to "sample missing" events
            if "samples missing" in event.info:
                self._thLock.acquire()
                try:
                    errors = self.amp.getDeviceStatus()[1] - self.initialErrorCount
                    event.info += " (device errors = %d)" % errors
                    self._thLock.release()
                except Exception as e:
                    self._thLock.release()
                    event.info += " (%s)" % (str(e))

    def _set_default_filter(self):
        """ set all filter properties to HW filter values
        """
        for channel in self.channel_config:
            channel.highpass = 0.0  # high pass off
            channel.lowpass = 0.0  # low pass off
            channel.notchfilter = False  # notch filter off

    def _check_reference(self):
        """ check if selected reference channels are consistent with the global flag
        """
        # nothing to do if multiple channels are allowed
        if AMP_MULTIPLE_REF:
            return
        # else keep the first reference channel only
        eeg_ref = np.array(list(map(lambda x: x.isReference, self.channel_config)))
        ref_index = np.nonzero(eeg_ref)[0]  # indices of reference channel(s)
        for ch in self.channel_config[ref_index[1:]]:
            ch.isReference = False

    def get_module_info(self):
        """ Get information about this module for the about dialog
        @return: Serial numbers of amplifier and modules
        """
        return self.amp.getDeviceInfoString()

    def process_start(self):
        """ Open amplifier hardware and start data acquisition
        """
        # reset variables
        self.eeg_data.sample_counter = 0
        self.acquisitionTimeoutCounter = 0
        self.battery_timer = 0
        self.test_counter = 0

        # open and setup hardware
        self.amp.open()

        # check battery
        ok, voltage = self._check_battery()
        if not ok:
            raise ModuleError(self._object_name, "battery low (%.1fV)!" % voltage)

        self.amp.setup(self.recording_mode, self.sample_rate['base'], self.sample_rate['div'])
        self.update_receivers()
        if len(self.channel_indices) == 0:
            raise ModuleError(self._object_name, "no input channels selected!")

        # check battery again
        ok, voltage = self._check_battery()
        if not ok:
            raise ModuleError(self._object_name, "battery low (%.1fV)!" % voltage)

        # start hardware
        self.amp.start()

        # set start time on first call
        self.start_time = datetime.datetime.now()

        # send status info
        if AMP_MONTAGE:
            info = "Start %s at %.0fHz with %d channels" % (CHAMP_Modes[self.recording_mode],
                                                            self.eeg_data.sample_rate,
                                                            len(self.channel_indices))
        else:
            if self.amp.hasPllOption() and self.amp.PllExternal:
                info = "Start %s at %.0fHz (ext. PLL)" % (CHAMP_Modes[self.recording_mode],
                                                          self.eeg_data.sample_rate)
            else:
                info = "Start %s at %.0fHz" % (CHAMP_Modes[self.recording_mode],
                                               self.eeg_data.sample_rate)

        self.send_event(ModuleEvent(self._object_name, EventType.LOGMESSAGE, info))
        # send recording mode
        self.send_event(ModuleEvent(self._object_name,
                                    EventType.STATUS,
                                    info=self.recording_mode,
                                    status_field="Mode"))
        # update button state
        self.online_cfg.updateUI(self.recording_mode)

        # skip the first received data blocks
        self.skip_counter = 5
        self.blocking_counter = 0
        self.initialErrorCount = -1

    def _check_battery(self):
        """ Check amplifier battery voltages
        @return: state (ok=True, bad=False) and voltage
        """
        # read battery state and internal voltages from amplifier
        state, voltages, faultyVoltages = self.amp.getBatteryVoltage()
        severe = ErrorSeverity.IGNORE
        if state == 1:
            severe = ErrorSeverity.NOTIFY
        elif state == 2:
            severe = ErrorSeverity.STOP

        # create and send faulty voltages warning message
        v_warning = ""
        if len(faultyVoltages) > 0:
            severe = ErrorSeverity.NOTIFY
            v_warning = "Faulty internal voltage(s): "
            for u in faultyVoltages:
                v_warning += " %s" % u
            # warning already sent?
            if v_warning != self.voltage_warning:
                self.send_event(ModuleEvent(self._object_name,
                                            EventType.ERROR,
                                            info=v_warning,
                                            severity=severe))
                pass
        self.voltage_warning = v_warning

        # create and send status message
        voltage_info = "%.2fV" % voltages.VDC  # battery voltage
        for u in faultyVoltages:
            voltage_info += "\n%s" % u
        self.send_event(ModuleEvent(self._object_name,
                                    EventType.STATUS,
                                    info=voltage_info,
                                    severity=severe,
                                    status_field="Battery"))
        return state < 2, voltages.VDC

    def process_stop(self):
        """
        Stop data acquisition and close hardware object
        """
        errors = 999
        try:
            errors = self.amp.getDeviceStatus()[1] - self.initialErrorCount  # get number of device errors
        except:
            pass
        try:
            if self.recording_mode == CHAMP_MODE_LED_TEST:
                self.amp.LedTest(0)
            self.amp.stop()
        except:
            pass
        try:
            self.amp.close()
        except:
            pass

        # send status info
        info = "Stop %s" % (CHAMP_Modes[self.recording_mode])
        if (errors > 0) and (self.recording_mode != CHAMP_MODE_IMPEDANCE) and (
                self.recording_mode != CHAMP_MODE_LED_TEST):
            info += " (device errors = %d)" % errors
        self.send_event(ModuleEvent(self._object_name, EventType.LOGMESSAGE, info))
        # send recording mode
        self.send_event(ModuleEvent(self._object_name,
                                    EventType.STATUS,
                                    info=-1,  # stop
                                    status_field="Mode"))
        # update button state
        self.online_cfg.updateUI(-1)

    def process_output(self):
        """ Get data from amplifier
        and return the eeg data block
        """
        t = time.process_time()
        self.eeg_data.performance_timer = 0
        self.eeg_data.performance_timer_max = 0
        self.recordtime = 0.0

        # check battery voltage every 5s
        if (t - self.battery_timer) > 5.0 or self.battery_timer == 0:
            ok, voltage = self._check_battery()
            if not ok:
                raise ModuleError(self._object_name, "battery low (%.1fV)!" % voltage)
            self.battery_timer = t

        if self.recording_mode == CHAMP_MODE_IMPEDANCE:
            return self.process_impedance()

        if self.recording_mode == CHAMP_MODE_LED_TEST:
            return self.process_led_test()

        if self.amp.BlockingMode:
            self._thLock.release()
            try:
                d, disconnected = self.amp.read(
                    self.channel_indices,
                    eegcount=len(self.eeg_indices), auxcount=len(self.aux_indices),
                    refcount=len(self.ref_indices), exgcount=len(self.exg_indices),
                )

            finally:
                self._thLock.acquire()
            self.output_timer = time.process_time()
        else:
            d, disconnected = self.amp.read(
                self.channel_indices,
                eegcount=len(self.eeg_indices), auxcount=len(self.aux_indices),
                refcount=len(self.ref_indices), exgcount=len(self.exg_indices),
            )

        if d is None:
            self.acquisitionTimeoutCounter += 1
            # about 5s timeout
            if self.acquisitionTimeoutCounter > 100:
                self.acquisitionTimeoutCounter = 0
                raise ModuleError(self._object_name, "connection to hardware is broken!")
            # check data rate mismatch messages
            if disconnected == CHAMP_ERR_MONITORING:
                self.send_event(ModuleEvent(self._object_name,
                                            EventType.ERROR,
                                            info="USB data rate mismatch",
                                            severity=ErrorSeverity.NOTIFY))
                pass
            return None
        else:
            self.acquisitionTimeoutCounter = 0

        # skip the first received data blocks
        if self.skip_counter > 0:
            self.skip_counter -= 1
            return None
        # get the initial error counter
        if self.initialErrorCount < 0:
            self.initialErrorCount = self.amp.getDeviceStatus()[1]

        # down sample required?
        if self.binning > 1:
            # anti-aliasing filter
            filtered, self.aliasing_zi = \
                signal.lfilter(self.aliasing_b, self.aliasing_a, d[0], zi=self.aliasing_zi)
            # reduce reslution to avoid limit cycle
            # self.aliasing_zi = np.asfarray(self.aliasing_zi, np.float32)

            self.eeg_data.eeg_channels = filtered[:, self.binningoffset::self.binning]
            self.eeg_data.trigger_channel = np.bitwise_or.reduce(d[1][:].reshape(-1, self.binning), axis=1).reshape(1,
                                                                                                                    -1)
            self.eeg_data.sample_channel = d[2][:, self.binningoffset::self.binning] / self.binning
            self.eeg_data.sample_counter += self.eeg_data.sample_channel.shape[1]
        else:
            self.eeg_data.eeg_channels = d[0]
            self.eeg_data.trigger_channel = d[1]
            self.eeg_data.sample_channel = d[2]
            self.eeg_data.sample_counter += self.eeg_data.sample_channel.shape[1]

        # average, subtract and remove the reference channels
        if len(self.ref_index):
            '''
            # subtract
            for ref_channel in self.eeg_data.eeg_channels[self.ref_index]:
                self.eeg_data.eeg_channels[:len(self.eeg_indices)] -= ref_channel
                # restore reference channel
                self.eeg_data.eeg_channels[self.ref_index[0]] = ref_channel

            # remove single reference channel if not enabled
            if not (len(self.eeg_data.channel_properties) > self.ref_index[0] and
                    self.eeg_data.channel_properties[self.ref_index[0]].isReference ):
                self.eeg_data.eeg_channels = np.delete(self.eeg_data.eeg_channels, self.ref_index, 0)
            '''
            # average reference channels
            reference = np.mean(self.eeg_data.eeg_channels[self.ref_index], 0)

            # subtract reference
            self.eeg_data.eeg_channels[:len(self.eeg_indices)] -= reference

            # remove all disabled reference channels
            if len(self.ref_remove_index) > 0:
                self.eeg_data.eeg_channels = np.delete(self.eeg_data.eeg_channels, self.ref_remove_index, 0)

        # calculate date and time for the first sample of this block in s
        sampletime = self.eeg_data.sample_channel[0][0] / self.eeg_data.sample_rate
        self.eeg_data.block_time = self.start_time + datetime.timedelta(seconds=sampletime)

        # put it into the receiver queues
        eeg = copy.copy(self.eeg_data)
        self.recordtime = time.process_time() - t

        return eeg

    def process_impedance(self):
        """
        Get the impedance values from amplifier
        and return the eeg data block
        """
        t = time.process_time()
        if t - self.impedance_timer < 1.0:
            return None

        # get impedance values from device
        imp, disconnected = self.amp.readImpedances()

        # check data rate mismatch messages
        if imp is None:
            return None

        eeg_imp = imp[self.eeg_indices]
        gnd_imp = imp[-1]

        # invalidate the old impedance data list
        self.eeg_data.impedances = []

        # copy impedance values to data array
        self.eeg_data.eeg_channels = np.zeros((len(self.channel_indices), 10), 'd')
        self.eeg_data.eeg_channels[self.eeg_indices, ImpedanceIndex.DATA] = eeg_imp
        self.eeg_data.eeg_channels[self.eeg_indices, ImpedanceIndex.GND] = gnd_imp

        # dummy values for trigger and sample counter
        self.eeg_data.trigger_channel = np.zeros((1, 10), np.uint32)
        self.eeg_data.sample_channel = np.zeros((1, 10), np.uint32)

        # set recording time
        self.eeg_data.block_time = datetime.datetime.now()

        # put it into the receiver queues
        eeg = copy.copy(self.eeg_data)
        return eeg

    def process_led_test(self):
        """ toggle LEDs on active electrodes
        and return no eeg data
        """
        # dummy read data
        d, disconnected = self.amp.read(self.channel_indices, len(self.eeg_indices), len(self.aux_indices))

        # toggle LEDs twice per second
        t = time.process_time()
        if (t - self.impedance_timer) < 0.5:
            return None
        self.impedance_timer = t

        # toggle all LEDs between off, green and red
        if self.test_counter % 3 == 0:
            self.amp.LedTest(0)
        elif self.test_counter % 3 == 1:
            self.amp.LedTest(11)
        else:
            self.amp.LedTest(12)

        self.test_counter += 1
        return None

    def process_update(self, params):
        """
        Prepare channel properties and propagate update to all connected receivers
        """
        # update device sampling rate and get new configuration
        try:
            self.amp.readConfiguration(self.sample_rate['base'])
        except Exception as e:
            self.send_exception(e)

        # indicate amplifier simulation
        if self.amp.getEmulationMode() > 0:
            self.online_cfg.groupBoxMode.setTitle("Amplifier SIMULATION")
        else:
            self.online_cfg.groupBoxMode.setTitle("actiCHamp2")

        # create channel selection maps
        if AMP_MONTAGE:
            # self._create_channel_selection()
            self.send_event(ModuleEvent(self._object_name,
                                        EventType.STATUS,
                                        info="%d ch" % (len(self.channel_indices)),
                                        status_field="Channels"))
        else:
            self._create_all_channel_selection()

        # send current status as event
        self.send_event(ModuleEvent(self._object_name,
                                    EventType.STATUS,
                                    info="%.0f Hz" % self.eeg_data.sample_rate,
                                    status_field="Rate"))
        return copy.copy(self.eeg_data)

    def getXML(self):
        ''' Get module properties for XML configuration file
        @return: objectify XML element::
            <ActiChamp instance="0" version="1" module="amplifier">
                <channels>
                    ...
                </channels>
                <samplerate>1000</samplerate>
            </ActiChamp>
        '''
        E = objectify.E

        channels = E.channels()
        if AMP_MONTAGE:
            for channel in self.channel_config:
                channels.append(channel.getXML())

        amplifier = E.AMP_ActiChamp(E.samplerate(self.sample_rate['value']),
                                    E.pllexternal(self.amp.PllExternal),
                                    channels,
                                    # devices,
                                    version=str(self.xmlVersion),
                                    instance=str(self._instance),
                                    module="amplifier")
        return amplifier

    def setXML(self, xml):
        ''' Set module properties from XML configuration file
        @param xml: complete objectify XML configuration tree,
        module will search for matching values
        '''
        # set default values in case we get no configuration data
        # self.inputDevices.reset()

        # search my configuration data
        amps = xml.xpath("//AMP_ActiChamp2[@module='amplifier' and @instance='%i']" % self._instance)
        if len(amps) == 0:
            return  # configuration data not found, leave everything unchanged

        cfg = amps[0]  # we should have only one amplifier instance from this type

        # check version, has to be lower or equal than current version
        version = cfg.get("version")
        if (version is None) or (int(version) > self.xmlVersion):
            self.send_event(ModuleEvent(self._object_name, EventType.ERROR, "XML Configuration: wrong version"))
            return
        version = int(version)

        # get the values
        try:
            # setup channel configuration from xml
            for idx, channel in enumerate(cfg.channels.iterchildren()):
                self.channel_config[idx].setXML(channel)
            # reset filter properties to default values (because configuration has been moved to filter module)
            self._set_default_filter()
            # validate reference channel selection
            self._check_reference()
            # set closest matching sample rate
            sr = cfg.samplerate.pyval
            for rate in sorted(self.sample_rates, key=itemgetter('value')):
                if rate["value"] >= sr:
                    self.sample_rate = rate
                    break
            if version >= 3:
                self.amp.PllExternal = cfg.pllexternal.pyval
            else:
                self.amp.PllExternal = 0

        except Exception as e:
            self.send_exception(e, severity=ErrorSeverity.NOTIFY)


"""
Amplifier module online GUI.
"""


class _OnlineCfgPane(QFrame, frmActiChampOnline.Ui_frmActiChampOnline):
    """ ActiChamp online configuration pane
    """
    modeChanged = pyqtSignal(int)

    def __init__(self, amp, *args):
        """ Constructor
        @param amp: parent module object
        """
        super().__init__()
        self.setupUi(self)
        self.amp = amp

        self.groupBoxMode.setTitle("actiCHamp2")
        # set default values
        self.pushButtonStop.setChecked(True)

        # re-assign the shielding button
        if not AMP_SHIELD_MODE:
            self.pushButtonStartShielding.setText("Electrode LED\nTest")

        # actions
        self.pushButtonStartDefault.clicked.connect(self._button_toggle)
        self.pushButtonStartImpedance.clicked.connect(self._button_toggle)
        self.pushButtonStartShielding.clicked.connect(self._button_toggle)
        self.pushButtonStartTest.clicked.connect(self._button_toggle)
        self.pushButtonStop.clicked.connect(self._button_toggle)


    def _button_toggle(self, checked):
        """ SIGNAL if one of the push buttons is clicked
        """
        if checked:
            mode = -1  # stop
            if self.pushButtonStartDefault.isChecked():
                mode = CHAMP_MODE_NORMAL
            elif self.pushButtonStartShielding.isChecked():
                if AMP_SHIELD_MODE:
                    mode = CHAMP_MODE_ACTIVE_SHIELD
                else:
                    mode = CHAMP_MODE_LED_TEST
            elif self.pushButtonStartImpedance.isChecked():
                mode = CHAMP_MODE_IMPEDANCE
            elif self.pushButtonStartTest.isChecked():
                mode = CHAMP_MODE_TEST
            self.modeChanged.emit(mode)

    def updateUI(self, mode):
        ''' Update user interface according to recording mode
        '''
        if mode == CHAMP_MODE_NORMAL:
            self.pushButtonStartDefault.setChecked(True)
        elif mode == CHAMP_MODE_ACTIVE_SHIELD or mode == CHAMP_MODE_LED_TEST:
            self.pushButtonStartShielding.setChecked(True)
        elif mode == CHAMP_MODE_IMPEDANCE:
            self.pushButtonStartImpedance.setChecked(True)
        elif mode == CHAMP_MODE_TEST:
            self.pushButtonStartTest.setChecked(True)
        else:
            self.pushButtonStop.setChecked(True)


'''
Amplifier module configuration GUI(with input device selection).
'''


class _DeviceConfigurationPane(QFrame):
    """
    ActiChamp configuration pane
    """

    rateChanged = pyqtSignal(int)
    emulationChanged = pyqtSignal(int)
    dataChanged = pyqtSignal()

    def __init__(self, amplifier, *args):
        super().__init__()

        # reference to our parent module
        self.amplifier = amplifier

        # Set tab name
        self.setWindowTitle("Amplifier")

        # make it nice
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)

        # base layout
        self.gridLayout = QGridLayout(self)

        # spacers
        self.vspacer_1 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        self.vspacer_2 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        self.vspacer_3 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        self.hspacer_1 = QSpacerItem(20, 40, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        # create the amplifier GUI elements
        self.comboBoxSampleRate = QComboBox()
        self.comboBoxEmulation = QComboBox()
        self.label_Simulated = QLabel()

        self.labelPLL = QLabel("PLL Input")
        self.radioPllInternal = QRadioButton("Internal")
        self.radioPllExternal = QRadioButton("External")

        self.label_AvailableChannels = QLabel("Available channels: 32 EEG and 5 AUX")
        self.label_AvailableChannels.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        # self.label_AvailableChannels.setIndent(20)
        font = QFont("Ms Shell Dlg 2", 10)
        self.label_AvailableChannels.setFont(font)

        self.label_1 = QLabel("Sampling Rate")
        self.label_2 = QLabel("[Hz]")
        self.label_3 = QLabel("Simulation")
        self.label_4 = QLabel("Module(s)")

        # group amplifier elements
        self.groupAmplifier = QGroupBox("Amplifier Configuration")

        self.gridLayoutAmp = QGridLayout()
        self.gridLayoutAmp.addWidget(self.label_1, 0, 0)
        self.gridLayoutAmp.addWidget(self.comboBoxSampleRate, 0, 1)
        self.gridLayoutAmp.addWidget(self.label_2, 0, 2)
        self.gridLayoutAmp.addWidget(self.label_3, 1, 0)
        self.gridLayoutAmp.addWidget(self.comboBoxEmulation, 1, 1)
        self.gridLayoutAmp.addWidget(self.label_4, 1, 2)
        self.gridLayoutAmp.addWidget(self.label_Simulated, 2, 1, 1, 2)

        self.gridLayoutAmp.addWidget(self.labelPLL, 3, 0)
        self.gridLayoutAmp.addWidget(self.radioPllInternal, 3, 1)
        self.gridLayoutAmp.addWidget(self.radioPllExternal, 4, 1)
        self.gridLayoutAmp.addItem(self.vspacer_1, 5, 0, 1, 3)

        self.gridLayoutAmpGroup = QGridLayout()
        self.gridLayoutAmpGroup.addLayout(self.gridLayoutAmp, 0, 0, 2, 1)
        self.gridLayoutAmpGroup.addItem(self.hspacer_1, 0, 1)
        self.gridLayoutAmpGroup.addWidget(self.label_AvailableChannels, 0, 2)
        self.gridLayoutAmpGroup.addItem(self.vspacer_2, 1, 1)

        self.groupAmplifier.setLayout(self.gridLayoutAmpGroup)

        # add all items to the main layout
        self.gridLayout.addWidget(self.groupAmplifier, 0, 0)

        # actions
        self.comboBoxSampleRate.currentIndexChanged.connect(self._samplerate_changed)
        self.comboBoxEmulation.currentIndexChanged.connect(self._emulationChanged)

        # emulation combobox
        self.comboBoxEmulation.addItems(["off", "1", "2", "3", "4", "5"])
        self.comboBoxEmulation.setCurrentIndex(self.amplifier.amp.getEmulationMode())

        # sample rate combobox
        sr_index = -1
        for sr in self.amplifier.sample_rates:
            self.comboBoxSampleRate.addItem(sr['rate'])
            if sr == self.amplifier.sample_rate:
                sr_index = self.comboBoxSampleRate.count() - 1
        self.comboBoxSampleRate.setCurrentIndex(sr_index)

        # available channels display
        self._updateAvailableChannels()

        # PLL configuration
        self.radioPllExternal.setChecked(self.amplifier.amp.PllExternal != 0)
        self.radioPllInternal.setChecked(self.amplifier.amp.PllExternal == 0)
        self.showPllParams(self.amplifier.amp.hasPllOption())
        self.radioPllExternal.toggled.connect(self._pllExternalToggled)

    def _samplerate_changed(self, index):
        ''' SIGNAL sample rate combobox value has changed
        '''
        if index >= 0:
            # notify parent about changes
            self.rateChanged.emit(index)
            self._updateAvailableChannels()

    def _emulationChanged(self, index):
        ''' SIGNAL emulation mode combobox value has changed
        '''
        if index >= 0:
            # notify parent about changes
            self.emulationChanged.emit(index)
            # simulated channels
            if index > 0:
                self.label_Simulated.setText("simulating %i + 8 channels" % (index * 32))
            else:
                self.label_Simulated.setText("")
            self._updateAvailableChannels()

    def _configurationDataChanged(self):
        self.dataChanged.emit()

    def _updateAvailableChannels(self):
        eeg = self.amplifier.amp.properties.CountEeg
        aux = self.amplifier.amp.properties.CountAux
        exg = self.amplifier.amp.properties.CountExG
        ref = self.amplifier.amp.properties.CountRef
        if self.amplifier.amp.getEmulationMode() == 0:
            amp = "actiCHamp2"
        else:
            amp = "Simulation"
        self.label_AvailableChannels.setText("Amplifier: %s\n\nAvailable channels: %d EEG, %d AUX, %d EXG, %d REF" % (amp, eeg, aux, exg, ref))

    def showEvent(self, event):
        pass

    def showPllParams(self, show):
        self.labelPLL.setVisible(show)
        self.radioPllExternal.setVisible(show)
        self.radioPllInternal.setVisible(show)

    def _pllExternalToggled(self, checked):
        if checked:
            self.amplifier.amp.PllExternal = 1
        else:
            self.amplifier.amp.PllExternal = 0

