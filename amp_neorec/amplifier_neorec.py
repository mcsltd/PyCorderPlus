import time
from operator import itemgetter

from modbase import *
from amp_neorec.neorec import *
from scipy import signal

from res import frmNeoRecOnline
from res import frmNeoRecConfiguration

from PyQt6.QtWidgets import (QFrame, QApplication)
from PyQt6.QtCore import pyqtSignal


class AMP_NeoRec(ModuleBase):
    """
    NeoRec devices module
    """
    disconnect_signal = pyqtSignal()

    def __init__(self, *args, **kwargs):
        super().__init__(name="Amplifier", **kwargs)

        # create hardware object
        self.amp = NeoRec()

        self.model = None  # Device model
        self.sn = None  # Serial Number

        # set default channel configuration
        self.max_eeg_channels = 21  #: number of EEG channels for max. HW configuration
        self.max_aux_channels = 0  #: number of AUX channels for max. HW configuration

        self.channel_config = EEG_DataBlock.get_default_properties(self.max_eeg_channels, self.max_aux_channels)
        self.recording_mode = NR_MODE_DATA

        # create dictionary of possible sampling rates
        self.sample_rates = []
        for rate in [125.0, 250.0, 500.0, 1000.0]:
            base, div = self.amp.getSamplingRateBase(rate)
            if base >= 0:
                self.sample_rates.append({'rate': str(int(rate)), 'base': base, 'div': div, 'value': rate})

        # create dictionary of possible dynamic ranges
        self.dynamic_ranges = []
        for range in [150.0, 300.0]:
            base = self.amp.getDynamicRangeBase(range)
            self.dynamic_ranges.append({"range": str(range), "base": base})

        # create dictionary of possible performance modes
        self.performance_modes = [{"mode": "Maximum", "base": NR_BOOST_MAXIMUM},
                                  {"mode": "Optimal", "base": NR_BOOST_OPTIMUM}]

        # default setup for sample rate, dynamic range, performance mode
        self.sample_rate = self.sample_rates[0]
        self.dynamic_range = self.dynamic_ranges[0]
        self.performance_mode = self.performance_modes[NR_BOOST_OPTIMUM]

        self.binning = self.sample_rate['div']
        self.binningoffset = 0

        # date and time of acquisition start
        self.start_time = datetime.datetime.now()

        # set default data block
        self._create_all_channel_selection()

        # impedance interval timer
        self.impedance_timer = time.process_time()

        # batter check interval timer and last voltage warning string
        self.battery_timer = time.process_time()
        self.voltage_warning = ""

        # create online configuration pane
        self.online_cfg = _OnlineCfgPane(self)
        self.online_cfg.modeChanged.connect(self._online_mode_changed)

        # skip the first received data blocks
        self.skip_counter = 5
        self.blocking_counter = 0

        # reset hardware error counter and acquisition time out
        self.initialErrorCount = -1
        self.acquisitionTimeoutCounter = 0
        self.test_counter = 0

    def get_online_configuration(self):
        """ Get the online configuration pane
        """
        return self.online_cfg

    def get_configuration_pane(self):
        """
        Get the configuration pane if available.
        Qt widgets are not reusable, so we have to create it every time
        """
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        # read amplifier configuration
        self.amp.readConfiguration(
            rate=self.sample_rate["base"],
            range=self.dynamic_range["base"],
            boost=self.performance_mode["base"],
            force=True
        )
        self.update_receivers()
        QApplication.restoreOverrideCursor()
        # create configuration pane
        config = _DeviceConfigurationPane(self)
        config.rateChanged.connect(self._samplerate_changed)
        config.rangeChanged.connect(self._dynamicrange_changed)
        config.modeChanged.connect(self._performancemode_changed)
        return config

    def _dynamicrange_changed(self, index):
        """ SIGNAL from configuration pane if dynamic range has changed
        """
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        self.dynamic_range = self.dynamic_ranges[index]
        self.update_receivers()
        QApplication.restoreOverrideCursor()

    def _performancemode_changed(self, index):
        """ SIGNAL from configuration pane if performance mode has changed"""
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        self.performance_mode = self.performance_modes[index]
        self.update_receivers()
        QApplication.restoreOverrideCursor()

    def _samplerate_changed(self, index):
        """ SIGNAL from configuration pane if sample rate has changed
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

    def _create_all_channel_selection(self):
        """
        Create index arrays of all available channels and prepare EEG_DataBlock
        """
        # get all eeg channel indices
        mask = lambda x: (x.group == ChannelGroup.EEG) and (x.input <= self.amp.CountEeg)
        eeg_map = np.array(list(map(mask, self.channel_config)))
        self.eeg_indices = np.nonzero(eeg_map)[0]  # indices of all eeg channels

        # get all aux channel indices
        mask = lambda x: (x.group == ChannelGroup.AUX) and (x.input <= self.amp.CountAux)
        eeg_map = np.array(list(map(mask, self.channel_config)))
        self.aux_indices = np.nonzero(eeg_map)[0]  # indices of all aux channels
        self.property_indices = np.append(self.eeg_indices, self.aux_indices)

        # adjust AUX indices to the actual available EEG channels
        self.aux_indices -= (self.max_eeg_channels - self.amp.CountEeg)
        self.channel_indices = np.append(self.eeg_indices, self.aux_indices)

        # create a new data block based on channel selection
        self.eeg_data = EEG_DataBlock(len(self.eeg_indices), len(self.aux_indices))
        self.eeg_data.channel_properties = copy.deepcopy(self.channel_config[self.property_indices])
        self.eeg_data.sample_rate = self.sample_rate['value']

        # reset the reference channel indices
        self.ref_index = np.array([])  # indices of reference channel(s)
        self.eeg_data.ref_channel_name = ""
        self.ref_remove_index = self.ref_index

        # prepare recording mode and anti aliasing filters
        self._prepare_mode_and_filters()

    def connection(self):
        """
        NeoRec amplifier detection and opening
        :return:
        """
        # search, open and get NeoRec properties
        res = self.amp.open()

        # if res == NR_ERR_OK and self.amp.CountEeg != self.max_eeg_channels:
        #     # self.channel_config = EEG_DataBlock.get_default_properties(self.max_eeg_channels, self.max_aux_channels)
        #     self._create_all_channel_selection()
        #     self.update_receivers()

        return res

    def _prepare_mode_and_filters(self):
        # translate recording modes
        if self.recording_mode == NR_MODE_DATA:
            self.eeg_data.recording_mode = RecordingMode.NORMAL
        elif self.recording_mode == NR_MODE_IMPEDANCE:
            self.eeg_data.recording_mode = RecordingMode.IMPEDANCE

        # down sampling
        self.binning = self.sample_rate['div']
        self.binningoffset = 0

        filter_order = 4
        filter_factor = 0.333
        rate_divider = self.binning
        Wn = 1.0 / rate_divider * 2.0 * filter_factor
        self.aliasing_b, self.aliasing_a = signal.filter_design.butter(filter_order, Wn, btype='low')
        zi = signal.lfiltic(self.aliasing_b, self.aliasing_a, (0.0,))
        self.aliasing_zi = np.resize(zi, (len(self.channel_indices), len(zi)))

        # define which channels contains which impedance values
        self.eeg_data.eeg_channels[:, :] = 0
        if self.eeg_data.recording_mode == RecordingMode.IMPEDANCE:
            self.eeg_data.eeg_channels[self.eeg_indices, ImpedanceIndex.DATA] = 1
            self.eeg_data.eeg_channels[self.eeg_indices, ImpedanceIndex.GND] = 1

    def _set_default_filter(self):
        """
        Set all filter properties to HW filter values
        """
        for channel in self.channel_config:
            channel.highpass = 0.0  # high pass off
            channel.lowpass = 0.0  # low pass off
            channel.notchfilter = False  # notch filter off

    def setDefault(self):
        """
        Set all module parameters to default values
        """
        self.sample_rate = self.sample_rates[0]  # 125Hz sample rate
        self.dynamic_range = self.dynamic_ranges[0]  # 150 mV dynamic range
        self.performance_mode = self.performance_modes[NR_BOOST_OPTIMUM]   # mode Optimal

        for channel in self.channel_config:
            channel.isReference = False
            if channel.group == ChannelGroup.EEG:
                channel.enable = True  # enable all EEG channels
                if channel.input == 1:
                    channel.isReference = True  # use first channel as reference
            else:
                channel.enable = False  # disable all AUX channels

        self._set_default_filter()

        # if NeoRec is connected, set the appropriate channel names
        if self.model is not None:
            self._set_eeg_channel_names()

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

    def process_event(self, event):
        """
        Handle events from attached receivers
        :param event:
        :return:
        """
        if event.type == EventType.COMMAND:
            # check for stop command
            if event.info == "Stop":
                if event.cmd_value == "force":
                    self.stop(force=True)
                else:
                    self.stop()

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

    def process_update(self, params):
        """
        Prepare channel properties and propagate update to all connected receivers
        :return:
        """
        # update device sampling rate and get new configuration
        try:
            self.amp.readConfiguration(
                rate=self.sample_rate["base"],
                range=self.dynamic_range["base"],
                boost=self.performance_mode["base"],
            )
        except Exception as err:
            pass

        # create channel selection maps
        self._create_all_channel_selection()

        # send current status as event
        self.send_event(
            ModuleEvent(
                self._object_name,
                EventType.STATUS,
                info=f"{self.eeg_data.sample_rate} Hz",
                status_field="Rate"
            )
        )

        return copy.copy(self.eeg_data)

    def process_start(self):
        """
        Open amplifier hardware and start data acquisition
        """
        # reset variables
        self.eeg_data.sample_counter = 0
        self.acquisitionTimeoutCounter = 0
        self.battery_timer = 0
        self.test_counter = 0

        # check battery
        self._check_battery()

        # setup hardware
        flag = self.amp.setup(
            mode=self.recording_mode,
            rate=self.sample_rate["base"],
            range=self.dynamic_range["base"],
            boost=self.performance_mode["base"]
        )

        # case of disconnection
        # if not flag:
        #     # set connection state
        #     self.amp.connected = False
        #     # emit signal start search device
        #     self.disconnect_signal.emit()
        #     raise ModuleError(self._object_name, "disconnected")

        self.update_receivers()

        if len(self.channel_indices) == 0:
            raise

        # start hardware
        self.amp.start()

        # set start time on first call
        self.start_time = datetime.datetime.now()

        # send status info in log
        self.send_event(
            ModuleEvent(
                self._object_name,
                EventType.LOGMESSAGE,
                info=f"Start {NR_Modes[self.recording_mode]} at {int(self.eeg_data.sample_rate)}Hz"
            )
        )

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
        """
        Check Amplifier NeoRec battery
        :return:
        """
        # read battery state
        self.amp.getBatteryInfo()

    def process_output(self):
        """
        Get data from amplifier
        and return the eeg data block
        """
        t = time.process_time()
        self.eeg_data.performance_timer = 0
        self.eeg_data.performance_timer_max = 0
        self.recordtime = 0.0

        # check battery voltage every 5s
        if (t - self.battery_timer) > 5.0 or self.battery_timer == 0:
            self._check_battery()
            self.battery_timer = t

        if self.recording_mode == NR_MODE_IMPEDANCE:
            return self.process_impedance()

        if self.amp.BlockingMode:
            self._thLock.release()
            try:
                d, disconnected = self.amp.read(self.channel_indices, len(self.eeg_indices))
            finally:
                self._thLock.acquire()
            self.output_timer = time.process_time()
        else:
            d, disconnected = self.amp.read(self.channel_indices, len(self.eeg_indices))

        if d is None:
            self.acquisitionTimeoutCounter += 1

            # about 5s timeout
            if self.acquisitionTimeoutCounter > 500:
                self.acquisitionTimeoutCounter = 0
                self.amp.connected = False
                # add search device NeoRec signal
                # raise

            return None
        else:
            self.acquisitionTimeoutCounter = 0

        # skip the first received data blocks
        if self.skip_counter > 0:
            self.skip_counter -= 1
            return None

        # get the initial error counter
        if self.initialErrorCount < 0:
            # self.initialErrorCount = self.amp.getDeviceStatus()[1]
            pass

        # down sample required?
        if self.binning > 1:
            # anti-aliasing filter
            filtered, self.aliasing_zi = \
                signal.lfilter(self.aliasing_b, self.aliasing_a, d[0], zi=self.aliasing_zi)
            # reduce reslution to avoid limit cycle
            # self.aliasing_zi = np.asfarray(self.aliasing_zi, np.float32)

            self.eeg_data.eeg_channels = filtered[:, self.binningoffset::self.binning]
            self.eeg_data.sample_channel = int(d[1][:, self.binningoffset::self.binning] / self.binning)
            self.eeg_data.sample_counter += self.eeg_data.sample_channel.shape[1]
        else:
            self.eeg_data.eeg_channels = d[0]
            self.eeg_data.sample_channel = d[1]
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
        sampletime = int(self.eeg_data.sample_channel[0][0] / self.eeg_data.sample_rate)
        self.eeg_data.block_time = self.start_time + datetime.timedelta(seconds=sampletime)

        # put it into the receiver queues
        eeg = copy.copy(self.eeg_data)
        self.recordtime = time.process_time() - t

        return eeg

    def process_stop(self):
        """
        Stop data acquisition and stop hardware object
        """
        try:
            self.amp.stop()
        except:
            pass

        # send status info in log
        self.send_event(
            ModuleEvent(
                self._object_name,
                EventType.LOGMESSAGE,
                info=f"Stop {NR_Modes[self.recording_mode]}"
            )
        )

        # send recording mode
        self.send_event(
            ModuleEvent(
                self._object_name,
                EventType.STATUS,
                info=-1,  # stop
                status_field="Mode"
            )
        )

        # update button state
        self.online_cfg.updateUI(-1)

    def process_idle(self):
        """ Check if record time exceeds 200ms over a period of 10 blocks
        and adjust idle time to record time
        """
        if self.recordtime > 0.2:
            self.blocking_counter += 1
            # drop blocks if exceeded
            if self.blocking_counter > 10:
                self.skip_counter = 10
                self.blocking_counter = 0
        else:
            self.blocking_counter = 0

        # adjust idle time to record time
        idletime = max(0.06 - self.recordtime, 0.02)

        if self.amp.BlockingMode:
            time.sleep(0.001)
        else:
            time.sleep(idletime)  # suspend the worker thread for 60ms

    def process_impedance(self):
        """
        Get the impedance values from amplifier
        and return the eeg data block
        """
        # send values only once per second
        t = time.process_time()
        if (t - self.impedance_timer) < 1.0:
            return None
        self.impedance_timer = t

        # get impedance values from device
        imp, disconnected = self.amp.readImpedances()

        if imp is None:
            return None

        eeg_imp = imp[self.eeg_indices]
        gnd_imp = imp[-1]
        self.eeg_data.impedances = eeg_imp.tolist()
        self.eeg_data.impedances.append(gnd_imp)

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

    def set_info(self):
        """
        Receive and save information about the type of amplifier connected.
        :return:
        """
        # save amplifier model and serial number
        self.model = self.amp.info.Model
        self.sn = self.amp.info.SerialNumber

        self._set_eeg_channel_names()
        self.update_receivers()

    def _set_eeg_channel_names(self):
        """
        Set channel names depending on NeoRec model.
        :return:
        """
        # set amplifier channel names
        if self.model in NR_Models:

            if NR_Models[self.model] == "NeoRec 21":
                # set channel names for NeoRec 21
                self.channel_config = EEG_DataBlock.get_default_properties(
                    self.max_eeg_channels,
                    self.max_aux_channels,
                    eeg_ch_names=NR_NAME_CHANNEL_EEG21
                )

            if NR_Models[self.model] == "NeoRec mini":
                # set channel names for NeoRec mini
                self.channel_config = EEG_DataBlock.get_default_properties(
                    self.max_eeg_channels,
                    self.max_aux_channels,
                    eeg_ch_names=NR_NAME_CHANNEL_EEG21S
                )

    def getXML(self):
        """
        Get properties for XML configuration file
        :return: objectify XML element
            <NeoRec instance="0" module="amplifier">
                <model>1902</model>
                <channels>
                    ...
                </channels>
                <samplerate>1000</samplerate>
                <dynamicrange>0</dynamicrange>
                <performancemode>1</performancemode>

            </NeoRec>
        """
        E = objectify.E

        amplifier = E.AMP_NeoRec(
            E.model(self.model),
            E.samplerate(self.sample_rate['value']),
            E.dynamicrange(self.dynamic_range["base"]),
            E.performancemode(self.performance_mode["base"]),
            instance=str(self._instance),
            module="amplifier"
        )

        return amplifier

    def setXML(self, xml):
        """
        Set module properties from XML configuration file,
        :param xml: complete objectify XML configuration tree,
        module will search for matching values
        """
        # search my configuration data
        amps = xml.xpath("//AMP_NeoRec[@module='amplifier' and @instance='%i']" % self._instance)
        if len(amps) == 0:
            return  # configuration data not found, leave everything unchanged

        cfg = amps[0]  # we should have only one amplifier instance from this type

        # check version, has to be lower or equal than current version
        # version = cfg.get("version")

        # get the values
        try:
            # reset filter properties to default values (because configuration has been moved to filter module)
            self._set_default_filter()

            # set number model
            self.model = cfg.model.pyval
            # If the model of the connected device and the model from the settings are different,
            # the settings will be reset

            # set closest matching sample rate
            sr = cfg.samplerate.pyval
            for rate in sorted(self.sample_rates, key=itemgetter('value')):
                if rate["value"] >= sr:
                    self.sample_rate = rate
                    break

            # set dynamic range
            self.dynamic_range = self.dynamic_ranges[cfg.dynamicrange.pyval]

            # set performance mode
            self.performance_mode = self.performance_modes[cfg.performancemode.pyval]

        except Exception as e:
            self.send_exception(e, severity=ErrorSeverity.NOTIFY)


"""
Amplifier module configuration GUI.
"""


class _DeviceConfigurationPane(QFrame, frmNeoRecConfiguration.Ui_frmNeoRecConfig):

    rateChanged = pyqtSignal(int)
    rangeChanged = pyqtSignal(int)
    modeChanged = pyqtSignal(int)

    # dataChanged = pyqtSignal()
    def __init__(self, amplifier, *args):
        super().__init__(*args)
        self.setupUi(self)

        # reference to our parent module
        self.amplifier = amplifier

        # Set tab name
        self.setWindowTitle("Amplifier")

        # set current index in combobox Sample Rate
        self.comboBoxSampleRate.setCurrentIndex(self.amplifier.sample_rate["base"])
        # set current index in combobox Dynamic Range
        self.comboBoxDynamicRange.setCurrentIndex(self.amplifier.dynamic_range["base"])
        # set current index in combobox Performance Mode
        self.comboBoxPerformanceMode.setCurrentIndex(self.amplifier.performance_mode["base"])

        self._updateAvailableChannels()

        # actions
        self.comboBoxSampleRate.currentIndexChanged.connect(self._samplerate_changed)
        self.comboBoxDynamicRange.currentIndexChanged.connect(self._dynamicrange_changed)
        self.comboBoxPerformanceMode.currentIndexChanged.connect(self._performancemode_changed)

    def _performancemode_changed(self, index):
        """ SIGNAL sample rate combobox value has changed """
        if index >= 0:
            # notify parent about changes
            self.modeChanged.emit(index)
            self._updateAvailableChannels()

    def _samplerate_changed(self, index):
        """ SIGNAL sample rate combobox value has changed """
        if index >= 0:
            # notify parent about changes
            self.rateChanged.emit(index)
            self._updateAvailableChannels()

    def _dynamicrange_changed(self, index):
        """ SIGNAL dynamic range combobox value has changed """
        if index >= 0:
            # notify parent about changes
            self.rangeChanged.emit(index)
            self._updateAvailableChannels()

    def _updateAvailableChannels(self):
        eeg = self.amplifier.amp.CountEeg
        amp = "NeoRec not connected"
        if self.amplifier.amp.connected:
            if self.amplifier.model in NR_Models:
                amp = NR_Models[self.amplifier.model]

        self.label.setText("Amplifier: %s\n\nAvailable channels: %d EEG" % (amp, eeg))


"""
Amplifier NeoRec module online GUI.
"""


class _OnlineCfgPane(QFrame, frmNeoRecOnline.Ui_frmNeoRecOnline):
    """
    NeoRec online configuration pane
    """

    modeChanged = pyqtSignal(int)

    def __init__(self, amp, *args):
        super().__init__(*args)
        self.setupUi(self)
        self.amp = amp

        # set default values
        self.pushButtonStop.setChecked(True)

        # actions
        self.pushButtonStartDefault.clicked.connect(self._button_toggle)
        self.pushButtonStartImpedance.clicked.connect(self._button_toggle)
        self.pushButtonStop.clicked.connect(self._button_toggle)

    def _button_toggle(self, checked):
        """ SIGNAL if one of the push buttons is clicked
        """
        if checked:
            mode = -1  # stop
            if self.pushButtonStartDefault.isChecked():
                mode = NR_MODE_DATA
            elif self.pushButtonStartImpedance.isChecked():
                mode = NR_MODE_IMPEDANCE
            self.modeChanged.emit(mode)

    def updateUI(self, mode):
        """ Update user interface according to recording mode
        """
        if mode == NR_MODE_DATA:
            self.pushButtonStartDefault.setChecked(True)
        elif mode == NR_MODE_IMPEDANCE:
            self.pushButtonStartImpedance.setChecked(True)
        else:
            self.pushButtonStop.setChecked(True)


if __name__ == "__main__":
    obj = AMP_NeoRec()
    print(obj.dynamic_ranges)
