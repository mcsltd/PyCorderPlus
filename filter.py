from scipy import signal
from modbase import *
from res import frmFilterConfig

from PyQt6.QtWidgets import QFrame, QStyledItemDelegate, QHeaderView
from PyQt6.QtCore import QAbstractTableModel


class FLT_Eeg(ModuleBase):
    """
    Low, high pass and notch filter
    """

    def __init__(self, *args, **kwargs):
        super().__init__(name="EEG Filter", **kwargs)

        # XML parameter version
        # 1: initial version
        # 2: include lp, hp and notch
        self.xmlVersion = 2

        self.data = None
        self.dataavailable = False
        self.params = None

        self.notchFilter = []  # notch filter array
        self.lpFilter = []  # lowpass filter array
        self.hpFilter = []  # highpass filter array

        # set default process values
        self.samplefreq = 50000.0
        self.filterorder = 2
        self.notchFrequency = 50.0  # notch filter frequency in Hz

        # set default properties
        self.setDefault()

    def setDefault(self):
        """ Set all module parameters to default values
        """
        # global filter values (for EEG-channels)
        self.lpGlobal = 0.0
        self.hpGlobal = 0.0
        self.notchGlobal = False

        # single channel values
        if self.params is not None:
            for ch in self.params.channel_properties:
                ch.lowpass = 0.0
                ch.highpass = 0.0
                ch.notchfilter = False

    def get_configuration_pane(self):
        """ Get the configuration pane if available.
        Qt widgets are not reusable, so we have to create it new every time
        """
        return _ConfigurationPane(self)

    def _design_filter(self, frequency, type, slice):
        """ Create filter settings for channel groups with equal filter parameters
        @param frequency: filter frequeny in Hz
        @param type: filter type, "low", "high" or "bandstop"
        @param slice: channel group indices
        @return: filter parameters and state vector
        """
        if (frequency == 0.0) or (frequency > self.samplefreq / 2.0):
            return None
        if type == "bandstop":
            cut1 = (frequency - 1.0) / self.samplefreq * 2.0
            cut2 = (frequency + 1.0) / self.samplefreq * 2.0
            b, a = signal.filter_design.iirfilter(2, [cut1, cut2], btype=type, ftype='butter')
            # b,a = signal.filter_design.iirfilter(2, [cut1, cut2], rs=40.0, rp=0.5, btype=type, ftype='elliptic')
        else:
            cut = frequency / self.samplefreq * 2.0
            b, a = signal.filter_design.butter(self.filterorder, cut, btype=type)
        zi = signal.lfiltic(b, a, (0.0,))
        czi = np.resize(zi, (slice.stop - slice.start, len(zi)))
        return {'slice': slice, 'a': a, 'b': b, 'zi': czi, 'frequency': frequency}

    def process_update(self, params):
        """ Calculate filter parameters for updated channels
        """
        # update the local reference
        if self.params is None:
            self.params = params
        else:
            # merge filter settings
            for ch in params.channel_properties:
                if ch.group == ChannelGroup.EEG:
                    ch.lowpass = self.lpGlobal
                    ch.highpass = self.hpGlobal
                    ch.notchfilter = self.notchGlobal
                else:
                    # get local channel property by input number
                    filterChannel = None
                    for filter in self.params.channel_properties:
                        if filter.input == ch.input and filter.inputgroup == ch.inputgroup:
                            filterChannel = filter
                            break
                    if filterChannel is not None:
                        ch.lowpass = filterChannel.lowpass
                        ch.highpass = filterChannel.highpass
                        ch.notchfilter = filterChannel.notchfilter
            self.params = params

        # reset filter
        self.samplefreq = params.sample_rate
        self.lpFilter = []
        self.hpFilter = []
        self.notchFilter = []

        # nothing to filter
        if len(params.channel_properties) == 0:
            return params

        # create channel slices and filter for continuous notch filters
        notch = params.channel_properties[0].notchfilter
        slc = slice(0, 1, 1)
        for property in params.channel_properties[1::]:
            if property.notchfilter == notch:
                slc = slice(slc.start, slc.stop + 1, 1)
            else:
                # design filter
                if notch:
                    freq = self.notchFrequency
                else:
                    freq = 0.0
                filter = self._design_filter(freq, 'bandstop', slc)
                if filter is not None:
                    self.notchFilter.append(filter)
                slc = slice(slc.stop, slc.stop + 1, 1)
                notch = property.notchfilter
        if notch:
            freq = self.notchFrequency
        else:
            freq = 0.0
        filter = self._design_filter(freq, 'bandstop', slc)
        if filter is not None:
            self.notchFilter.append(filter)

        # create channel slices and filter for continuous unique lowpass filter frequencies
        freq = params.channel_properties[0].lowpass
        slc = slice(0, 1, 1)
        for property in params.channel_properties[1::]:
            if property.lowpass == freq:
                slc = slice(slc.start, slc.stop + 1, 1)
            else:
                # design filter
                filter = self._design_filter(freq, 'low', slc)
                if filter is not None:
                    self.lpFilter.append(filter)
                slc = slice(slc.stop, slc.stop + 1, 1)
                freq = property.lowpass
        filter = self._design_filter(freq, 'low', slc)
        if filter is not None:
            self.lpFilter.append(filter)

        # create channel slices and filter for continuous unique highpass filter frequencies
        freq = params.channel_properties[0].highpass
        slc = slice(0, 1, 1)
        for property in params.channel_properties[1::]:
            if property.highpass == freq:
                slc = slice(slc.start, slc.stop + 1, 1)
            else:
                # design filter
                filter = self._design_filter(freq, 'high', slc)
                if filter is not None:
                    self.hpFilter.append(filter)
                slc = slice(slc.stop, slc.stop + 1, 1)
                freq = property.highpass
        filter = self._design_filter(freq, 'high', slc)
        if filter is not None:
            self.hpFilter.append(filter)

        # propagate down
        return params

    def process_input(self, datablock):
        """
        Filter all channel groups
        """
        self.dataavailable = True
        self.data = datablock

        # don't filter impedance values
        if self.data.recording_mode == RecordingMode.IMPEDANCE:
            return

        # replace channel filter configuration within the data block with our modified configuration
        for channel in range(len(self.data.channel_properties)):
            self.data.channel_properties[channel].lowpass = self.params.channel_properties[channel].lowpass
            self.data.channel_properties[channel].highpass = self.params.channel_properties[channel].highpass
            self.data.channel_properties[channel].notchfilter = self.params.channel_properties[channel].notchfilter

        # highpass filter
        for flt in self.hpFilter:
            self.data.eeg_channels[flt['slice']], flt['zi'] = \
                signal.lfilter(flt['b'], flt['a'],
                               self.data.eeg_channels[flt['slice']], zi=flt['zi'])

        # lowpass filter
        for flt in self.lpFilter:
            self.data.eeg_channels[flt['slice']], flt['zi'] = \
                signal.lfilter(flt['b'], flt['a'],
                               self.data.eeg_channels[flt['slice']], zi=flt['zi'])

        # notch filter
        for flt in self.notchFilter:
            self.data.eeg_channels[flt['slice']], flt['zi'] = \
                signal.lfilter(flt['b'], flt['a'],
                               self.data.eeg_channels[flt['slice']], zi=flt['zi'])

    def process_output(self):
        if not self.dataavailable:
            return None
        self.dataavailable = False
        return self.data

    def getXML(self):
        """ Get module properties for XML configuration file
        @return: objectify XML element::
            e.g.
            <EegFilter instance="0" version="1">
                <notch_frequency>50.0</path>
                ...
            </EegFilter>
        """
        pass

    def setXML(self, xml):
        """
        Set module properties from XML configuration file
        @param xml: complete objectify XML configuration tree,
        module will search for matching values
        """
        pass

