# -*- coding: utf-8 -*-
"""
Impedance Display Module

PyCorder ActiChamp Recorder

------------------------------------------------------------

Copyright (C) 2010, Brain Products GmbH, Gilching
Copyright (C) 2024, Medical Computer Systems Ltd


This file is part of PyCorderPlus
"""

from modbase import *

from PyQt6.QtWidgets import (QApplication, QDialog, QHeaderView, QTableWidgetItem)
from PyQt6.QtCore import Qt, QMetaType, pyqtSignal
from PyQt6.QtGui import QFont, QIntValidator, QValidator, QColor

from res import frmImpedanceDisplay

import qwt


class IMP_Display(ModuleBase):
    """
    Display impedance values
    """

    update = pyqtSignal("PyQt_PyObject")

    def __init__(self, *args, **kwargs):
        super().__init__(name="Impedance Display", **kwargs)

        # XML parameter version
        # 1: initial version
        self.xmlVersion = 1

        # set default values
        self.params = None
        self.data = None
        self.dataavailable = False

        self.impDialog = None  #: Impedance dialog widget
        self.range_max = 50  #: Impedance range 0-range_max in KOhm
        self.show_values = True  #: Show numerical impedance values

    def terminate(self):
        """ 
        Destructor
        """
        # close dialog widget on exit
        if self.impDialog is not None:
            self.impDialog.close()
            self.impDialog = None

    def setDefault(self):
        """ 
        Set all module parameters to default values
        """
        self.range_max = 50
        self.show_values = True

    def process_start(self):
        """ 
        Prepare and open impedance dialog if recording mode == IMPEDANCE
        """
        # create and show the impedance dialog
        if self.params.recording_mode == RecordingMode.IMPEDANCE:
            if self.impDialog is None:
                # impedance dialog should be always on top
                topLevelWidgets = QApplication.topLevelWidgets()
                activeWindow = QApplication.activeWindow()
                if activeWindow:
                    self.impDialog = DlgImpedance(self, QApplication.activeWindow())
                else:
                    if len(topLevelWidgets):
                        self.impDialog = DlgImpedance(self, topLevelWidgets[0])
                    else:
                        self.impDialog = DlgImpedance(self)
                self.impDialog.setWindowFlags(Qt.WindowType.Tool)
                self.impDialog.show()
                self.impDialog.updateLabels(self.params)
            else:
                self.impDialog.updateLabels(self.params)
            self.sendColorRange()
        else:
            if self.impDialog is not None:
                self.impDialog.close()
                self.impDialog = None

    def sendColorRange(self):
        """
        Send new impedance color range as ModuleEvent to update ActiCap LED color range
        """
        val = tuple([self.range_max / 3.0, self.range_max * 2.0 / 3.0])
        self.send_event(ModuleEvent(self._object_name, EventType.COMMAND, info="ImpColorRange",
                                    cmd_value=val))

    def process_stop(self):
        """
        Close impedance dialog
        """
        if self.impDialog is not None:
            self.impDialog.close()
            self.impDialog = None

    def process_update(self, params):
        """
        Get channel properties and
        propagate parameter update down to all attached receivers
        """
        self.params = params
        # propagate down
        return params

    def process_input(self, datablock):
        """
        Get data from input queue and update display
        """
        self.dataavailable = True
        self.data = datablock

        # nothing to do if not in impedance mode
        if datablock.recording_mode != RecordingMode.IMPEDANCE:
            return

        # check for an outdated impedance structure
        if len(datablock.impedances) > 0 or len(datablock.channel_properties) != len(self.params.channel_properties):
            raise ModuleError(self._object_name, "outdated impedance structure received!")

        if self.impDialog is not None:
            self.update.emit(datablock)
            pass

    def process_output(self):
        """
        Put processed data into output queue
        """
        if not self.dataavailable:
            return None
        self.dataavailable = False
        return self.data

    def getXML(self):
        """
        Get module properties for XML configuration file
        @return: objectify XML element::
            e.g.
            <IMP_Display instance="0" version="1">
                <range_max>50</range_max>
                ...
            </IMP_Display>
        """
        E = objectify.E
        cfg = E.IMP_Display(E.range_max(self.range_max),
                            E.show_values(self.show_values),
                            version=str(self.xmlVersion),
                            instance=str(self._instance),
                            module="impedance")
        return cfg

    def setXML(self, xml):
        """
         Set module properties from XML configuration file
        @param xml: complete objectify XML configuration tree,
        module will search for matching values
        """
        # search my configuration data
        displays = xml.xpath("//IMP_Display[@module='impedance' and @instance='%i']" % self._instance)
        if len(displays) == 0:
            # configuration data not found, leave everything unchanged
            return

            # we should have only one display instance from this type
        cfg = displays[0]

        # check version, has to be lower or equal than current version
        version = cfg.get("version")
        if (version is None) or (int(version) > self.xmlVersion):
            self.send_event(ModuleEvent(self._object_name, EventType.ERROR, "XML Configuration: wrong version"))
            return
        version = int(version)

        # get the values
        try:
            self.range_max = cfg.range_max.pyval
            self.show_values = cfg.show_values.pyval
        except Exception as e:
            self.send_exception(e, severity=ErrorSeverity.NOTIFY)


