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
from PyQt6.QtCore import QSize, Qt, QRect, QPoint
from PyQt6.QtWidgets import QApplication, QFrame
from PyQt6.QtGui import QBrush, QPen, QFont




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

        # legend
        legend = _ScopeLegend()
        legend.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Sunken)
        legend.setDefaultItemMode(Qwt.QwtLegend.itemClicked)
        self.insertLegend(legend, Qwt.QwtPlot.LeftLegend)
        # self.connect(self, Qt.SIGNAL("legendClicked(QwtPlotItem*)"),
        #              self.channelItemClicked)

        # grid
        self.grid = Qwt.QwtPlotGrid()
        self.grid.enableY(False)
        self.grid.enableX(True)
        self.grid.enableXMin(True)
        self.grid.setMajorPen(QPen(Qt.GlobalColor.gray, 0, Qt.PenStyle.SolidLine))
        self.grid.setMinorPen(QPen(Qt.GlobalColor.gray, 0, Qt.PenStyle.DashLine))
        self.grid.attach(self)

        # X axes
        font = QFont("arial", 9)
        title = Qwt.QwtText('Time [s]')
        title.setFont(font)
        self.setAxisTitle(Qwt.QwtPlot.xBottom, title)
        self.setAxisMaxMajor(Qwt.QwtPlot.xBottom, 5)
        self.setAxisMaxMinor(Qwt.QwtPlot.xBottom, 10)
        self.setAxisFont(Qwt.QwtPlot.xBottom, font)
        self.TimeScale = _TimeScaleDraw()
        self.setAxisScaleDraw(Qwt.QwtPlot.xBottom, self.TimeScale)

        # Y axis
        self.setAxisTitle(Qwt.QwtPlot.yLeft, 'Amplitude')
        self.setAxisMaxMajor(Qwt.QwtPlot.yLeft, 0)
        self.setAxisMaxMinor(Qwt.QwtPlot.yLeft, 0)
        self.enableAxis(Qwt.QwtPlot.yLeft, False)

        # self.plotscale = Qwt.QwtPlotSeriesItem(Qwt.QwtScaleDraw.RightScale)
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


class _ScopeLegend(Qwt.QwtLegend):
    """ QwtPlot custom legend widget.
        Only necessary to make legend size same as canvas and to distribute
        labels at curve positions
        """
    def __init__(self, *args):
        super().__init__()
        layout = self.contentsWidget().layout()
        layout.setSpacing(0)

    def heightForWidth(self, width):
        return 0

    def sizeHint(self):
        sz = Qwt.QwtLegend.sizeHint(self)
        width = sz.width() + Qwt.QwtLegend.verticalScrollBar(self).sizeHint().width()
        sz.setHeight(200)
        sz.setWidth(width)
        return sz

    def layoutContents(self):
        topMargin = self.parent().plotLayout().canvasMargin(Qwt.QwtPlot.xTop)
        bottomMargin = self.parent().plotLayout().canvasMargin(Qwt.QwtPlot.xBottom)
        viewport = self.contentsWidget().parentWidget()
        visibleSize = viewport.size()
        items = self.legendItems()
        itemspace = float(visibleSize.height() - (topMargin + bottomMargin)) / (self.itemCount() + 1)
        offset = itemspace * 0.8 - itemspace * 0.5 + topMargin
        yBottom = 0
        for idx, item in enumerate(items):
            yTop = (idx + 1) * itemspace
            itemHeight = int(yTop - yBottom)
            item.setFixedHeight(itemHeight)
            yBottom += itemHeight
        layout = self.contentsWidget().layout()
        layout.setGeometry(QRect(QPoint(0, offset),
                                 QPoint(visibleSize.width(), visibleSize.height() - 2 * offset)))
        self.contentsWidget().resize(visibleSize.width(), visibleSize.height())
        return


class _TimeScaleDraw(Qwt.QwtScaleDraw):
    """
    Draw custom time values for x-axis
    """

    def __init__(self, *args):
        super().__init__()
        self._offset = 0.0

    def label(self, value):
        ret = Qwt.QwtText()
        v = value
        s = "%.2f" % v
        ret.setText(s)
        return ret

    def setOffset(self, offset):
        self._offset = offset
        Qwt.QwtScaleDraw.invalidateCache(self)


if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    obj = DISP_Scope()
    print(vars(obj))
    obj.show()
    app.exec()