from modbase import *
from amp_neorec.neorec import *
from scipy import signal


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

        # skip the first received data blocks
        self.skip_counter = 5
        self.blocking_counter = 0

        # reset hardware error counter and acquisition time out
        self.initialErrorCount = -1
        self.acquisitionTimeoutCounter = 0
        self.test_counter = 0

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
            channel.highpass = 0.0                  # high pass off
            channel.lowpass = 0.0                   # low pass off
            channel.notchfilter = False             # notch filter off



if __name__ == "__main__":
    obj = AMP_NeoRec()
    print(obj.dynamic_ranges)