"""
Impedance dialog.
"""


class DlgImpedance(QDialog, frmImpedanceDisplay.Ui_frmImpedanceDisplay):
    """
    Impedance display dialog
    """

    def __init__(self, module, *args):
        super().__init__()
        self.setupUi(self)
        self.module = module
        self.params = None  # last received parameter block
        self.data = None  # last received data block

        # create table view grid (10x16 eeg electrodes + 1 row for ground electrode)
        cc = 10
        rc = 16
        self.tableWidgetValues.setColumnCount(cc)
        self.tableWidgetValues.setRowCount(rc + 1)
        self.tableWidgetValues.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tableWidgetValues.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tableWidgetValues.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tableWidgetValues.verticalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        # add ground electrode row
        self.tableWidgetValues.setSpan(rc, 0, 1, cc)
        # row headers
        rheader = []
        for r in range(rc):
            rheader.append("%d - %d" % (r * cc + 1, r * cc + cc))
        rheader.append("GND")
        self.tableWidgetValues.setVerticalHeaderLabels(rheader)
        # create cell items
        fnt = QFont()
        fnt.setPointSize(8)
        for r in range(rc):
            for c in range(cc):
                item = QTableWidgetItem()
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item.setFont(fnt)
                self.tableWidgetValues.setItem(r, c, item)

        # GND electrode cell
        item = QTableWidgetItem()
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        item.setFont(fnt)
        item.setText("GND")
        self.tableWidgetValues.setItem(rc, 0, item)
        self.defaultColor = item.background().color()

        # set range list
        self.comboBoxRange.clear()
        self.comboBoxRange.addItem("15")
        self.comboBoxRange.addItem("50")
        self.comboBoxRange.addItem("100")
        self.comboBoxRange.addItem("500")

        # set validators
        validator = QIntValidator(self)
        validator.setBottom(15)
        validator.setTop(500)
        self.comboBoxRange.setValidator(validator)
        self.comboBoxRange.setEditText(str(self.module.range_max))

        # setup color scale
        self.linearscale = False
        self.scale_engine = qwt.scale_engine.QwtLinearScaleEngine()
        self.scale_interval = qwt.QwtInterval(0, self.module.range_max)
        self.scale_map = qwt.QwtLinearColorMap(Qt.GlobalColor.green, Qt.GlobalColor.red)
        if self.linearscale:
            self.scale_map.addColorStop(0.45, Qt.GlobalColor.yellow)
            self.scale_map.addColorStop(0.55, Qt.GlobalColor.yellow)
            self.scale_map.setMode(qwt.QwtLinearColorMap.ScaledColors)
        else:
            self.scale_map.addColorStop(0.33, Qt.GlobalColor.yellow)
            self.scale_map.addColorStop(0.66, Qt.GlobalColor.red)
            self.scale_map.setMode(qwt.QwtLinearColorMap.FixedColors)
        self.ScaleWidget.setColorMap(self.scale_interval, self.scale_map)
        self.ScaleWidget.setColorBarEnabled(True)
        self.ScaleWidget.setColorBarWidth(30)
        self.ScaleWidget.setBorderDist(10, 10)

        # set default values
        self.setColorRange(0, self.module.range_max)
        self.checkBoxValues.setChecked(self.module.show_values)

        # actions
        self.comboBoxRange.editTextChanged.connect(self._rangeChanged)
        self.checkBoxValues.stateChanged.connect(self._showvalues_changed)
        self.module.update.connect(self._updateValues)

    def _rangeChanged(self, rrange):
        """
        SIGNAL range combo box value has changed
        @param range: new range value in KOhm
        """
        # validate range
        valid = self.comboBoxRange.validator().validate(rrange, 0)[0]
        if valid != QValidator.State.Acceptable:
            return
            # use new range
        newrange = int(rrange)

        self.setColorRange(0, newrange)
        self.module.range_max = newrange
        self._updateValues(self.data)
        self.module.sendColorRange()

    def setColorRange(self, cmin, cmax):
        """
        Create new color range for the scale widget
        """
        self.scale_interval.setMaxValue(cmax)
        self.scale_interval.setMinValue(cmin)
        self.ScaleWidget.setColorMap(self.scale_interval, self.scale_map)
        self.ScaleWidget.setScaleDiv(self.scale_engine.divideScale(self.scale_interval.minValue(), self.scale_interval.maxValue(), 5, 2))

    def _showvalues_changed(self, state):
        """
        SIGNAL show values radio button clicked
        """
        self.module.show_values = (state == Qt.CheckState.Checked)
        self._updateValues(self.data)

    def _updateValues(self, data):
        """
        SIGNAL send from impedance module to update cell values
        @param data: EEG_DataBlock
        """
        if data is None:
            return
        # keep the last data block
        self.data = copy.deepcopy(data)

        # check for an outdated impedance structure
        if len(data.impedances) > 0 or len(data.channel_properties) != len(self.params.channel_properties):
            print("outdated impedance structure received!")
            return

        cc = self.tableWidgetValues.columnCount()
        rc = self.tableWidgetValues.rowCount() - 1
        # EEG electrodes
        gndImpedance = None
        impCount = 0
        for idx, ch in enumerate(data.channel_properties):
            if (ch.enable or ch.isReference) and (ch.input > 0) and (ch.input <= rc * cc) and (
                    ch.inputgroup == ChannelGroup.EEG):
                impCount += 1
                row = int((ch.input - 1) / cc)
                col = int((ch.input - 1) % cc)
                item = self.tableWidgetValues.item(row, col)

                # channel has a data impedance value?
                if self.params.eeg_channels[idx, ImpedanceIndex.DATA] == 1:
                    # data channel value
                    value, color = self._getValueText(data.eeg_channels[idx, ImpedanceIndex.DATA])
                    item.setBackground(color)
                    if self.module.show_values:
                        item.setText("%s\n%s" % (item.label, value))
                    else:
                        item.setText(item.label)

                # channel has a reference impedance value?
                if self.params.eeg_channels[idx, ImpedanceIndex.REF] == 1:
                    row = int(ch.input / cc)
                    col = int(ch.input % cc)
                    item = self.tableWidgetValues.item(row, col)
                    # reference channel value
                    value, color = self._getValueText(data.eeg_channels[idx, ImpedanceIndex.REF])
                    item.setBackground(color)
                    if self.module.show_values:
                        item.setText("%s\n%s" % (item.label, value))
                    else:
                        item.setText(item.label)

                # channel has a GND impedance value?
                if gndImpedance is None and self.params.eeg_channels[idx, ImpedanceIndex.GND] == 1:
                    gndImpedance = data.eeg_channels[idx, ImpedanceIndex.GND]

        # GND electrode, take the value of the first EEG electrode
        item = self.tableWidgetValues.item(rc, 0)
        if gndImpedance is None:
            item.setText("")
            item.setBackground(Qt.GlobalColor.white)
        else:
            value, color = self._getValueText(gndImpedance)
            item.setBackground(color)
            if self.module.show_values:
                item.setText("%s\n%s" % ("GND", value))
            else:
                item.setText("GND")

    def _getValueText(self, impedance):
        """ evaluate the impedance value and get the text and color for display
        @return: text and color
        """
        if impedance > CHAMP_IMP_INVALID:
            valuetext = "disconnected"
            color = QColor(128, 128, 128)
        else:
            v = impedance / 1000.0
            if impedance == CHAMP_IMP_INVALID:
                valuetext = "out of range"
            else:
                valuetext = "%.0f" % v
            color = self.ScaleWidget.colorMap().color(self.ScaleWidget.colorBarInterval(), v)
        return valuetext, color

    def updateLabels(self, params):
        """
        Update cell labels
        """
        # copy channel configuration
        self.params = copy.deepcopy(params)

        # update cells
        cc = self.tableWidgetValues.columnCount()
        rc = self.tableWidgetValues.rowCount() - 1

        # reset items
        for row in range(rc):
            for col in range(cc):
                item = self.tableWidgetValues.item(row, col)
                item.setText("")
                item.label = ""
                item.setBackground(Qt.GlobalColor.white)
        # set channel labels
        for idx, ch in enumerate(self.params.channel_properties):
            if (ch.enable or ch.isReference) and (ch.input > 0) and (ch.input <= rc * cc) and (
                    ch.inputgroup == ChannelGroup.EEG):
                row = int((ch.input - 1) / cc)
                col = int((ch.input - 1) % cc)
                # channel has a reference impedance value?
                if self.params.eeg_channels[idx, ImpedanceIndex.REF] == 1:
                    # prefix the channel name
                    name = ch.name + " " + ImpedanceIndex.Name[ImpedanceIndex.DATA]
                    self._setLabelText(row, col, name)
                    # put the reference values at the following table item, if possible
                    name = ch.name + " " + ImpedanceIndex.Name[ImpedanceIndex.REF]
                    row = int(ch.input / cc)
                    col = int(ch.input % cc)
                    self._setLabelText(row, col, name)
                else:
                    self._setLabelText(row, col, ch.name)

    def _setLabelText(self, row, col, text):
        item = self.tableWidgetValues.item(row, col)
        item.setText(text)
        item.setBackground(QColor(128, 128, 128))
        item.label = text

    def reject(self):
        """
        ESC key pressed, Dialog want's close, just ignore it
        """
        return

    def closeEvent(self, event):
        """ Dialog want's close, send stop request to main window
        """
        self.setParent(None)
        self.disconnect(self.module.update.connect(self._updateValues))
        if self.sender() is None:
            self.module.send_event(ModuleEvent(self.module._object_name, EventType.COMMAND, "Stop"))
        event.accept()


