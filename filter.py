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
        ''' Set all module parameters to default values
        '''
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
