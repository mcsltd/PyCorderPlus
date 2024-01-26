"""
Digital Filter Module

PyCorderPlus ActiChamp Recorder

------------------------------------------------------------

Copyright (C) 2010, Brain Products GmbH, Gilching
Copyright (C) 2024, Medical Computer Systems Ltd


This file is part of PyCorderPlus
"""

from scipy import signal
from modbase import *
from operator import itemgetter

from PyQt6.QtWidgets import QFrame, QStyledItemDelegate, QHeaderView, QAbstractItemView, QComboBox
from PyQt6.QtCore import QAbstractTableModel, pyqtSignal
from PyQt6.QtGui import QColor
from res import frmFilterConfig


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
        E = objectify.E
        channels = E.channels()
        for channel in self.params.channel_properties:
            if channel.group != ChannelGroup.EEG:
                channels.append(channel.getXML())
        cfg = E.EegFilter(E.notch_frequency(self.notchFrequency),
                          E.lp_global(self.lpGlobal),
                          E.hp_global(self.hpGlobal),
                          E.notch_global(self.notchGlobal),
                          channels,
                          version=str(self.xmlVersion),
                          instance=str(self._instance),
                          module="filter")
        return cfg

    def setXML(self, xml):
        """
        Set module properties from XML configuration file
        @param xml: complete objectify XML configuration tree,
        module will search for matching values
        """
        # search my configuration data
        storages = xml.xpath("//EegFilter[@module='filter' and @instance='%i']" % self._instance)
        if len(storages) == 0:
            # configuration data not found, set default values
            self.notchFrequency = 50.0
            return

            # we should have only one instance from this type
        cfg = storages[0]

        # check version, has to be lower or equal than current version
        version = cfg.get("version")
        if (version is None) or (int(version) > self.xmlVersion):
            self.send_event(ModuleEvent(self._object_name, EventType.ERROR, "XML Configuration: wrong version"))
            return
        version = int(version)

        # get the values
        try:
            self.notchFrequency = cfg.notch_frequency.pyval
            if version > 1:
                # get global filter values
                self.notchGlobal = cfg.notch_global.pyval
                self.lpGlobal = cfg.lp_global.pyval
                self.hpGlobal = cfg.hp_global.pyval
                # get single channel filter values
                channel_properties = []
                for idx, channel in enumerate(cfg.channels.iterchildren()):
                    ch = EEG_ChannelProperties("")
                    ch.setXML(channel)
                    channel_properties.append(ch)
                self.params.channel_properties = np.array(channel_properties)

        except Exception as e:
            self.send_exception(e, severity=ErrorSeverity.NOTIFY)


"""
Filter module configuration pane.
"""


