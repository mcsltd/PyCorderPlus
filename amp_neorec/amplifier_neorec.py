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

    def __init__(self, *args, **kwargs):
        super().__init__(name="Amplifier", **kwargs)

        # create hardware object
        self.amp = NeoRec()

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

        self.sample_rate = self.sample_rates[1]
        self.dynamic_range = self.dynamic_ranges[0]
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
            rate=self.sample_rate['base'],
            range=self.dynamic_range["base"],
            force=True
        )
        self.update_receivers()
        QApplication.restoreOverrideCursor()
        # create configuration pane
        config = _DeviceConfigurationPane(self)
        config.rateChanged.connect(self._samplerate_changed)
        config.rangeChanged.connect(self._dynamicrange_changed)
        return config

    def _dynamicrange_changed(self, index):
        """ SIGNAL from configuration pane if dynamic range has changed
        """
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        self.dynamic_range = self.dynamic_ranges[index]
        self.update_receivers()
        QApplication.restoreOverrideCursor()

    def _samplerate_changed(self, index):
        """ SIGNAL from configuration pane if sample rate has changed
        """
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        self.sample_rate = self.sample_rates[index]
        self.update_receivers()
        QApplication.restoreOverrideCursor()

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
        """ set all filter properties to HW filter values
        """
        for channel in self.channel_config:
            channel.highpass = 0.0  # high pass off
            channel.lowpass = 0.0  # low pass off
            channel.notchfilter = False  # notch filter off

    def setDefault(self):
        """
        Set all module parameters to default values
        """
        self.sample_rate = self.sample_rates[7]  # 500Hz sample rate
        for channel in self.channel_config:
            channel.isReference = False
            if channel.group == ChannelGroup.EEG:
                channel.enable = True  # enable all EEG channels
                if channel.input == 1:
                    channel.isReference = True  # use first channel as reference
            else:
                channel.enable = False  # disable all AUX channels
        self._set_default_filter()
        self.update_receivers()


    def _online_mode_changed(self, new_mode):
        """ SIGNAL from online configuration pane if recording mode has changed
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

    def process_start(self):
        """
        Open amplifier hardware and start data acquisition
        """

        # reset variables
        self.eeg_data.sample_counter = 0
        self.acquisitionTimeoutCounter = 0
        self.battery_timer = 0
        self.test_counter = 0

        # setup hardware
        self.amp.setup(mode=self.recording_mode, rate=self.sample_rate["base"], range=self.dynamic_range["base"])
        self.update_receivers()

        if len(self.channel_indices) == 0:
            raise

        # check battery

        # start hardware
        self.amp.start()

        # set start time on first call
        self.start_time = datetime.datetime.now()

        # update button state
        self.online_cfg.updateUI(self.recording_mode)

        # skip the first received data blocks
        self.skip_counter = 5
        self.blocking_counter = 0
        self.initialErrorCount = -1


"""
Amplifier module configuration GUI.
"""


class _DeviceConfigurationPane(QFrame, frmNeoRecConfiguration.Ui_frmNeoRecConfig):
    rateChanged = pyqtSignal(int)
    rangeChanged = pyqtSignal(int)
    def __init__(self, amplifier, *args):
        super().__init__(*args)
        self.setupUi(self)

        # reference to our parent module
        self.amplifier = amplifier

        # Set tab name
        self.setWindowTitle("Amplifier")

        # actions
        self.comboBoxSampleRate.currentIndexChanged.connect(self._samplerate_changed)
        self.comboBoxDynamicRange.currentIndexChanged.connect(self._dynamicrange_changed)

    def _samplerate_changed(self, index):
        """ SIGNAL sample rate combobox value has changed """
        print("sample rate changed", index)
        if index >= 0:
            # notify parent about changes
            self.rateChanged.emit(index)
            self._updateAvailableChannels()

    def _dynamicrange_changed(self, index):
        """ SIGNAL dynamic range combobox value has changed """
        print("dynamic range changed", index)
        if index >= 0:
            # notify parent about changes
            self.rangeChanged.emit(index)
            self._updateAvailableChannels()

    def _updateAvailableChannels(self):
        eeg = self.amplifier.amp.CountEeg
        amp = "NeoRec"
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
