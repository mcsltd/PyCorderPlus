'''
Display Module

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
@date: $Date: 2013-06-05 12:04:17 +0200 (Mi, 05 Jun 2013) $
@version: 1.0

B{Revision:} $LastChangedRevision: 197 $
'''


import qwt as Qwt

from modbase import *
from PyQt6.QtCore import QSize, Qt
from PyQt6.QtWidgets import QApplication

from qtpy.QtGui import QBrush


class DISP_Scope(Qwt.QwtPlot, ModuleBase):
    """
    EEG signal display widget.
    """
    def __init__(self, *args, **keys):
        ModuleBase.__init__(self, usethread=True, name="Display", **keys)  # use transmit / receive thread
        Qwt.QwtPlot.__init__(self, *args)

        self.setMinimumSize(QSize(400, 200))
        self.setObjectName("Display")

        # XML parameter version
        # 1: initial version
        # 2: scale and group size added
        # 3: baseline correction flag added
        # 4: timebase values changed from per division to screen (factor 10)
        #    Type of timebase, scale and groupsize changed from string to float
        # 5: separate scale values for EEG and AUX channels
        self.xmlVersion = 5

        # self.setTitle('ActiChamp');
        self.setCanvasBackground(QBrush(Qt.GlobalColor.white))

        # ToDo: create online configuration pane
        # self.online_cfg = _OnlineCfgPane()
        # self.connect(self.online_cfg.comboBoxTime, Qt.SIGNAL("activated(QString)"),
        #              self.timebaseChanged)
        # self.connect(self.online_cfg.comboBoxScale, Qt.SIGNAL("currentIndexChanged(QString)"),
        #              self.scaleChanged)
        # self.connect(self.online_cfg.comboBoxChannels, Qt.SIGNAL("currentIndexChanged(int)"),
        #              self.channelsChanged)
        # self.connect(self.online_cfg.pushButton_Now, Qt.SIGNAL("clicked()"),
        #              self.baselineNowClicked)
        # self.connect(self.online_cfg.checkBoxBaseline, Qt.SIGNAL("stateChanged()"),
        #              self.baselineNowClicked)

        # Todo add: legend
        # legend = _ScopeLegend()
        # legend.setFrameStyle(Qt.QFrame.Box | Qt.QFrame.Sunken)
        # legend.setItemMode(Qwt.QwtLegend.ClickableItem)
        # self.insertLegend(legend, Qwt.QwtPlot.LeftLegend)
        # self.connect(self, Qt.SIGNAL("legendClicked(QwtPlotItem*)"),
        #              self.channelItemClicked)

        # grid
        # self.grid = Qwt.QwtPlotGrid()
        # self.grid.enableY(False)
        # self.grid.enableX(True)
        # self.grid.enableXMin(True)
        # self.grid.setMajPen(Qt.QPen(Qt.Qt.gray, 0, Qt.Qt.SolidLine))
        # self.grid.setMinPen(Qt.QPen(Qt.Qt.gray, 0, Qt.Qt.DashLine))
        # self.grid.attach(self)

        # ToDo add: X axes
        # font = Qt.QFont("arial", 9)
        # title = Qwt.QwtText('Time [s]')
        # title.setFont(font)
        # self.setAxisTitle(Qwt.QwtPlot.xBottom, title)
        # self.setAxisMaxMajor(Qwt.QwtPlot.xBottom, 5)
        # self.setAxisMaxMinor(Qwt.QwtPlot.xBottom, 10)
        # self.setAxisFont(Qwt.QwtPlot.xBottom, font)
        # self.TimeScale = _TimeScaleDraw()
        # self.setAxisScaleDraw(Qwt.QwtPlot.xBottom, self.TimeScale)

        # ToDo add: Y axis
        # self.setAxisTitle(Qwt.QwtPlot.yLeft, 'Amplitude');
        # self.setAxisMaxMajor(Qwt.QwtPlot.yLeft, 0);
        # self.setAxisMaxMinor(Qwt.QwtPlot.yLeft, 0);
        # self.enableAxis(Qwt.QwtPlot.yLeft, False)

        # self.plotscale = Qwt.QwtPlotScaleItem(Qwt.QwtScaleDraw.RightScale)
        # self.plotscale.setBorderDistance(5)
        # self.plotscale.attach(self)

        # reset trace buffer
        self.traces = []

        # reset marker buffer
        self.plot_markers = []  # list of QwtPlotMarker()
        self.input_markers = []  # list of EEG markers

        # EEG data block backup
        self.last_eeg = None
        self.last_slice = None

        # default settings
        # self.setScale(self.online_cfg.get_scale())  # µV / Division
        # self.timebase = self.online_cfg.get_timebase()  # s  / Screen
        self.xsize = 1500
        self.binning = 300
        self.binningoffset = 0
        self.channel_slice = slice(0, 0, 1)  # channel group selection
        self.baseline_request = False
        self.selectedChannel = None

        # set default display
        self.eeg = EEG_DataBlock()
        self.process_update(self.eeg)

        # timing test
        self.ttime = -1.0
        self.tcount = 10.0

        # start self.timerEvent() to update display asynchronously
        self.startTimer(30)
        self.update_display = False
        self.dataavailable = False

    def get_display_pane(self):
        """
        Get the signal display pane
        """
        return self


if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    obj = DISP_Scope()
    print(vars(obj))
    obj.show()
    app.exec()
