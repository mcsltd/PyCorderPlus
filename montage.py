"""
Recording Montage Module

PyCorder ActiChamp Recorder

------------------------------------------------------------

Copyright (C) 2013, Brain Products GmbH, Gilching

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
@date: $Date: 2013-07-03 17:26:26 +0200 (Mi, 03 Jul 2013) $
@version: 1.0

B{Revision:} $LastChangedRevision: 216 $
"""
from collections import defaultdict

from modbase import *


class MNT_Recording(ModuleBase):
    """
    Recording Montage
    Configure and use a recording montage
    """

    def __init__(self, *args, **kwargs):
        # initialize the base class, give a descriptive name
        super().__init__(name="Recording Montage", **kwargs)

        # XML parameter version
        # 1: initial version
        self.xmlVersion = 1

        # initialize module variables
        self.data = None  # hold the data block we got from previous module
        self.dataavailable = False  # data available for output to next module
        self.current_input_params = None  # backup of last received properties

        self.montage_channel_properties = np.array([])
        self.montage = Montage()

        self.hideRefChannels = True  # always hide or show reference channels
        self.refChannelNames = "none"
        self.hasDuplicateLabels = False

        self.needs_conversion = True  # amplifier montage needs to be converted (compatibility mode)

    def setDefault(self):
        """
        Set all module parameters to default values
        """
        self.needs_conversion = True
        self.montage.reset()

    def getMontageList(self):
        return self.montage.get_configuration_table(self.current_input_params.channel_properties)


class Montage:
    """
    Montage dictionary
    """
    def __init__(self):
        # XML parameter version
        # 1: initial version
        self.xmlVersion = 1

        self.reset()

    def reset(self):
        """ Reset the channel dictionary
        """
        # dictionary with input group and input channel number as keys
        self.channel_dict = defaultdict(lambda: defaultdict(dict))

    def add(self, channel):
        """ add a channel to the dictionary
        @param channel: EEG_ChannelProperties object
        """
        ch = copy.copy(channel)
        # remove trailing and leading spaces from channel label
        ch.name = ch.name.strip()
        self.channel_dict[channel.inputgroup][channel.input][channel.group] = ch

    def has_channel(self, channel):
        """ check if the dictionary has an entry for this channel
        @param channel: EEG_ChannelProperties object
        @return: True if channel entry available
        """
        return channel.inputgroup in self.channel_dict and \
            (channel.input in self.channel_dict[channel.inputgroup]) and \
            (channel.group in self.channel_dict[channel.inputgroup][channel.input])

    def get_channel(self, channel):
        """ get channel from dictionary
        @param channel: EEG_ChannelProperties object
        @return: EEG_ChannelProperties object or None if channel is not available
        """
        if not self.has_channel(channel):
            return None
        ch = self.channel_dict[channel.inputgroup][channel.input][channel.group]
        # remove trailing and leading spaces from channel label
        ch.name = ch.name.strip()
        return ch

    def update_channel(self, channel):
        """ update the channel properties from montage settings
        @param channel: EEG_ChannelProperties object
        @return: True on success
        """
        mntchannel = self.get_channel(channel)
        if mntchannel is None:
            return False

        channel.name = mntchannel.name
        channel.enable = mntchannel.enable
        channel.isReference = mntchannel.isReference
        channel.color = mntchannel.color
        channel.unit = mntchannel.unit
        return True

    def get_configuration_table(self, properties):
        """ get the configuration table for the current input properties
        @param properties: current channel properties array
        @return: montage channel properties
        """
        mntproperties = []
        for ch in properties:
            mntchannel = self.get_channel(ch)
            if mntchannel is not None:
                mntproperties.append(mntchannel)
        return np.array(mntproperties)

    def setXML(self, xml):
        """ Set module properties from XML configuration file
        @param xml: complete objectify XML configuration tree,
        module will search for matching values
        """
        # self.reset()
        # for chXML in xml.MontageChannels.iterchildren():
        #     channel = EEG_ChannelProperties("")
        #     channel.setXML(chXML)
        #     self.add(channel)
        pass

    def getXML(self):
        """ Get module properties for XML configuration file.
        @return: objectify XML element
        """
        # E = objectify.E
        # channels = E.MontageChannels()
        # for inputgroup in self.channel_dict.values():
        #     for inputnr in inputgroup.values():
        #         for channel in inputnr.values():
        #             channels.append(channel.getXML())
        # channels.attrib["version"] = str(self.xmlVersion)
        # return channels
        pass