class _ConfigurationPane(frmFilterConfig.Ui_frmFilterConfig, QFrame):
    """
    Module configuration pane
    """
    dataChanged = pyqtSignal()

    def __init__(self, filter, *args):
        super().__init__()

        self.setupUi(self)
        self.tableView.horizontalHeader().ResizeMode(QHeaderView.ResizeMode.ResizeToContents)

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
        self.comboBox_Notch.currentTextChanged.connect(self._notchFrequencyChanged)
        self.checkBoxEegNotch.stateChanged.connect(self._notchFilterChanged)
        self.comboBoxEegHighpass.currentTextChanged.connect(self._highpassChanged)
        self.comboBoxEegLowpass.currentTextChanged.connect(self._lowpassChanged)

    def _get_cb_index(self, cb, value):
        ''' Get closest matching combobox index
        @param cb: combobox object
        @param value: float lookup value
        '''
        itemlist = []
        for i in range(cb.count()):
            try:
                val = float(cb.itemText(i))
            except:
                val = 0.0
            itemlist.append((i, val))
        idx = itemlist[-1][0]
        for item in sorted(itemlist, key=itemgetter(1)):
            if item[1] >= value - 0.0001:
                idx = item[0]
                break
        return idx

    def _notchFrequencyChanged(self, value):
        try:
            self.filter.notchFrequency = float(value)
        except:
            self.filter.notchFrequency = 0.0

    def _notchFilterChanged(self, value):
        self.filter.notchGlobal = (value == Qt.CheckState.Checked.value)

    def _lowpassChanged(self, value):
        try:
            self.filter.lpGlobal = float(value)
        except:
            self.filter.lpGlobal = 0.0

    def _highpassChanged(self, value):
        try:
            self.filter.hpGlobal = float(value)
        except:
            self.filter.hpGlobal = 0.0

    def _fillChannelTables(self):
        """ Create and fill channel tables
        """
        # AUX channel table
        mask = lambda x: x.group != ChannelGroup.EEG
        ch_map = np.array(list(map(mask, self.filter.params.channel_properties)))
        ch_indices = np.nonzero(ch_map)[0]
        self.table_model = _ConfigTableModel(self.filter.params.channel_properties[ch_indices])
        self.tableView.setModel(self.table_model)
        self.tableView.setItemDelegate(_ConfigItemDelegate())
        self.tableView.setEditTriggers(QAbstractItemView.EditTrigger.AllEditTriggers)

        # actions
        self.table_model.dataChanged.connect(self._channeltable_changed)

    def _channeltable_changed(self, topLeft, bottomRight):
        """ SIGNAL data in channel table has changed
        """
        # notify parent about changes
        self.dataChanged.emit()

    def showEvent(self, event):
        self._fillChannelTables()


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

    def _getitem(self, row, column):
        """ Get amplifier property item based on table row and column
        @param row: row number
        @param column: column number
        @return:  QVariant property value
        """
        if (row >= len(self.arraydata)) or (column >= len(self.columns)):
            return None

        # get channel properties
        property = self.arraydata[row]
        # get property name from column description
        property_name = self.columns[column]['property']
        # get property value
        if property_name == 'input':
            d = property.input
        elif property_name == 'enable':
            d = property.enable
        elif property_name == 'name':
            d = property.name
        elif property_name == 'lowpass':
            if property.lowpass == 0.0:
                d = 'off'
            else:
                d = property.lowpass
        elif property_name == 'highpass':
            if property.highpass == 0.0:
                d = 'off'
            else:
                d = property.highpass
        elif property_name == 'notchfilter':
            d = property.notchfilter
        elif property_name == 'isReference':
            d = property.isReference
        else:
            d = None
        return d

    def _setitem(self, row, column, value):
        """ Set amplifier property item based on table row and column
        @param row: row number
        @param column: column number
        @param value: QVariant value object
        @return: True if property value was set, False if not
        """
        if (row >= len(self.arraydata)) or (column >= len(self.columns)):
            return False
        # get channel properties
        property = self.arraydata[row]
        # get property name from column description
        property_name = self.columns[column]['property']
        # set channel property
        if property_name == 'enable':
            property.enable = bool(value)
            return True
        elif property_name == 'name':
            property.name = str(value)
            return True
        elif property_name == 'lowpass':

            try:
                property.lowpass = float(value)
            except:
                property.lowpass = 0.0

            if property.group == ChannelGroup.EEG:
                for prop in self.arraydata:
                    prop.lowpass = property.lowpass
            return True
        elif property_name == 'highpass':
            try:
                property.highpass = float(value)
            except:
                property.highpass = 0.0

            if property.group == ChannelGroup.EEG:
                for prop in self.arraydata:
                    prop.highpass = property.highpass
            return True
        elif property_name == 'notchfilter':
            property.notchfilter = bool(value)
            if property.group == ChannelGroup.EEG:
                for prop in self.arraydata:
                    prop.notchfilter = property.notchfilter
                self.revert()
                # self.reset()
            return True
        elif property_name == 'isReference':
            # available for EEG channels only
            if property.group == ChannelGroup.EEG:
                # remove previously selected reference channel
                if bool(value):
                    for prop in self.arraydata:
                        prop.isReference = False
                property.isReference = bool(value)
                self.revert()
                # self.reset()
            return True
        return False

    def editorType(self, column):
        """ Get the columns editer type from column description
        @param column: table column number
        @return: editor type as QVariant (string)
        """
        if column >= len(self.columns):
            return None
        return self.columns[column]['editor']

    def comboBoxList(self, column):
        """ Get combo box item list for column 'highpass' or 'lowpass'
        @param column: table column number
        @return: combo box item list as QVariant
        """
        if column >= len(self.columns):
            return
        if self.columns[column]['property'] == 'lowpass':
            return self.lowpasslist
        elif self.columns[column]['property'] == 'highpass':
            return self.highpasslist
        else:
            return None

    def rowCount(self, parent):
        """ Get the number of required table rows
        @return: number of rows
        """
        if parent.isValid():
            return 0
        return len(self.arraydata)

    def columnCount(self, parent):
        """ Get the number of required table columns
        @return: number of columns
        """
        if parent.isValid():
            return 0
        return len(self.columns)

    def data(self, index, role):
        """ Abstract method from QAbstactItemModel to get cell data based on role
        @param index: QModelIndex table cell reference
        @param role: given role for the item referred to by the index
        @return: the data stored under the given role for the item referred to by the index
        """
        if not index.isValid():
            return None

        # get the underlying data
        value = self._getitem(index.row(), index.column())

        if role == Qt.ItemDataRole.CheckStateRole and self.columns[index.column()]['header'] == "Notch":

            if value:
                return Qt.CheckState.Checked
            else:
                return Qt.CheckState.Unchecked

        elif (role == Qt.ItemDataRole.DisplayRole) or (role == Qt.ItemDataRole.EditRole):

            if type(value) is not bool:
                return value

        elif role == Qt.ItemDataRole.BackgroundRole:
            # change background color for reference channel
            property = self.arraydata[index.row()]
            # if (property.isReference) and (index.column() == 0):
            if property.isReference:
                return QColor(0, 0, 255)

        return None

    def flags(self, index):
        """ Abstract method from QAbstactItemModel
        @param index: QModelIndex table cell reference
        @return: the item flags for the given index
        """
        if not index.isValid():
            return Qt.ItemFlag.ItemIsEnabled
        if not self.columns[index.column()]['edit']:
            return Qt.ItemFlag.ItemIsEnabled
        value = self._getitem(index.row(), index.column())
        if type(value) is bool:
            return QAbstractTableModel.flags(self, index) | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsSelectable
        return QAbstractTableModel.flags(self, index) | Qt.ItemFlag.ItemIsEditable

    def setData(self, index, value, role):
        """ Abstract method from QAbstactItemModel to set cell data based on role
        @param index: QModelIndex table cell reference
        @param value: QVariant new cell data
        @param role: given role for the item referred to by the index
        @return: true if successful; otherwise returns false.
        """
        if index.isValid():
            if role == Qt.ItemDataRole.EditRole.value:
                if not self._setitem(index.row(), index.column(), value):
                    return False
                self.dataChanged.emit(index, index)
                return True
            elif role == Qt.ItemDataRole.CheckStateRole.value:
                if not self._setitem(index.row(), index.column(), value == Qt.CheckState.Checked.value):
                    return False
                self.dataChanged.emit(index, index)
                return True
        return False

    def headerData(self, col, orientation, role):
        """ Abstract method from QAbstactItemModel to get the column header
        @param col: column number
        @param orientation: Qt.Horizontal = column header, Qt.Vertical = row header
        @param role: given role for the item referred to by the index
        @return: header
        """
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole.value:
            return self.columns[col]['header']
        return None


