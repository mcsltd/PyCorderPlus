"""
Storage Module for Vision EEG file format

PyCorderPlus ActiChamp Recorder

------------------------------------------------------------

Copyright (C) 2010, Brain Products GmbH, Gilching
Copyright (C) 2024, Medical Computer Systems Ltd


This file is part of PyCorderPlus
"""
import time

import platform
import ctypes as ct

from PyQt6.QtWidgets import QMessageBox, QFileDialog, QFrame
from PyQt6.QtCore import QDir, QFile, Qt, QByteArray
from PyQt6.QtGui import QPalette, QColor, QIntValidator, QDoubleValidator

from modbase import *

from res import frmStorageVisionOnline
from res import frmStorageVisionConfig

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

        # Amplifier name
        self.name_device = "actiCHamp"

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
        self.missing_timer = time.process_time()
        self.missing_interval = 0
        self.missing_cumulated = 0
        self.next_samplecounter = -2
        # enable recording button
        if self.params.recording_mode != RecordingMode.IMPEDANCE:
            self.online_cfg.pushButtonRecord.setEnabled(True)
        else:
            self.online_cfg.pushButtonRecord.setEnabled(False)

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
                    ModuleEvent(self._object_name, EventType.ERROR, info=error, severity=ErrorSeverity.NOTIFY)
                )
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
                # notify application
                self.send_event(ModuleEvent(self._object_name, EventType.ERROR,
                                            str(e),
                                            severity=ErrorSeverity.NOTIFY))

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
        self.marker_file.write(m)
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
            self.online_cfg.set_recording_state(False)
        self._thLock.release()

    def process_output(self):
        if not self.dataavailable:
            return None
        self.dataavailable = False
        return self.data

    def process_stop(self):
        """
        Stop data acquisition
        """
        self._close_recording()
        # disable recording button
        self.online_cfg.pushButtonRecord.setEnabled(False)

    def process_update(self, params):
        """
        Calculate recording parameters for updated channels
        """
        # copy settings
        self.params = copy.copy(params)
        if params.recording_mode == RecordingMode.IMPEDANCE:
            self.last_impedance_config = copy.copy(params)
        numchannels = len(params.channel_properties)
        self.samples_per_second = numchannels * params.sample_rate
        return params

    def process_query(self, command):
        """ Evaluate query commands.
        @param command: command string
        @return: True if user confirms to stop recording to file
        """
        if self.data_file == 0:
            return True
        if command == "Stop":
            ret = QMessageBox.question(
                None,
                "PyCorderPlus",
                "Stop Recording?",
                QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel, QMessageBox.StandardButton.Cancel
            )
            if ret != QMessageBox.StandardButton.Ok:
                return False
        if command == "RemoteStop":
            return False
        return True

    def process_event(self, event):
        """ Handle events from attached receivers
        @param event: ModuleEvent
        """
        # Get info of all connected modules for header file comment
        if event.type == EventType.STATUS and event.status_field == "ModuleInfo":
            self.moduledescription = event.info

        # handle remote commands
        if event.type == EventType.COMMAND:
            # check for start, cmd_value contains the EEG filename without extension
            if event.info == "StartSaving":
                # quit if recording is already active or if we are in impendance mode
                if self.data_file != 0 or self.params.recording_mode == RecordingMode.IMPEDANCE:
                    return
                try:
                    self.file_name = self._get_unique_filename(event.cmd_value)
                    if self._prepare_recording():
                        self.online_cfg.set_filename(os.path.split(self.file_name)[0],
                                                     os.path.split(self.file_name)[1])
                except Exception as e:
                    # self.send_exception(e, severity=ErrorSeverity.STOP)
                    pass

            # check for stop
            if event.info == "StopSaving":
                self._close_recording()

            if event.status_field == "ChangeAmp":
                self.name_device = event.info

    def _prepare_recording(self):
        """ Create and prepare EEG data, header and marker file
        """
        if self.file_name is not None:
            # check for minimum available disk space
            if self.get_free_space(self.file_name)[0] < 0:
                # self.online_cfg.set_recording_state(False)
                path = os.path.split(self.file_name)[0]
                QMessageBox.critical(None, "Storage",
                                     "out of disk space (%.2fGB) on %s" % (self.min_disk_space, path))
                return False

            fname, ext = os.path.splitext(self.file_name)
            headername = fname + ".vhdr"
            markername = fname + ".vmrk"
            crlf = "\n"

            # create EEG header file
            try:
                self.header_file = open(headername, "w")
                # ToDo: add data from which device the data is being recorded
                h = "Brain Vision Data Exchange Header File Version 1.0" + crlf
                h += f"; Data created by the {self.name_device} PyCorderPlus" + crlf + crlf

                # common infos.
                h += "[Common Infos]" + crlf
                h += "Codepage=UTF-8" + crlf
                h += "DataFile=" + os.path.split(self.file_name)[1] + crlf
                h += "MarkerFile=" + os.path.split(markername)[1] + crlf
                h += "DataFormat=BINARY" + crlf
                h += "; Data orientation: MULTIPLEXED=ch1,pt1, ch2,pt1 ..." + crlf
                h += "DataOrientation=MULTIPLEXED" + crlf
                h += "NumberOfChannels=%d" % (len(self.params.channel_properties)) + crlf
                h += "; Sampling interval in microseconds" + crlf
                usSR = 1000000.0 / self.params.sample_rate
                if int(usSR) == usSR:
                    h += "SamplingInterval=%d" % usSR + crlf
                else:
                    h += "SamplingInterval=%.5f" % usSR + crlf
                h += crlf
                h += "[Binary Infos]" + crlf
                h += "BinaryFormat=IEEE_FLOAT_32" + crlf
                h += crlf
                h += "[Channel Infos]" + crlf
                h += "; Each entry: Ch<Channel number>=<Name>,<Reference channel name>," + crlf
                h += "; <Scaling factor in \"Unit\">,<Unit>, Future extensions.." + crlf
                h += "; Fields are delimited by commas, some fields might be omitted (empty)." + crlf
                h += "; Commas in channel names are coded as \"\\1\"." + crlf

                # channel configuration
                ch = 1
                for channel in self.params.channel_properties:
                    lbl = channel.name.replace(",", "\\1")
                    refLabel = channel.refname.replace(",", "\\1")
                    if len(channel.unit) > 0:
                        unit = channel.unit
                    else:
                        unit = "µV"
                    h += "Ch%d=%s,%s,1.0,%s" % (ch, lbl, refLabel, unit) + crlf
                    ch += 1

                # recorder info
                h += crlf
                h += "[Comment]" + crlf
                h += self.moduledescription
                h += crlf

                # reference channel names
                h += "Reference channel: %s" % self.params.ref_channel_name + crlf

                # impedance values if available
                if self.last_impedance is not None:
                    h += crlf
                    h += "Impedance [KOhm] at %s (recording started at %s)" % (
                        self.last_impedance.block_time.strftime("%H:%M:%S"),
                        datetime.datetime.now().strftime("%H:%M:%S")) + crlf

                    # impedance for eeg electrodes
                    gndImpedance = None
                    for idx, ch in enumerate(self.last_impedance_config.channel_properties):
                        if not ((ch.inputgroup == ChannelGroup.EEG) and (ch.enable or ch.isReference)):
                            continue
                        valD = ""
                        valR = ""
                        # impedance value for data electrode available?
                        if self.last_impedance_config.eeg_channels[idx, ImpedanceIndex.DATA] == 1:
                            valD = self._getImpedanceValueText(
                                self.last_impedance.eeg_channels[idx, ImpedanceIndex.DATA])

                        # impedance value for reference electrode available?
                        if self.last_impedance_config.eeg_channels[idx, ImpedanceIndex.REF] == 1:
                            valR = self._getImpedanceValueText(
                                self.last_impedance.eeg_channels[idx, ImpedanceIndex.REF])

                        if len(valD) and len(valR):
                            impedanceText = "+%s / -%s" % (valD, valR)
                        else:
                            impedanceText = valD

                        # take the first available GND impedance
                        if gndImpedance is None and self.last_impedance_config.eeg_channels[
                            idx, ImpedanceIndex.GND] == 1:
                            gndImpedance = self.last_impedance.eeg_channels[idx, ImpedanceIndex.GND]

                        if len(impedanceText) > 0:
                            h += "%3d %s: %s" % (ch.input, ch.name, impedanceText) + crlf

                    # GND electrode
                    if gndImpedance is not None:
                        val = self._getImpedanceValueText(gndImpedance)
                        h += "GND: %s" % val + crlf

                self.header_file.write(h)
                self.header_file.close()

            except Exception as e:
                raise ModuleError(self._object_name, "failed to create %s\n%s" % (headername, str(e)))

            # create EEG marker file
            try:
                self.marker_file = open(markername, "w")
                h = "Brain Vision Data Exchange Marker File, Version 1.0" + crlf
                h += crlf
                # common infos.
                h += "[Common Infos]" + crlf
                h += "Codepage=UTF-8" + crlf
                h += "DataFile=" + os.path.split(self.file_name)[1] + crlf
                h += crlf
                # Marker infos.
                h += "[Marker Infos]" + crlf
                h += "; Each entry: Mk<Marker number>=<Type>,<Description>,<Position in data points>," + crlf
                h += "; <Size in data points>, <Channel number (0 = marker is related to all channels)>" + crlf
                h += "; Fields are delimited by commas, some fields might be omitted (empty)." + crlf
                h += "; Commas in type or description text are coded as \"\\1\"." + crlf

                self.marker_file.write(h)
                self.marker_file.flush()
                self.marker_counter = 0
                self.marker_newseg = False

            except Exception as e:
                self.header_file.close()
                raise ModuleError(self._object_name, "failed to create %s\n%s" % (markername, str(e)))

            # create EEG data file
            try:
                self._thLock.acquire()
                self.data_file = self.libc._wfopen(self.file_name, u"wb")
                self.write_error = False
            except IOError as e:
                self.header_file.close()
                self.marker_file.close()
                raise ModuleError(self._object_name, "failed to create %s" % self.file_name)
            finally:
                self._thLock.release()

            # show recording state
            self.online_cfg.set_recording_state(True)

            # send status to application
            self.send_event(ModuleEvent(self._object_name,
                                        EventType.STATUS,
                                        info=self.file_name,
                                        status_field="Storage"))
        return True

    def _get_unique_filename(self, filename):
        """ if file already exists, append the next free number to the filename
        @param filename: filename without path and extension, has to be unicode
        @return: fully qualified path and filename for the next, not yet existing eeg file
        """
        # get rid of path and extension from filename
        fnx = os.path.split(filename)[1]
        fn = os.path.splitext(fnx)[0]
        # take path from configuration
        pn = self.default_path
        eegdir = QDir(pn)
        if not eegdir.exists():
            raise Exception("path '%s' does not exist" % pn)
        eegdir.setFilter(QDir.Filter.Files)
        eegdir.setNameFilters(["%s*.eeg" % fn])
        allfiles = eegdir.entryList()
        eegdir.setNameFilters(["%s_*.eeg" % fn])
        numberedfiles = eegdir.entryList()

        if allfiles.count() == 0:
            return os.path.join(pn, filename + ".eeg")

        # extract numbers
        numberedfiles.replaceInStrings(".eeg", "", Qt.CaseSensitivity.CaseInsensitive)
        numberedfiles.replaceInStrings(fn + "_", "", Qt.CaseSensitivity.CaseInsensitive)
        numbers = []
        for f in numberedfiles:
            num, ok = f.toInt()
            if ok:
                numbers.append(num)
        if len(numbers) > 0:
            # get the highest number
            numbers.sort()
            fnum = numbers[-1] + 1
        else:
            fnum = 1
        newfilename = os.path.join(pn, "%s_%d.eeg" % (filename, fnum))

        # verify that the file is not yet existing
        if QFile.exists(newfilename):
            raise Exception("auto numbering failed, '%s' already exists" % newfilename)

        return newfilename

    def get_free_space(self, path):
        """
        Get the total and free available disk space
        @param path: complete data file path
        @return: tuple folder/drive free and total space (in bytes)
        """
        if platform.system() == 'Windows':
            folder = os.path.splitdrive(path)[0]
            free_bytes = ct.c_ulonglong(0)
            total_bytes = ct.c_ulonglong(0)
            ct.windll.kernel32.GetDiskFreeSpaceExW(ct.c_wchar_p(folder),
                                                   ct.pointer(free_bytes),
                                                   ct.pointer(total_bytes),
                                                   None)
            free = free_bytes.value - self.min_disk_space * 1024 ** 3
            return free, total_bytes.value
        else:
            folder = os.path.split(path)[0]
            diskinfo = os.statvfs(folder)
            total_bytes = diskinfo.f_blocks * diskinfo.f_bsize
            free = (diskinfo.f_bavail * diskinfo.f_bsize) - self.min_disk_space * 1024 ** 3
            return free, total_bytes

    def _getImpedanceValueText(self, impedance):
        """
        evaluate the impedance value and get the text for the header file
        @return: text
        """
        if impedance > CHAMP_IMP_INVALID:
            valuetext = "Disconnected!"
        else:
            v = impedance / 1000.0
            if impedance == CHAMP_IMP_INVALID:
                valuetext = "Out of Range!"
            else:
                valuetext = "%.0f" % v
        return valuetext

    def set_recording_file(self):
        """
        SIGNAL recording button clicked: Select data file and prepare recording
        """
        try:
            # is recording active?
            if self.data_file != 0:
                if self.process_query("Stop"):
                    self._close_recording()
                else:
                    self.online_cfg.set_recording_state(True)
            elif self.params.recording_mode != RecordingMode.IMPEDANCE:
                dlg = QFileDialog()
                dlg.setFileMode(QFileDialog.FileMode.AnyFile)
                dlg.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
                dlg.setDefaultSuffix("eeg")
                if len(self.default_path) > 0:
                    dlg.setDirectory(self.default_path)
                dlg.selectFile(self._get_auto_filename(dlg.directory()))
                namefilters = ["EEG files (*.eeg)"]
                if self.default_autoname and (len(self.default_prefix) > 0):
                    namefilters.insert(0, "EEG files (%s*.eeg)" % self.default_prefix)
                dlg.setNameFilters(namefilters)
                ok = False
                if dlg.exec():
                    ok = True
                    files = dlg.selectedFiles()
                    pf = files[0]
                    # strip leading/trailing spaces from file name
                    pn, fn = os.path.split(pf)
                    self.file_name = os.path.join(pn, fn.strip())
                    # append the extension .eeg, if not already present
                    if not self.file_name.lower().endswith(".eeg"):
                        self.file_name += ".eeg"
                    # additional check for existing files, possibly we have modified the file name
                    if self.file_name.replace("\\", "/") != pf.replace("\\", "/") and os.path.exists(self.file_name):
                        ret = QMessageBox.warning(None, "Save As",
                                                  "%s already exists.\nDo you want to replace it?" % (
                                                      os.path.split(self.file_name)[1]),
                                                  QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.No,
                                                  QMessageBox.StandardButton.No)
                        if ret != QMessageBox.StandardButton.Ok:
                            ok = False

                    if ok and self._prepare_recording():
                        self.online_cfg.set_filename(os.path.split(self.file_name)[0],
                                                     os.path.split(self.file_name)[1])
                if not ok:
                    self.online_cfg.set_recording_state(False)
        except Exception as e:
            self.send_exception(e, severity=ErrorSeverity.STOP)

    def _get_auto_filename(self, searchdir):
        """ Search for next auto file number
        @param searchdir: Qt.Qdir
        @return: the generated filename
        """
        if not self.default_autoname:
            return ""
        numberstring = "?"
        for n in range(1, self.default_numbersize):
            numberstring += "?"
        searchdir.setNameFilters(["%s%s.eeg" % (self.default_prefix, numberstring)])
        searchdir.setFilter(QDir.Filter.Files)
        flist = searchdir.entryList()
        # extract numbers

        # flist.replaceInStrings(".eeg", "", Qt.Qt.CaseInsensitive)
        flist = [s.replace(".eeg", "") for s in flist]

        if len(self.default_prefix) > 0:
            # flist.replaceInStrings(self.default_prefix, "", Qt.Qt.CaseInsensitive)
            flist = [s.replace(self.default_prefix, "") for s in flist]
        flist, list(flist)
        numbers = []
        for f in flist:
            num = int(f)
            if num < 10 ** self.default_numbersize - 1:
                numbers.append(num)
        if len(numbers) > 0:
            # get the highest number
            numbers.sort()
            fn = numbers[-1] + 1
        else:
            fn = 1
        name = "%s%0*d.eeg" % (self.default_prefix, self.default_numbersize, fn)
        return name

    def get_online_configuration(self):
        ''' Get the online configuration pane
        '''
        # create online configuration pane
        self.online_cfg = _OnlineCfgPane(self)
        # connect recording button
        self.online_cfg.pushButtonRecord.clicked.connect(self.set_recording_file)
        return self.online_cfg

    def get_configuration_pane(self):
        """ Get the configuration pane if available
        - Qt widgets are not reusable, so we have to create it every time
        """
        config = _ConfigurationPane(self)
        return config

    def getXML(self):
        ''' Get module properties for XML configuration file
        @return: objectify XML element::
            e.g.
            <StorageVision instance="0" version="1">
                <path>D:\EEG</path>
                ...
            </StorageVision>
        '''
        E = objectify.E
        cfg = E.StorageVision(E.d_path(self.default_path),
                              E.d_autoname(self.default_autoname),
                              E.d_prefix(self.default_prefix),
                              E.d_numbersize(self.default_numbersize),
                              E.mindiskspace(self.min_disk_space),
                              version=str(self.xmlVersion),
                              instance=str(self._instance),
                              module="storage")
        return cfg

    def setXML(self, xml):
        ''' Set module properties from XML configuration file
        @param xml: complete objectify XML configuration tree,
        module will search for matching values
        '''
        # search my configuration data
        storages = xml.xpath("//StorageVision[@module='storage' and @instance='%i']" % self._instance)
        if len(storages) == 0:
            # configuration data not found, leave everything unchanged
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
            self.default_path = cfg.d_path.pyval
            self.default_autoname = cfg.d_autoname.pyval
            self.default_prefix = cfg.d_prefix.pyval
            self.default_numbersize = cfg.d_numbersize.pyval
            if version > 1:
                self.min_disk_space = cfg.mindiskspace.pyval
            else:
                self.min_disk_space = 1.0

        except Exception as e:
            self.send_exception(e, severity=ErrorSeverity.NOTIFY)
            pass

    def check_free_space(self, freespace):
        """ Check for a minimum available free space
        - If disk runs out of space during recording, stop recording
        @param freespace: available space in bytes
        @return: False if disk is out of space
        """
        if freespace > 0:
            return True
        if self.data_file != 0:
            # stop recording
            self.write_error = True
            self._close_recording()
            # notify application
            self.send_event(ModuleEvent(self._object_name, EventType.ERROR,
                                        "out of disk space (<%.2fGB), recording stopped" % self.min_disk_space,
                                        severity=ErrorSeverity.NOTIFY))
        return False


