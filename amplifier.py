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

        # ToDo: set default data block
        # if AMP_MONTAGE:
        #     self._create_channel_selection()
        # else:
        #     self._create_all_channel_selection()

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


if __name__ == "__main__":
    obj = AMP_ActiChamp()
    print(vars(obj))