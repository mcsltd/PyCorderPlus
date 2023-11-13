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
import qwt
import qwt as Qwt

from qwt.scale_widget import QwtScaleWidget

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

        self.plotscale = qwt.scale_widget.QwtScaleWidget()
        self.plotscale.setAlignment(qwt.QwtScaleDraw.RightScale)
        self.plotscale.setBorderDist(5, 0)
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
        self.timebase = 0.1
        self.setScale(0.5)

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

    def setDefault(self):
        ''' Set all module parameters to default values
        '''
        # ToDo: self.setScale(self.online_cfg.set_scale(100.0, 1000.0))  # EEG: 100µV, AUX: 1000µV / Division
        # self.timebase = self.online_cfg.set_timebase(10.0)  # 10s / Screen
        # self.online_cfg.set_groupsize(16)  # group size 16 channels
        # self.online_cfg.checkBoxBaseline.setChecked(True)  # baseline correction enabled

        # update display
        self.process_update(self.eeg)

    def process_update(self, params):
        ''' Channel properties have changed, module needs update
        @param params: EEG_DataBlock with channel properties
        '''
        if params is not None:
            self.eeg = params
            # ToDo: self.online_cfg.update_content(self.eeg)
            self.arrangeTraces()
            self.replot()
        return params

    def process_start(self):
        ''' Module start command.
        '''
        # reset timing test timer
        self.ttime = -1.0

    def process_input(self, datablock):
        ''' Data available
        @param datablock: EEG_DataBlock with channel data
        '''
        # don't display impedance date
        if datablock.recording_mode == RecordingMode.IMPEDANCE:
            return

        # get data from source
        self.eeg = datablock
        self.dataavailable = True

        # timing test functions
        # first call
        if self.ttime < 0:
            self.ttime = time.clock()
            self.tcount = 30.0
        else:
            if time.clock() >= self.ttime + self.tcount:
                # send status info
                info = "Received Samples = %d / Sample Counter = %d / Time = %.3fs" \
                       % (self.eeg.sample_counter, self.eeg.sample_channel[0, -1] + 1, time.clock() - self.ttime)
                # self.send_event(ModuleEvent(self._object_name, EventType.MESSAGE))
                self.tcount += 30.0

        # update display buffers
        self.setDisplay()

    def setDisplay(self):
        """
        Copy all traces from input buffer to display transfer buffer
        """
        # select the requested channel group
        self.channel_group = self.eeg.eeg_channels[self.channel_slice]
        self.channel_group_properties = self.eeg.channel_properties[self.channel_slice]

        # anything to display?
        if self.channel_group.shape[0] == 0:
            return

        # calculate downsampling size
        points = self.channel_group.shape[1]
        down = int(points / (self.eeg.sample_rate * self.dtX))

        # down sample and copy raw data to ring buffer
        offset = 0
        for buf in self.buffer:
            if self.channel_group.shape[0] > offset:
                # r = self.rebin(self.channel_group[offset], tuple([down]))
                r = -self.channel_group[offset][self.binningoffset::self.binning]
                bufindex = np.arange(self.writePointer, self.writePointer + len(r))
                buf.put(bufindex, r, mode='wrap')
            offset += 1
        # down sample and copy sample counter buffer
        r = self.eeg.sample_channel[0][self.binningoffset::self.binning]
        bufindex = np.arange(self.writePointer, self.writePointer + len(r))
        self.sc_buffer[0].put(bufindex, r, mode='wrap')

        # update write pointer
        self.writePointer += len(r)
        # wrap around occurred?
        if self.writePointer >= self.buffer.shape[1]:
            # yes, adjust write pointer
            while self.writePointer >= self.buffer.shape[1]:
                self.writePointer -= self.buffer.shape[1]

            # request new baseline values
            self.baseline_request = True

            # and calculate new time axis offset
            sc = self.eeg.sample_channel[0][self.binningoffset::self.binning]  # down sample the sample counter buffer
            scLeft = sc[
                         len(sc) - self.writePointer - 1] / self.eeg.sample_rate  # sample counter at the leftmost screen position
            # self.TimeScale.setOffset(scLeft)
            # self.update()

        # calculate signal baselines for display baseline correction
        if self.baseline_request and (self.writePointer > 10):
            self.baseline_request = False
            self.baselines = np.mean(self.buffer[:, 5:10], axis=1).reshape(-1, 1)

        # calculate new binning offset
        self.binningoffset = self.binning - (points - self.binningoffset - (len(r) - 1) * self.binning)

        # normalize and offset ring buffer values
        channels = len(self.traces)
        bottomMargin = -2.0  # no margin, clip below window
        topMargin = channels + 1.0  # no margin, clip above window
        scale = self.axisScaleDiv(Qwt.QwtPlot.yLeft).range() / self.scale / 10.0
        offset = np.arange(channels, 0, -1).reshape(-1, 1) - 0.8

        # baseline correction
        # if self.online_cfg.checkBoxBaseline.isChecked():
        #     buffer = (self.buffer - self.baselines) * scale + offset
        # else:
        #     buffer = self.buffer * scale + offset
        buffer = (self.buffer - self.baselines) * scale + offset

        # clip to visible area
        buffer.clip(bottomMargin, topMargin, out=self.displaybuffer)

        # add EEG marker to marker transfer list
        self.input_markers.extend(self.eeg.markers)

        # redisplay everything
        if self.receive_data_available() < 3:
            self.update_display = True

    def process_output(self):
        ''' Send data to next module
        @return: EEG_DataBlock if available, else return None
        '''
        if self.dataavailable:
            self.dataavailable = False
            # send performance / utilization event
            totaltime = 1000.0 * self.eeg.performance_timer_max
            sampletime = 1000.0 * totaltime / self.eeg.sample_channel.shape[1]
            utilization = sampletime * self.eeg.sample_rate / 1e6 * 100.0
            if self._instance == 0:
                # self.send_event(ModuleEvent(self._object_name,
                #                             EventType.STATUS,
                #                             info = utilization,
                #                             status_field = "Utilization"))
                pass
        return None

    def arrangeTraces(self):
        ''' Setup display traces according to EEG data block settings
        '''
        # select the requested channel group
        self.channel_group = self.eeg.eeg_channels[self.channel_slice]
        self.channel_group_properties = self.eeg.channel_properties[self.channel_slice]

        # remove old traces
        for pc in self.traces:
            pc.detach()
        self.traces = []

        # insert new traces
        font = QFont("arial", 8)
        for pccount in range(self.channel_group.shape[0]):
            color = self.channel_group_properties[pccount].color
            title = Qwt.QwtText(self.channel_group_properties[pccount].name)
            title.setFont(font)
            title.setColor(color)
            title.setPaintAttribute(Qwt.QwtText.PaintUsingTextFont)
            pc = Qwt.QwtPlotCurve(title)
            pc.setPen(QPen(color, 0))
            pc.setYAxis(Qwt.QwtPlot.yLeft)
            pc.setCurveAttribute(Qwt.QwtPlotCurve.Lines.PaintFiltered)
            pc.attach(self)
            self.traces.append(pc)

        # # reduce the legend items margin
        # for item in self.legend():
        #     item.setMargin(0)

        # update Y axis scale
        self.setAxisScale(Qwt.QwtPlot.yLeft, -1.0, len(self.traces), 1.0)

        # update sample buffer
        self.setTimebase(self.timebase)

    def addPlotMarker(self, xPosition, label, samplecounter):
        ''' Create and add trigger event marker
        @param xPosition: horizontal screen position
        @param label: label string
        @param samplecounter: total sample position
        '''
        margin = float(len(self.traces) + 1) / 10.0 / 3.0 # 2.5% bottom margin
        sym = Qwt.QwtSymbol()
        sym.setStyle(Qwt.QwtSymbol.VLine)
        sym.setSize(20)
        mX = Qwt.QwtPlotMarker()
        mX.setLabel(Qwt.QwtText(label))
        mX.setLabelAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom)
        mX.setLineStyle(Qwt.QwtPlotMarker.NoLine)
        mX.setXValue(xPosition)
        mX.setYValue(-1.0 + margin)
        mX.setSymbol(sym)
        mX.sampleCounter = samplecounter
        mX.attach(self)
        self.plot_markers.append(mX)

    def timerEvent(self, e):
        ''' Timer event to update display
        '''
        if self.update_display:
            # acquire thread lock
            self._thLock.acquire()
            self.update_display = False

            # check color attributes
            for pccount in range(self.channel_group.shape[0]):
                if self.selectedChannel == self.channel_group_properties[pccount].name:
                    color = Qt.GlobalColor.green
                else:
                    color = self.channel_group_properties[pccount].color
                if (self.traces[pccount].pen().color != color):
                    self.traces[pccount].setPen(QPen(color, 0))
                    title = self.traces[pccount].title()
                    title.setColor(color)
                    self.traces[pccount].setTitle(title)

            # copy ring buffer to display
            idx = 0
            for pc in self.traces:
                pc.setData(self.xValues, self.displaybuffer[idx])
                idx += 1

            # add trigger markers
            for marker in self.input_markers:
                diffpos = np.int64(self.sc_buffer[0] - marker.position)
                idx = np.abs(diffpos).argmin(0)
                self.addPlotMarker(self.xValues[idx], marker.description, marker.position)
            # remove processed markers
            self.input_markers = []

            # remove old markers
            min_sc = self.sc_buffer[0].min()
            for marker in self.plot_markers[:]:
                if marker.sampleCounter < min_sc:
                    marker.detach()
                    self.plot_markers.remove(marker)

            # release thread lock
            self._thLock.release()

            t = time.clock()
            self.replot()
            displayTime = time.clock() - t

    def setTimebase(self, timebase):
        ''' Change the display timebase
        @param timebase: new timebase value in seconds per screen
        '''
        self.timebase = timebase

        # calculate new binning value for current sample rate
        inputsize = self.eeg.sample_rate * self.timebase
        self.binning = max([1, int(inputsize / self.xsize)])
        self.binningoffset = 0

        # calculate new ring buffer size
        self.dtX = self.binning / self.eeg.sample_rate
        self.xValues = np.arange(0.0, self.timebase, self.dtX)
        self.buffer = np.zeros((len(self.traces), len(self.xValues)), 'd')  # channel buffer
        self.sc_buffer = np.zeros((1, len(self.xValues)), np.uint64)  # sample counter buffer
        self.displaybuffer = np.zeros((len(self.traces), len(self.xValues)), 'd')  # channel display transfer buffer
        self.baselines = np.zeros((len(self.traces), 1), 'd')  # baseline correction buffer

        # reset buffer pointer
        self.writePointer = 0

        # request new baseline values
        self.baseline_request = True

        # update X axis scale
        self.grid.setMinPen(QPen(Qt.GlobalColor.gray, 0, Qt.PenStyle.DotLine))
        if timebase < 1.0:
            major = 0.1
            self.setAxisMaxMinor(Qwt.QwtPlot.xBottom, 5)
        elif timebase > 10.0:
            major = 10.0
            self.setAxisMaxMinor(Qwt.QwtPlot.xBottom, 10)
            self.grid.setMinPen(QPen(Qt.GlobalColor.gray, 0, Qt.PenStyle.SolidLine))
        else:
            major = 1.0
            self.setAxisMaxMinor(Qwt.QwtPlot.xBottom, 5)
        self.setAxisScale(Qwt.QwtPlot.xBottom, 0, timebase, major)

        # remove all markers
        for marker in self.plot_markers:
            marker.detach()
        self.plot_markers = []
        self.input_markers = []

        self.replot()

    def setScale(self, scale):
        ''' Change the display scaling
        @param scale: new scale value in µV/Div
        '''
        self.scale = scale
        ticks = list(np.arange(0.0, scale*11.0, scale))
        yScaleDiv = Qwt.QwtScaleDiv(0.0, scale*10.0, [], ticks, [])
        self.plotscale.setScaleDiv(yScaleDiv)
        self.replot()

    def onlineCfgChanged(self):
        ''' Reset signal display if any of the online parameters has changed
        and acquisition is not running
        '''
        if not self.isRunning():
            self.arrangeTraces()

    # actions from online configuration pane

    # def timebaseChanged(self, value):
    #     ''' SIGNAL New timebase value selected
    #     '''
    #     # acquire thread lock
    #     self._thLock.acquire()
    #     # change timebase
    #     # self.setTimebase(self.online_cfg.get_timebase())
    #     # release thread lock
    #     self._thLock.release()
    #     self.onlineCfgChanged()

    # def scaleChanged(self, value):
    #     ''' SIGNAL New scale value selected
    #     '''
    #     # acquire thread lock
    #     self._thLock.acquire()
    #     # change scale
    #     self.setScale(self.online_cfg.get_scale())
    #     # release thread lock
    #     self._thLock.release()
    #     self.onlineCfgChanged()

    # def channelsChanged(self, idx):
    #     ''' SIGNAL Display channel configuration changed
    #     '''
    #     # acquire thread lock
    #     self._thLock.acquire()
    #     # change display channel configuration
    #     if idx >= 0:
    #         self.channel_slice = self.online_cfg.comboBoxChannels.itemData(idx).toPyObject()
    #         self.arrangeTraces()
    #     else:
    #         self.channel_slice = slice(0, 0, 1)
    #         # release thread lock
    #     self._thLock.release()

    # def baselineNowClicked(self):
    #     ''' SIGNAL Baseline correction now
    #     '''
    #     # acquire thread lock
    #     self._thLock.acquire()
    #     # use channel values at current write pointer position as new baselines
    #     self.baselines = self.buffer[:, self.writePointer].reshape(-1, 1)
    #     # release thread lock
    #     self._thLock.release()
    #     self.onlineCfgChanged()

    # def channelItemClicked(self, plotitem):
    #     ''' SIGNAL Channel legend clicked
    #     '''
    #     if self.selectedChannel == plotitem.title().text():
    #         self.selectedChannel = None
    #     else:
    #         self.selectedChannel = plotitem.title().text()
    #     self.send_event(ModuleEvent(self._object_name,
    #                                 EventType.COMMAND,
    #                                 info="ChannelSelected",
    #                                 cmd_value=plotitem.title().text()))


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
        topMargin = self.parent().layout().canvasMargin(Qwt.QwtPlot.xTop)
        bottomMargin = self.parent().layout().canvasMargin(Qwt.QwtPlot.xBottom)
        viewport = self.contentsWidget().parentWidget()
        visibleSize = viewport.size()
        items = self.legendItems()
        print(self.sizeHint())
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