"""
Storage module online GUI.
"""


class _OnlineCfgPane(QFrame, frmStorageVisionOnline.Ui_frmStorageVisionOnline):
    """
    Vision Storage Module online configuration pane
    """

    def __init__(self, module, *args):
        """ Constructor
        @param module: parent module
        """
        super().__init__()
        self.setupUi(self)
        self.module = module

        # set default values
        self.pushButtonRecord.setEnabled(False)
        self.set_recording_state(False)

        self.filename = ""
        self.pathname = ""

        # start display update timer
        self.startTimer(1000)

    def set_filename(self, path, file, time=0):
        """ Show pathname, filename and optional recording time
        @param path: recording path name
        @param file: recording file name
        @param time: time of data written to file in seconds
        """
        self.pathname = path
        self.filename = file
        if time > 0:
            days, hours, minutes, seconds = self.get_DHMS(time)
            if days == 0:
                timestring = "  %02d:%02d:%02d [h:m:s]" % (hours, minutes, seconds)
            else:
                timestring = "  %d:%02d:%02d:%02d [d:h:m:s]" % (days, hours, minutes, seconds)
        else:
            timestring = ""
        self.lineEditPath.setText(path)
        self.lineEditFile.setText(file + timestring)

    def timerEvent(self, e):
        """ Display update timer event
        """
        # calculate available disk size
        path = self.lineEditPath.text()
        if len(path) > 0:
            free, total = self.module.get_free_space(path)
            if total > 0 and free > 0:
                ratio = int(free * 100.0 / total)
            else:
                ratio = 0
            self.progressBar.setValue(ratio)
            self.module.check_free_space(free)
        else:
            free = total = 0
            self.progressBar.setValue(0)

        # estimate required size in Byte per second
        bps = self.module.samples_per_second * np.zeros(1, np.float32).dtype.itemsize
        if bps > 0:
            if free > 0:
                seconds = free / bps
            else:
                seconds = 0
            # Get the days, hours, minutes:
            days, hours, minutes, seconds = self.get_DHMS(seconds)
            self.lineEditDiskSpace.setText("%d:%02d:%02d" % (days, hours, minutes))
        else:
            self.lineEditDiskSpace.setText("--:--:--")

        # calculate the time of data written to file
        if (self.module.params is not None) and (self.module.params.sample_rate > 0):
            seconds = self.module.samples_written / self.module.params.sample_rate
            self.set_filename(self.pathname, self.filename, time=seconds)

    def get_DHMS(self, seconds):
        """ Get days, hours, minutes and seconds from seconds
        @param seconds: total number of seconds
        @return: tuple (Days, Hours, Minutes, Seconds)
        """
        MINUTE = 60
        HOUR = MINUTE * 60
        DAY = HOUR * 24
        days = int(seconds / DAY)
        hours = int((seconds % DAY) / HOUR)
        minutes = int((seconds % HOUR) / MINUTE)
        seconds = int(seconds % MINUTE)
        return days, hours, minutes, seconds

    def set_recording_state(self, on):
        """
        Update display elements to reflect the recording state
        """
        if on:
            self.progressBar.setEnabled(True)
            palette = self.lineEditFile.palette()
            if self.module.write_error:
                palette.setColor(QPalette.ColorRole.Base, Qt.GlobalColor.red)
            else:
                palette.setColor(QPalette.ColorRole.Base, Qt.GlobalColor.green)
            self.lineEditFile.setPalette(palette)
            self.pushButtonRecord.setChecked(True)
            self.pushButtonRecord.setText("Stop Recording")
        else:
            self.progressBar.setEnabled(False)
            palette = self.lineEditFile.palette()
            if self.module.write_error:
                palette.setColor(QPalette.ColorRole.Base, Qt.GlobalColor.red)
            else:
                palette.setColor(QPalette.ColorRole.Base, QColor(240, 240, 240))
            self.lineEditFile.setPalette(palette)
            self.pushButtonRecord.setChecked(False)
            self.pushButtonRecord.setText("Start Recording")


