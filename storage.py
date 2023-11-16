"""
Storage Module for Vision EEG file format

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
@date: $Date: 2013-06-20 14:00:34 +0200 (Do, 20 Jun 2013) $
@version: 1.0

B{Revision:} $LastChangedRevision: 206 $
"""
import time

from modbase import *
import platform
import ctypes as ct

"""
Storage module.
"""


class StorageVision(ModuleBase):
    """
    Vision Date Exchange Format
    - Storage class using ctypes
    """

    def __init__(self, *args, **kwargs):
        super().__init__(queuesize=50, name="StorageVision", **kwargs)

        # XML parameter version
        # 1: initial version
        # 2: minimum required disk space added
        self.xmlVersion = 2

        # get OS architecture (32/64-bit)
        self.x64 = ("64" in platform.architecture()[0])

        # load C library
        try:
            self.libc = ct.cdll.msvcrt  # Windows
        except:
            self.libc = ct.CDLL("libc.so.6")  # Linux

        # set error handling for C library
        def errcheck(res, func, args):
            if not res:
                raise IOError
            return res

        self.libc._wfopen.errcheck = errcheck
        if self.x64:
            self.libc._wfopen.restype = ct.c_int64
            self.libc.fwrite.argtypes = [ct.c_void_p, ct.c_size_t, ct.c_size_t, ct.c_int64]
            self.libc.fclose.argtypes = [ct.c_int64]
        else:
            self.libc._wfopen.restype = ct.c_void_p
            self.libc.fwrite.argtypes = [ct.c_void_p, ct.c_size_t, ct.c_size_t, ct.c_void_p]
            self.libc.fclose.argtypes = [ct.c_void_p]

        self.data = None
        self.dataavailable = False
        self.params = None
        self.last_impedance = None  #: last received impedance EEG block
        self.last_impedance_config = None  #: last received impedance configuration EEG block
        self.moduledescription = ""  #: description of connected modules

        # configuration data
        self.setDefault()

        # output files
        self.file_name = None  #: output file name
        self.data_file = 0  #: clib data file handle
        self.header_file = 0  #: header file handle
        self.marker_file = 0  #: marker file handle
        self.marker_counter = 0  #: total number of markers written
        self.start_sample = 0  #: sample counter of first sample written to file
        self.marker_newseg = False  #: request for new segment marker

        self.next_samplecounter = -2  #: verify sample counter of next EEG block
        self.total_missing = 0  #: number of total samples missing
        self.samples_written = 0  #: number of samples written to file
        self.write_error = False  #: write to disk failed
        self.min_disk_space = 1.0  #: minimum free disk space in GByte

    def setDefault(self):
        """
        Set all module parameters to default values
        """
        self.default_path = ""  #: default data storage path
        self.default_prefix = ""  #: prefex for data files e.g. "EEG_"
        self.default_numbersize = 6  #: number of digits to append to file name
        self.default_autoname = False  #: create auto file name

    def process_start(self):
        """
        Start data acquisition
        """
        # reset sample counter check
        self.missing_timer = time.clock()
        self.missing_interval = 0
        self.missing_cumulated = 0
        self.next_samplecounter = -2
        # ToDo: enable recording button
        # if self.params.recording_mode != RecordingMode.IMPEDANCE:
        #     self.online_cfg.pushButtonRecord.setEnabled(True)
        # else:
        #     self.online_cfg.pushButtonRecord.setEnabled(False)

    def process_input(self, datablock):
        """
        Store data to file
        """
        self.dataavailable = True
        self.data = datablock

        # keep last impedance values for next EEG header file
        if self.data.recording_mode == RecordingMode.IMPEDANCE:
            self.last_impedance = copy.copy(datablock)
            return

        # check sample counter
        if self.next_samplecounter < -1:
            self.next_samplecounter = self.data.sample_channel[0][0] - 1  # first block after start
        samples = len(self.data.sample_channel[0])
        missing_precheck = self.data.sample_channel[0][-1] - (self.next_samplecounter + samples)
        self.marker_newseg = True  # always write new segment markers if samples are missing

        # counter not in expected range ?
        if missing_precheck != 0:
            sct = self.data.sample_channel[0]
            sct_check = np.append(self.next_samplecounter, sct)
            sctDiff = np.diff(sct_check) - 1
            sctBreak = np.nonzero(sctDiff)[0]
            missing_samples = np.sum(sctDiff)
            self.missing_interval += missing_samples
            self.missing_cumulated += missing_samples
            sctBreakDiff = np.array([sct_check[sctBreak + 1], sctDiff[sctBreak]])  # samplecounter / missing
            if time.process_time() - self.missing_timer > 30:
                self.missing_interval = missing_samples
            # print("samples missing = %i, interval = %i, cumulated = %i"%(missing_samples, self.missing_interval, self.missing_cumulated))
            error = "%d samples missing" % missing_samples
            if self.missing_interval > 2:
                self.send_event(
                    ModuleEvent(self._object_name, EventType.ERROR, info=error, severity=ErrorSeverity.NOTIFY))
                self.missing_interval = 0
                self.missing_cumulated = 0
            else:
                self.send_event(ModuleEvent(self._object_name, EventType.LOG, info=error))
            self.missing_timer = time.process_time()
        else:
            missing_samples = 0
            sctBreakDiff = np.array([[], []], dtype=np.int64)

        # set counter to the expected start sample number of next data block
        self.next_samplecounter = self.data.sample_channel[0, -1]

        if (self.data_file != 0) and not self.write_error:
            try:
                t = time.process_time()
                # convert data to float and write to data file
                d = datablock.eeg_channels.transpose()
                f = d.flatten().astype(np.float32)
                sizeof_item = f.dtype.itemsize  # item size in bytes
                write_items = len(f)  # number of items to write
                nitems = self.libc.fwrite(f.tostring(), sizeof_item, write_items, self.data_file)
                if nitems != write_items:
                    raise ModuleError(self._object_name, "Write to file %s failed" % self.file_name)
                # write marker
                # self._write_marker(self.data.markers, self.data.block_time, self.data.sample_channel[0,0])
                self.data.markers = self._write_marker(self.data.markers, self.data.block_time,
                                                       self.data.sample_channel[0, 0], sctBreakDiff)

                # update file sample counter
                self.samples_written += samples

                writetime = time.process_time() - t
                # print("Write file: %.0f ms / %d Bytes / QSize %d"%(writetime*1000.0, nitems, self._input_queue.qsize()))
            except Exception as e:
                self.write_error = True  # indicate write error
                self._thLock.release()  # release the thread lock because it is acquired by _close_recording()
                self._close_recording()  # stop recording
                self._thLock.acquire()
                # ToDo: notify application
                # self.send_event(ModuleEvent(self._object_name, EventType.ERROR,
                #                             str(e),
                #                             severity=ErrorSeverity.NOTIFY))

        # update the global sample counter missing value
        self.total_missing += missing_samples

    def _write_marker(self, markers, blockdate, blocksamplecounter, sctBreakDiff):
        """
        Write marker to file
        @param markers: list of marker objects (EEG_Marker)
        @param blockdate: datetime object with start time of the current data block
        @param blocksamplecounter: first sample counter value of the current data block
        @param sctBreakDiff: 2-dimensional numpy array with sample counter values at index 0
                             and number of missing samples at this counter at index 1
        """
        # insert "New Segment" marker as first marker and reset internal sample counters
        if self.marker_counter == 0:
            markers.insert(0, EEG_Marker(type="New Segment", date=True, position=blocksamplecounter))
            self.start_sample = blocksamplecounter
            self.total_missing = 0
            self.samples_written = 0
            self.start_time = blockdate

        # adjust marker positions and insert new segment markers if necessary
        new_segments = sctBreakDiff[:, :]
        ns_cumulatedMissing = 0
        output_markers = []

        for marker in markers:
            # are there a new segments before current marker position?
            if self.marker_newseg and new_segments.shape[1]:
                ns_position = new_segments[0, np.nonzero(new_segments[0] <= marker.position)[0]]
                ns_missing = new_segments[1, np.nonzero(new_segments[0] <= marker.position)[0]]
                # insert new segment markers
                for ns in range(ns_position.size):
                    ns_cumulatedMissing += ns_missing[ns]
                    mkr = EEG_Marker(type="New Segment", date=True, position=ns_position[ns])
                    output_markers.append(copy.deepcopy(mkr))
                    # adjust the new segment marker time
                    sampletime = (ns_position[ns] - self.start_sample) / self.params.sample_rate
                    mkr.dt = self.start_time + datetime.timedelta(seconds=sampletime)
                    # adjust position to file sample counter
                    mkr.position = ns_position[ns] - self.start_sample - self.total_missing - ns_cumulatedMissing + 1
                    # write new segment marker to file
                    self._writeMarkerToFile(mkr, blockdate)
                # remove handled new segments
                new_segments = new_segments[:, np.nonzero(new_segments[0] > marker.position)[0]]

            output_markers.append(copy.deepcopy(marker))
            # missing samples up to marker position
            miss = np.sum(sctBreakDiff[1, np.nonzero(sctBreakDiff[0] <= marker.position)[0]])
            # adjust position to file sample counter
            marker.position = marker.position - self.start_sample - self.total_missing - miss + 1
            # write marker to file
            self._writeMarkerToFile(marker, blockdate)

        # append disregarded new segment markers
        if self.marker_newseg and new_segments.shape[1]:
            ns_position = new_segments[0, :]
            ns_missing = new_segments[1, :]
            # insert new segment markers
            for ns in range(ns_position.size):
                ns_cumulatedMissing += ns_missing[ns]
                mkr = EEG_Marker(type="New Segment", date=True, position=ns_position[ns])
                output_markers.append(copy.deepcopy(mkr))
                # adjust the new segment marker time
                sampletime = (ns_position[ns] - self.start_sample) / self.params.sample_rate
                mkr.dt = self.start_time + datetime.timedelta(seconds=sampletime)
                # adjust position to file sample counter
                mkr.position = ns_position[ns] - self.start_sample - self.total_missing - ns_cumulatedMissing + 1
                # write new segment marker to file
                self._writeMarkerToFile(mkr, blockdate)

        return output_markers

    def _writeMarkerToFile(self, marker, blockdate):
        """
        Write single marker object to marker file
        @param marker: EEG_Marker object
        @param blockdate: datetime object with start time of the current data block
        """
        # consecutive marker number
        self.marker_counter += 1
        # Mkn=type,description,position,points,channel
        m = u"Mk%d=%s,%s,%d,%d,%d" % (self.marker_counter,
                                      marker.type,
                                      marker.description,
                                      marker.position,
                                      marker.points,
                                      marker.channel)
        if marker.date:
            try:
                m += marker.dt.strftime(",%Y%m%d%H%M%S%f")
            except:
                m += blockdate.strftime(",%Y%m%d%H%M%S%f")
        m += u"\n"
        self.marker_file.write(m.encode('utf-8'))
        self.marker_file.flush()

    def _close_recording(self):
        """
        Close all EEG files
        """
        self._thLock.acquire()
        if self.data_file != 0:
            try:
                self.libc.fclose(self.data_file)
                self.marker_file.close()
            except Exception as e:
                print(f"Failed to close recording files: {e}")
            self.data_file = 0
            self.data_file = 0
            # ToDo: self.online_cfg.set_recording_state(False)
        self._thLock.release()


    def process_output(self):
        if not self.dataavailable:
            return None
        self.dataavailable = False
        return self.data

    def process_stop(self):
        pass

    def process_update(self, params):
        pass


"""
Storage module online GUI.
"""


class _OnlineCfgPane:
    pass


"""
Storage module configuration GUI.
"""


class _ConfigurationPane:
    pass
