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
        self.default_path = ""          #: default data storage path
        self.default_prefix = ""        #: prefex for data files e.g. "EEG_"
        self.default_numbersize = 6     #: number of digits to append to file name
        self.default_autoname = False   #: create auto file name



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