"""
Storage module configuration GUI.
"""


class _ConfigurationPane(QFrame, frmStorageVisionConfig.Ui_frmStorageVisionConfig):
    """
    Vision Storage configuration pane
    """

    def __init__(self, storage, *args):
        """ Constructor
        @param storage: parent module
        """
        super().__init__()
        self.setupUi(self)

        # set validators
        validator = QIntValidator(1, 50, self)
        self.lineEditCounterSize.setValidator(validator)

        validator2 = QDoubleValidator(0.01, 500.0, 2, self)
        self.lineEditSpace.setValidator(validator2)

        # setup content
        self.storage = storage

        self.lineEditFolder.setText(storage.default_path)
        self.lineEditPrefix.setText(storage.default_prefix)
        self.lineEditCounterSize.setText(str(storage.default_numbersize))
        self.checkBoxAutoFile.setChecked(storage.default_autoname)
        self.lineEditSpace.setText(str(storage.min_disk_space))
        self._showExample()

        # actions
        self.lineEditFolder.editingFinished.connect(self._contentChanged)
        self.lineEditPrefix.editingFinished.connect(self._contentChanged)
        self.lineEditCounterSize.editingFinished.connect(self._contentChanged)
        self.checkBoxAutoFile.clicked.connect(self._contentChanged)
        self.pushButtonBrowse.clicked.connect(self._browse)
        self.lineEditSpace.editingFinished.connect(self._contentChanged)

    def _contentChanged(self):
        """
        Update parent object vars
        """
        self.storage.default_path = self.lineEditFolder.displayText()
        self.storage.default_prefix = self.lineEditPrefix.displayText().lstrip()
        self.lineEditPrefix.setText(self.storage.default_prefix)
        self.storage.default_numbersize = int(self.lineEditCounterSize.displayText())
        self.storage.default_autoname = self.checkBoxAutoFile.isChecked()
        self.storage.min_disk_space = float(self.lineEditSpace.displayText())
        self._showExample()

    def _browse(self):
        """
        Browse for the default data folder
        """
        dlg = QFileDialog()
        dlg.setFileMode(QFileDialog.FileMode.Directory)
        dlg.setOption(QFileDialog.Option.ShowDirsOnly)
        dlg.setAcceptMode(QFileDialog.AcceptMode.AcceptOpen)
        if dlg.exec():
            files = dlg.selectedFiles()
            file_name = files[0]
            self.lineEditFolder.setText(file_name)
            self._contentChanged()

    def _showExample(self):
        """
        Show auto file name example
        """
        example = "%s%0*d.eeg" % (self.storage.default_prefix, self.storage.default_numbersize, 1)
        self.labelExample.setText(example)