class _ConfigItemDelegate(QStyledItemDelegate):
    """
    Combobox item editor.
    """

    def __init__(self, parent=None):
        super(_ConfigItemDelegate, self).__init__(parent)

    def createEditor(self, parent, option, index):
        if index.model().editorType(index.column()) == 'combobox':
            combobox = QComboBox(parent)
            combobox.addItems(index.model().comboBoxList(index.column()))
            combobox.setEditable(False)
            # self.connect(combobox, Qt.SIGNAL('activated(int)'), self.emitCommitData)
            combobox.activated.connect(self.emitCommitData)
            return combobox
        return QStyledItemDelegate.createEditor(self, parent, option, index)

    def setEditorData(self, editor, index):
        if index.model().columns[index.column()]['editor'] == 'combobox':
            text = index.model().data(index, Qt.ItemDataRole.DisplayRole)   # can return different types

            # handler for different types of text variable
            if type(text) is not str:
                text = str(text).replace(".0", "") if str(text).endswith(".0") else str(text)

            i = editor.findText(text)
            if i == -1:
                i = 0
            editor.setCurrentIndex(i)

        QStyledItemDelegate.setEditorData(self, editor, index)

    def setModelData(self, editor, model, index):
        if model.columns[index.column()]['editor'] == 'combobox':
            model.setData(index, editor.currentText(), Qt.ItemDataRole.EditRole)
            model.revert()
        QStyledItemDelegate.setModelData(self, editor, model, index)

    def emitCommitData(self):
        self.commitData.emit(self.sender())

