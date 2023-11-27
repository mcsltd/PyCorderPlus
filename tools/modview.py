import types

from PyQt6.QtWidgets import QTableWidget, QStyledItemDelegate, QAbstractItemView, QHeaderView
from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PyQt6.QtGui import QColor


class GenericTableWidget(QTableWidget):
    """
    Generic model/view table widget
    """

    def __init__(self, *args, **kwargs):
        ''' Constructor
        '''
        super().__init__(*args)

        self.setAlternatingRowColors(True)
        # self.setObjectName("tableViewGeneric")
        # self.horizontalHeader().setCascadingSectionResizes(False)
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().ResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        if "RowNumbers" in kwargs:
            self.verticalHeader().setVisible(kwargs["RowNumbers"])
        else:
            self.verticalHeader().setVisible(False)
        self.verticalHeader().ResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        if "SelectionBehavior" in kwargs:
            self.setSelectionBehavior(kwargs["SelectionBehavior"])
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)

        # table description and content
        self.fnColorSelect = lambda x: None
        self.fnCheckBox = lambda x: None
        self.fnValidate = lambda row, col, data: True
        self.descrition = []
        self.cblist = {}
        self.data = []

        # selection info
        self.selectedRow = 0

    def _fillTables(self):
        """ Create and fill data tables
        """
        self.data_model = _DataTableModel(self.data, self.descrition, self.cblist)
        self.setModel(self.data_model)
        self.setItemDelegate(_DataItemDelegate())
        self.setEditTriggers(Qt.QAbstractItemView.AllEditTriggers)
        self.data_model.fnColorSelect = self.fnColorSelect
        self.data_model.fnCheckBox = self.fnCheckBox
        self.data_model.fnValidate = self.fnValidate

        # actions
        self.data_model.dataChanged.connect(self._table_data_changed)
        self.selectionModel().selectionChanged.connect(self._selectionChanged)

    def _table_data_changed(self, topLeft, bottomRight):
        """ SIGNAL data in channel table has changed
        """
        # look for multiple selected rows
        cr = self.currentIndex().row()
        cc = self.currentIndex().column()
        selectedRows = [i.row() for i in self.selectedIndexes() if i.column() == cc]
        # change column value in all selected rows, but only if value is of type Bool
        if len(selectedRows) > 1:
            val = self.data_model._getitem(cr, cc)
            if type(val) is bool:
                for r in selectedRows:
                    self.data_model._setitem(r, cc, val)

        # notify parent about changes
        # self.emit(Qt.SIGNAL('dataChanged()'))
        self.dataChanged.emit()

    def _selectionChanged(self, selected, deselected):
        if len(selected.indexes()) > 0:
            self.selectedRow = selected.indexes()[0].row()
        '''
        selectedIdx = [i.row() for i in selected.indexes()]
        deselectedIdx = [i.row() for i in deselected.indexes()]
        print "selected: ",selectedIdx, " deselected: ", deselectedIdx
        '''

    def setData(self, data, description, cblist):
        """
        Initialize the table view
        @param data: list of data objects
        @param description: list of column description dictionaries
        @param cblist: dictionary of combo box list contents
        """
        self.data = data
        self.descrition = description
        self.cblist = cblist
        self._fillTables()

    def setfnColorSelect(self, lambdaColor):
        """ Set the background color selection function
        @param lambdaColor: color selction function
        """
        self.fnColorSelect = lambdaColor

    def setfnCheckBox(self, lambdaCheckBox):
        """ Set the checkbox display function
        @param lambdaCheckBox: function override
        """
        self.fnCheckBox = lambdaCheckBox

    def setfnValidate(self, lambdaValidate):
        """ Set the row validation function
        @param lambdaValidate: function override
        """
        self.fnValidate = lambdaValidate

    def getSelectedRow(self):
        return self.selectedRow


