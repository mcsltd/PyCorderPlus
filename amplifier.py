# -*- coding: utf-8 -*-
'''
Acquisition Module

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
'''
from scipy import signal

from modbase import *
from actichamp_w import *

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


class AMP_ActiChamp(ModuleBase):
    ''' ActiChamp EEG amplifier module
    '''

    def __init__(self, *args, **keys):
        ''' Constructor
        '''
        super().__init__(self, name="Amplifier", **keys)

        # XML parameter version
        # 1: initial version
        # 2: input device container added
        # 3: PLL external input
        self.xmlVersion = 3

        # create hardware object
        self.amp = ActiChamp()  #: amplifier hardware object

        # set default channel configuration
        self.max_eeg_channels = 160  #: number of EEG channels for max. HW configuration
        self.max_aux_channels = 8  #: number of AUX channels for max. HW configuration
        self.channel_config = EEG_DataBlock.get_default_properties(self.max_eeg_channels, self.max_aux_channels)
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
        if AMP_MONTAGE:
            # ToDo: self._create_channel_selection()
            pass
        else:
            self._create_all_channel_selection()

        # ToDo: make the input device container
        # create the input device container
        # self.inputDevices = DeviceContainer()

        # date and time of acquisition start
        self.start_time = datetime.datetime.now()

        # ToDo: create online configuration pane
        # self.online_cfg = _OnlineCfgPane(self)

        # ToDo: rewrite this signal
        # self.connect(self.online_cfg, Qt.SIGNAL("modeChanged(int)"), self._online_mode_changed)

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

    # def _create_channel_selection(self):
    #     ''' Create index arrays of selected channels and prepare EEG_DataBlock
    #     '''
    #     # get all active eeg channel indices (including reference channel)
    #     mask = lambda x: (x.group == ChannelGroup.EEG) and (x.enable | x.isReference) and (
    #             x.input <= self.amp.properties.CountEeg)
    #     eeg_map = np.array(list(map(mask, self.channel_config)))
    #     self.eeg_indices = np.nonzero(eeg_map)[0]  # indices of all eeg channels
    #
    #     # get all active aux channel indices
    #     mask = lambda x: (x.group == ChannelGroup.AUX) and x.enable and (x.input <= self.amp.properties.CountAux)
    #     eeg_map = np.array(list(map(mask, self.channel_config)))
    #     self.aux_indices = np.nonzero(eeg_map)[0]  # indices of all aux channels
    #     self.property_indices = np.append(self.eeg_indices, self.aux_indices)
    #
    #     # adjust AUX indices to the actual available EEG channels
    #     self.aux_indices -= (self.max_eeg_channels - self.amp.properties.CountEeg)
    #     self.channel_indices = np.append(self.eeg_indices, self.aux_indices)
    #
    #     # create a new data block based on channel selection
    #     self.eeg_data = EEG_DataBlock(len(self.eeg_indices), len(self.aux_indices))
    #     self.eeg_data.channel_properties = copy.deepcopy(self.channel_config[self.property_indices])
    #     self.eeg_data.sample_rate = self.sample_rate['value']
    #
    #     # get the reference channel indices
    #     # mask = lambda x: (x.group == ChannelGroup.EEG) and x.isReference and (x.input <= self.amp.properties.CountEeg)
    #     # ToDo: check type map(...)
    #     eeg_ref = np.array(map(lambda x: x.isReference, self.eeg_data.channel_properties))
    #     self.ref_index = np.nonzero(eeg_ref)[0]  # indices of reference channel(s)
    #     if len(self.ref_index) and not AMP_MULTIPLE_REF:
    #         # use only the first reference channel
    #         self.ref_index = self.ref_index[0:1]
    #         idx = np.nonzero(map(lambda x: x not in self.ref_index,
    #                              range(0, len(self.eeg_indices))
    #                              )
    #                          )[0]
    #         for prop in self.eeg_data.channel_properties[idx]:
    #             prop.isReference = False
    #
    #     # append "REF" to the reference channel name and create the combined reference channel name
    #     refnames = []
    #     for prop in self.eeg_data.channel_properties[self.ref_index]:
    #         refnames.append(str(prop.name))
    #         prop.name = "REF_" + prop.name
    #         prop.refname = "REF"
    #         # global hide for all reference channels?
    #         if AMP_HIDE_REF:
    #             prop.enable = False
    #     if len(refnames) > 1:
    #         self.eeg_data.ref_channel_name = "AVG(" + "+".join(refnames) + ")"
    #     else:
    #         self.eeg_data.ref_channel_name = "".join(refnames)
    #
    #     # remove reference channel if not in impedance mode
    #     self.ref_remove_index = self.ref_index
    #     if (self.recording_mode != CHAMP_MODE_IMPEDANCE) and len(self.ref_index):
    #         # set reference channel names for all other electrodes
    #         idx = np.nonzero(map(lambda x: x not in self.ref_index,
    #                              range(0, len(self.eeg_indices))
    #                              )
    #                          )[0]
    #         for prop in self.eeg_data.channel_properties[idx]:
    #             prop.refname = "REF"
    #
    #         '''
    #         # remove single reference channel
    #         if AMP_HIDE_REF or not self.eeg_data.channel_properties[self.ref_index[0]].enable:
    #             self.eeg_data.channel_properties = np.delete(self.eeg_data.channel_properties, self.ref_index, 0)
    #             self.eeg_data.eeg_channels = np.delete(self.eeg_data.eeg_channels, self.ref_index, 0)
    #         '''
    #         # remove all disabled reference channels
    #         ref_dis = np.array(map(lambda x: x.isReference and not x.enable,
    #                                self.eeg_data.channel_properties))
    #         self.ref_remove_index = np.nonzero(ref_dis)[0]  # indices of disabled reference channels
    #         self.eeg_data.channel_properties = np.delete(self.eeg_data.channel_properties, self.ref_remove_index, 0)
    #         self.eeg_data.eeg_channels = np.delete(self.eeg_data.eeg_channels, self.ref_remove_index, 0)
    #
    #     # prepare recording mode and anti aliasing filters
    #     # self._prepare_mode_and_filters()

    def _create_all_channel_selection(self):
        ''' Create index arrays of all available channels and prepare EEG_DataBlock
        '''
        # get all eeg channel indices
        mask = lambda x: (x.group == ChannelGroup.EEG) and (x.input <= self.amp.properties.CountEeg)
        eeg_map = np.array(list(map(mask, self.channel_config)))
        self.eeg_indices = np.nonzero(eeg_map)[0]  # indices of all eeg channels

        # get all aux channel indices
        mask = lambda x: (x.group == ChannelGroup.AUX) and (x.input <= self.amp.properties.CountAux)
        eeg_map = np.array(list(map(mask, self.channel_config)))
        self.aux_indices = np.nonzero(eeg_map)[0]  # indices of all aux channels
        self.property_indices = np.append(self.eeg_indices, self.aux_indices)

        # adjust AUX indices to the actual available EEG channels
        self.aux_indices -= (self.max_eeg_channels - self.amp.properties.CountEeg)
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
        ''' Set all module parameters to default values
        '''
        emulation_mode = self.amp.getEmulationMode() > 0
        self.sample_rate = self.sample_rates[7]     # 500Hz sample rate
        for channel in self.channel_config:
            channel.isReference = False
            if channel.group == ChannelGroup.EEG:
                channel.enable = True               # enable all EEG channels
                if (channel.input == 1) and not emulation_mode:
                    channel.isReference = True      # use first channel as reference
            else:
                channel.enable = False              # disable all AUX channels
        self._set_default_filter()
        # ToDo: self.inputDevices.reset()
        self.update_receivers()

    def _set_default_filter(self):
        ''' set all filter properties to HW filter values
        '''
        for channel in self.channel_config:
            channel.highpass = 0.0                  # high pass off
            channel.lowpass = 0.0                   # low pass off
            channel.notchfilter = False             # notch filter off

    def process_start(self):
        ''' Open amplifier hardware and start data acquisition
        '''
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
            info = "Start %s at %.0fHz with %d channels" % (CHAMP_Modes[self.recording_mode], self.eeg_data.sample_rate,
                                                            len(self.channel_indices))
        else:
            if self.amp.hasPllOption() and self.amp.PllExternal:
                info = "Start %s at %.0fHz (ext. PLL)" % (CHAMP_Modes[self.recording_mode],
                                                          self.eeg_data.sample_rate)
            else:
                info = "Start %s at %.0fHz" % (CHAMP_Modes[self.recording_mode],
                                               self.eeg_data.sample_rate)

        # ToDo: self.send_event(ModuleEvent(self._object_name, EventType.LOGMESSAGE, info))
        # ToDo: send recording mode
        # self.send_event(ModuleEvent(self._object_name,
        #                             EventType.STATUS,
        #                             info=self.recording_mode,
        #                             status_field="Mode"))
        # ToDo: update button state
        # self.online_cfg.updateUI(self.recording_mode)

        # skip the first received data blocks
        self.skip_counter = 5
        self.blocking_counter = 0
        self.initialErrorCount = -1




if __name__ == "__main__":
    obj = AMP_ActiChamp()
    # print(vars(obj))
