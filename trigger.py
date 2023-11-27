# -*- coding: utf-8 -*-
"""
Trigger Detection Module

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
@date: $Date: 2011-04-11 11:51:56 +0200 (Mo, 11 Apr 2011) $
@version: 1.0

B{Revision:} $LastChangedRevision: 69 $
"""

from modbase import *


class TRG_Eeg(ModuleBase):
    """
    Input and output trigger detection
    """

    def __init__(self, *args, **kwargs):
        super().__init__(name="EEG Trigger", **kwargs)

        self.data = None
        self.dataavailable = False

        # Trigger events

        self.lastevent = [[] for i in range(3)]  #: last values of trigger data block
        self.debouncing_delay = 2  #: debouncing value (number of samples)

        # Button events
        self.lastbutton = 0, 0, False  #: last button state (value, count, state)
        self.debouncing_button = 20  #: button debouncing value (number of samples)

    def process_start(self):
        """
        Prepare the module for startup
        """
        self.lastevent = [[] for i in range(3)]  # reset last values of trigger data block
        self.lastbutton = 0, 0, False  # reset button state

    def process_input(self, datablock):
        """ Search for trigger values and create trigger marker
        """
        self.dataavailable = True
        self.data = datablock

        # don't search trigger in impedance mode
        if self.data.recording_mode == RecordingMode.IMPEDANCE:
            return

        # search for trigger input events (Bit 0-3)
        self.searchTrigger(0)
        # search for trigger input events (Bit 4-7)
        self.searchTrigger(1)
        # search for trigger output events
        self.searchTrigger(2)
        # search for button events
        self.searchButton()

    def searchTrigger(self, in_out):
        """ Search for trigger values
        @param in_out: 0=search trigger input, 1=search trigger output
        """
        # search for trigger events
        if in_out == 0:
            trigger = np.bitwise_and(self.data.trigger_channel[0], 0x000F)  # mask trigger input channels 0-3
        elif in_out == 1:
            trigger = np.bitwise_and(self.data.trigger_channel[0], 0x00F0)  # mask trigger input channels 4-7
        else:
            trigger = np.bitwise_and(self.data.trigger_channel[0], 0xFF00)  # mask trigger output channels
        lastevent = self.lastevent[in_out]

        diff = np.diff(np.r_[-1, trigger])  # get changes
        idx = np.nonzero(diff)[0]  # indices of changes
        count = np.diff(np.r_[idx, len(trigger)])  # number of trigger values for each change
        values = trigger[idx]  # trigger values
        nzidx = np.nonzero(values)[0]  # indices for non zero trigger values

        # create event list
        events = []
        for nz in nzidx:
            # is there an outstanding event from the last data package
            if nz == 0 and len(lastevent) and values[nz] == lastevent[1]:
                count[nz] += lastevent[2]  # add number of values from last event
                sc = lastevent[3]  # get sample counter from last event
                sent = lastevent[4]  # get sent flag
            else:
                sc = self.data.sample_channel[0][idx[nz]]  # take sample counter
                sent = False  # reset sent flag
            debounced = count[nz] >= self.debouncing_delay
            if not sent and debounced:
                # add trigger events to marker array
                if in_out == 0:
                    descr = "S%3i" % (values[nz])
                    mtype = "Stimulus"
                elif in_out == 1:
                    descr = "R%3i" % (values[nz] >> 4)
                    mtype = "Response"
                else:
                    descr = "TO%3i" % (values[nz] >> 8)
                    mtype = "Comment"
                self.data.markers.append(EEG_Marker(type=mtype,
                                                    description=descr,
                                                    position=sc,
                                                    channel=0))
                sent = True
            t = [idx[nz], values[nz], count[nz], sc, sent]
            events.append(t)

        # if last event ends at array boundary, keep it
        if len(idx[nzidx]) and (idx[nzidx][-1] + count[nzidx][-1] >= len(trigger)):
            self.lastevent[in_out] = events[-1]
        else:
            self.lastevent[in_out] = []

    def searchButton(self):
        """
        Search for button events
        """
        # mask button input bit
        button = np.bitwise_and(self.data.trigger_channel[0], 0x80000000)
        # search changes
        diff = np.diff(np.r_[-1, button])  # get changes
        idx = np.nonzero(diff)[0]  # indices of changes
        count = np.diff(np.r_[idx, len(button)])  # number of values for each change
        if self.lastbutton[0] == button[0]:  # add count from last data block
            count[0] += self.lastbutton[1]
            lastcount = self.lastbutton[1]
        else:
            lastcount = 0
        state = button[idx] > 0  # button states
        nzidx = np.nonzero(count > self.debouncing_button)[0]  # indices of valid button states

        # send change message
        button_state = self.lastbutton[2]  # get last button state
        for nz in nzidx:
            if state[nz] != button_state:
                button_state = state[nz]
                # self.send_event(ModuleEvent(self._object_name,
                #                             EventType.COMMAND,
                #                             info="MyButton",
                #                             cmd_value="pressed" if button_state else "released"
                #                             ))
                # insert button marker
                sc = self.data.sample_channel[0][idx[nz]]  # take sample counter
                if idx[nz] == 0:
                    sc -= lastcount
                descr = "BtnPressed" if button_state else "BtnReleased"
                mtype = "Comment"
                self.data.markers.append(EEG_Marker(type=mtype,
                                                    description=descr,
                                                    position=sc,
                                                    channel=0))

        # keep the current state
        self.lastbutton = button[-1], count[-1], button_state

    def process_output(self):
        if not self.dataavailable:
            return None
        self.dataavailable = False
        return self.data