"""
Filter module configuration pane.
"""


class _ConfigurationPane(QFrame, frmFilterConfig.Ui_frmFilterConfig):
    """
    Module configuration pane
    """

    def __init__(self, filter, *args):
        super().__init__(filter, *args)

        self.setupUi(self)
        self.tableView.horizontalHeader().setResizeMode(QHeaderView.ResizeMode.ResizeToContents)

        # setup content
        self.filter = filter
        # notch frequency
        idx = self._get_cb_index(self.comboBox_Notch, self.filter.notchFrequency)
        if idx >= 0:
            self.comboBox_Notch.setCurrentIndex(idx)

        # channel tables
        self._fillChannelTables()

        # Global lowpass filter
        self.comboBoxEegLowpass.addItems(self.table_model.lowpasslist)
        idx = self._get_cb_index(self.comboBoxEegLowpass, self.filter.lpGlobal)
        if idx >= 0:
            self.comboBoxEegLowpass.setCurrentIndex(idx)

        # Global highpass filter
        self.comboBoxEegHighpass.addItems(self.table_model.highpasslist)
        idx = self._get_cb_index(self.comboBoxEegHighpass, self.filter.hpGlobal)
        if idx >= 0:
            self.comboBoxEegHighpass.setCurrentIndex(idx)

        # global notch filter
        self.checkBoxEegNotch.setChecked(self.filter.notchGlobal)

        # actions
        self.comboBox_Notch.currentIndexChanged.connect(self._notchFrequencyChanged)
        self.checkBoxEegNotch.stateChanged.connect(self._notchFilterChanged)
        self.comboBoxEegHighpass.currentIndexChanged.connect(self._highpassChanged)
        self.comboBoxEegLowpass.currentIndexChanged.connect(self._lowpassChanged)


class _ConfigTableModel(QAbstractTableModel):
    def __init__(self, data, parent=None, *args):
        """
        Constructor
        @param data: array of EEG_ChannelProperties objects
        """
        super().__init__(parent)
        self.arraydata = data
        # column description
        self.columns = [{'property': 'input', 'header': 'Channel', 'edit': False, 'editor': 'default'},
                        {'property': 'lowpass', 'header': 'High Cutoff', 'edit': True, 'editor': 'combobox'},
                        {'property': 'highpass', 'header': 'Low Cutoff', 'edit': True, 'editor': 'combobox'},
                        {'property': 'notchfilter', 'header': 'Notch', 'edit': True, 'editor': 'default'},
                        {'property': 'name', 'header': 'Name', 'edit': False, 'editor': 'default'},
                        ]

        # combo box list contents
        self.lowpasslist = ['off', '10', '20', '30', '50', '100', '200', '500', '1000', '2000']
        self.highpasslist = ['off', '0.01', '0.02', '0.05', '0.1', '0.2', '0.5', '1', '2', '5', '10']


class _ConfigItemDelegate(QStyledItemDelegate):
    """
    Combobox item editor.
    """

    def __init__(self, parent=None):
        super(_ConfigItemDelegate, self).__init__(parent)
