"""
Impedance Display Module

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
@date: $Date: 2013-06-07 19:21:40 +0200 (Fr, 07 Jun 2013) $
@version: 1.0

B{Revision:} $LastChangedRevision: 198 $
"""

from modbase import *

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt


class IMP_Display(ModuleBase):
    """
    Display impedance values
    """

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
        if self.impDialog != None:
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
                self.impDialog.setWindowFlags(Qt.ToolBarArea.Tool)
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
        # self.send_event(ModuleEvent(self._object_name, EventType.COMMAND, info="ImpColorRange",
        #                             cmd_value=val))

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
            # ToDo add emit signal: self.emit(Qt.SIGNAL('update(PyQt_PyObject)'), datablock)
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
        # E = objectify.E
        # cfg = E.IMP_Display(E.range_max(self.range_max),
        #                     E.show_values(self.show_values),
        #                     version=str(self.xmlVersion),
        #                     instance=str(self._instance),
        #                     module="impedance")
        # return cfg
        pass

    def setXML(self, xml):
        """
         Set module properties from XML configuration file
        @param xml: complete objectify XML configuration tree,
        module will search for matching values
        """
        # # search my configuration data
        # displays = xml.xpath("//IMP_Display[@module='impedance' and @instance='%i']" % self._instance)
        # if len(displays) == 0:
        #     # configuration data not found, leave everything unchanged
        #     return
        #
        #     # we should have only one display instance from this type
        # cfg = displays[0]
        #
        # # check version, has to be lower or equal than current version
        # version = cfg.get("version")
        # if (version is None) or (int(version) > self.xmlVersion):
        #     self.send_event(ModuleEvent(self._object_name, EventType.ERROR, "XML Configuration: wrong version"))
        #     return
        # version = int(version)
        #
        # # get the values
        # try:
        #     self.range_max = cfg.range_max.pyval
        #     self.show_values = cfg.show_values.pyval
        # except Exception as e:
        #     self.send_exception(e, severity=ErrorSeverity.NOTIFY)
        pass


if __name__ == "__main__":
    obj = IMP_Display()
    print(vars(obj))