class _DataTableModel(QAbstractTableModel):
    """
    EEG and AUX table data model for the configuration pane
    """

    def __init__(self, data, description, cblist, parent=None, *args):
        ''' Constructor
        @param data: list of data objects
        @param description: list of column description dictionaries
        @param cblist: dictionary of combo box list contents
        '''
        super().__init__(parent=parent)
        self.arraydata = data
        # list of column description dictionaries
        # dictionary: {'variable':'variable name', 'header':'header text', 'edit':False/True, 'editor':'default' or 'combobox'}
        # optional entries: 'min': minum value, 'max': maximum value, 'dec': number of decimal places,
        #                   'step': spin box incr/decr
        #                   'indexed' : True, use value as combobox index
        self.columns = description

        # dictionary of combo box list contents
        # dictionary: {'variable name':['Item 1', 'Item 2', ...]}
        self.cblist = cblist

        # color selection function
        self.fnColorSelect = lambda x: None
        # checkbox modification function
        self.fnCheckBox = lambda x: None
        # row validation function
        self.fnValidate = lambda row, col, data: True

    def _getitem(self, row, column):
        ''' Get data item based on table row and column
        @param row: row number
        @param column: column number
        @return:  QVariant data value
        '''
        if (row >= len(self.arraydata)) or (column >= len(self.columns)):
            return None

        # get data object
        data = self.arraydata[row]
        # get variable name from column description
        variable_name = self.columns[column]['variable']
        # get variable value
        if hasattr(data, variable_name):
            d = vars(data)[variable_name]
            # get value from combobox list values?
            if 'indexed' in self.columns[column] and variable_name in self.cblist:
                try:
                    idx = int(d)
                    ok = True
                except:
                    idx = 0
                    ok = False

                if ok and 0 <= idx < len(self.cblist[variable_name]):
                    d = self.cblist[variable_name][idx]
        else:
            d = None
        return d

    def _setitem(self, row, column, value):
        ''' Set data item based on table row and column
        @param row: row number
        @param column: column number
        @param value: QVariant value object
        @return: True if property value was set, False if not
        '''
        if (row >= len(self.arraydata)) or (column >= len(self.columns)):
            return False

        # get data object
        data = self.arraydata[row]

        # get variable name from column description
        variable_name = self.columns[column]['variable']

        # get index from combobox list values
        if 'indexed' in self.columns[column] and variable_name in self.cblist:
            v = str(value)
            if v in self.cblist[variable_name]:
                value = self.cblist[variable_name].index(v)
            else:
                return False

        # set variable value
        if hasattr(data, variable_name):
            t = type(vars(data)[variable_name])
            if t is bool:
                vars(data)[variable_name] = bool(value)
                return True
            elif t is float:
                vars(data)[variable_name] = float(value)
                return True
            elif t is int:
                vars(data)[variable_name] = int(value)
                return True
            elif t is str:
                vars(data)[variable_name] = "%s" % str(value)
                return True
            else:
                return False
        else:
            return False

    def editorType(self, column):
        """
        Get the columns editor type from column description
        @param column: table column number
        @return: editor type as QVariant (string)
        """
        if column >= len(self.columns):
            return None
        return self.columns[column]['editor']

    def editorMinValue(self, column):
        """ Get the columns editor minimum value from column description
        @param column: table column number
        @return: minimum value as QVariant
        """
        if column >= len(self.columns):
            return None
        if 'min' in self.columns[column]:
            return self.columns[column]['min']
        else:
            return None

    def editorDecimals(self, column):
        """ Get the columns editor decimal places from column description
        @param column: table column number
        @return: minimum value as QVariant
        """
        if column >= len(self.columns):
            return None
        if 'dec' in self.columns[column]:
            return self.columns[column]['dec']
        else:
            return None

    def editorStep(self, column):
        """ Get the columns editor single step value from column description
        @param column: table column number
        @return: minimum value as QVariant
        """
        if column >= len(self.columns):
            return None
        if self.columns[column].has_key('step'):
            return self.columns[column]['step']
        else:
            return None

    def comboBoxList(self, column):
        """ Get combo box item list for specified column
        @param column: table column number
        @return: combo box item list as QVariant
        """
        if column >= len(self.columns):
            return None

        # get variable name from column description
        variable_name = self.columns[column]['variable']
        # lookup list in dictionary
        if self.cblist.has_key(variable_name):
            return self.cblist[variable_name]
        else:
            return None

    def rowCount(self, parent=QModelIndex()):
        """ Get the number of required table rows
        @return: number of rows
        """
        if parent.isValid():
            return 0
        return len(self.arraydata)

    def columnCount(self, parent=QModelIndex()):
        """ Get the number of required table columns
        @return: number of columns
        """
        if parent.isValid():
            return 0
        return len(self.columns)

    def data(self, index, role):
        ''' Abstract method from QAbstactItemModel to get cell data based on role
        @param index: QModelIndex table cell reference
        @param role: given role for the item referred to by the index
        @return: the data stored under the given role for the item referred to by the index
        '''
        if not index.isValid():
            return None

        # get the underlying data
        value = self._getitem(index.row(), index.column())

        if role == Qt.CheckState.CheckStateRole:
            # display function override?
            data = self.arraydata[index.row()]
            check = self.fnCheckBox((index.column(), data))
            if check is not None:
                if check:
                    return Qt.CheckState.Checked
                else:
                    return Qt.CheckState.Unchecked
            # use data value
            if type(value) is bool:
                if value:
                    return Qt.CheckState.Checked
                else:
                    return Qt.CheckState.Unchecked

        elif (role == Qt.ItemDataRole.DisplayRole) or (role == Qt.ItemDataRole.EditRole):
            if type(value) is not bool:
                return value

        elif role == Qt.ItemDataRole.BackgroundRole:
            # change background color for a specified row
            data = self.arraydata[index.row()]
            color = self.fnColorSelect(data)
            if not self.fnValidate(index.row(), index.column(), self.arraydata):
                color = QColor(255, 0, 0)
            if color is not None:
                return color

        return None

    def flags(self, index):
        """ Abstract method from QAbstactItemModel
        @param index: QModelIndex table cell reference
        @return: the item flags for the given index
        """
        if not index.isValid():
            return Qt.ItemFlag.ItemIsEnabled
        if not self.columns[index.column()]['edit']:
            return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
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
            left = self.createIndex(index.row(), 0)
            right = self.createIndex(index.row(), self.columnCount())
            if role == Qt.ItemDataRole.EditRole:
                if not self._setitem(index.row(), index.column(), value):
                    return False

                self.dataChanged.emit(index, index)

                return True
            elif role == Qt.ItemDataRole.CheckStateRole:
                if not self._setitem(index.row(), index.column(), value == Qt.CheckState.Checked):
                    return False
                self.dataChanged.emit(left, right)

                return True
        return False

    def headerData(self, section, orientation, role):
        """ Abstract method from QAbstactItemModel to get the column header
        @param section: column or row number
        @param orientation: Qt.Horizontal = column header, Qt.Vertical = row header
        @param role: given role for the item referred to by the index
        @return: header
        """
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.columns[section]['header']
        if orientation == Qt.Orientation.Vertical and role == Qt.ItemDataRole.DisplayRole:
            return str(section + 1)
        return None


class _DataItemDelegate(QStyledItemDelegate):
    pass