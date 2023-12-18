import re
import sys
import os

from lxml import objectify, etree

from PyQt6.QtWidgets import QApplication, QMainWindow, QDialog, QWidget, QGridLayout, QMessageBox
from PyQt6.QtCore import QDir

"""
Import GUI resources.
"""

from res import frmMain
from res import frmMainConfiguration
from res import frmDialogSelectAmp

"""
Import and instantiate recording modules.
"""
from amplifier import AMP_ActiChamp, Receiver
from montage import MNT_Recording
from display import DISP_Scope
from impedance import IMP_Display
from storage import StorageVision


def InstantiateModules():
    """
    Instantiate and arrange module objects.
    Modules will be connected top -> down, starting with array index 0.
    Additional modules can be connected left -> right with tuples as list objects.
    @return: list with instantiated module objects
    """
    # test modules for control amplifier
    modules = [
        AMP_ActiChamp(),
        MNT_Recording(),
        StorageVision(),
        IMP_Display(),
        DISP_Scope(instance=0),
        # Receiver()
    ]
    return modules


class MainWindow(QMainWindow, frmMain.Ui_MainWindow):
    """
    Application Main Window Class
    includes main menu, status bar and module handling
    """

    def __init__(self):

        super().__init__()
        self.setupUi(self)

        # menu actions
        self.actionQuit.triggered.connect(self.close)

        # button actions
        self.pushButtonConfiguration.clicked.connect(self.configurationClicked)

        # preferences
        self.application_name = "PyCorderPlus"
        self.name_amplifier = ""
        self.configuration_file = ""
        self.configuration_dir = ""
        self.log_dir = ""
        self.loadPreferences()
        self.recording_mode = -1
        # self.usageConfirmed = False

        # create module chain (top = index 0, bottom = last index)
        self.defineModuleChain()

        # connect modules
        for idx_vertical in range(len(self.modules) - 1):
            self.modules[idx_vertical].add_receiver(self.modules[idx_vertical + 1])

        # get the top module
        self.topmodule = self.modules[0]

        # get the bottom module
        self.bottommodule = self.modules[-1]

        # get signal panes for plot area
        self.horizontalLayout_SignalPane.removeItem(self.horizontalLayout_SignalPane.itemAt(0))
        for module in flatten(self.modules):
            pane = module.get_display_pane()
            if pane is not None:
                self.horizontalLayout_SignalPane.addWidget(pane)

        # initial module chain update (top module)
        self.topmodule.update_receivers()

        # insert online configuration panes
        position = 0
        for module in flatten(self.modules):
            module.main_object = self
            pane = module.get_online_configuration()
            if pane is not None:
                self.verticalLayout_OnlinePane.insertWidget(position, pane)
                position += 1

        # load configuration file
        # try to load the last configuration file
        try:
            if len(self.configuration_file) > 0:
                cfg = os.path.normpath(self.configuration_dir + '/' + self.configuration_file)
                self._loadConfiguration(cfg)
            else:
                self.defaultConfiguration()
        except:
            pass

        # update log text module info
        # self.updateModuleInfo()

        # update button states
        self.updateUI()

    def updateUI(self, isRunning=False):
        """ Update user interface to reflect the recording state
        """
        if isRunning:
            self.pushButtonConfiguration.setEnabled(False)
            self.actionLoad_Configuration.setEnabled(False)
            self.actionSave_Configuration.setEnabled(False)
            self.actionQuit.setEnabled(False)
            self.actionDefault_Configuration.setEnabled(False)
        else:
            self.pushButtonConfiguration.setEnabled(True)
            self.actionLoad_Configuration.setEnabled(True)
            self.actionSave_Configuration.setEnabled(True)
            self.actionQuit.setEnabled(True)
            self.actionDefault_Configuration.setEnabled(True)
            # self.statusWidget.resetUtilization()

    def defaultConfiguration(self):
        """
        Menu "Reset Configuration":
        Set default values for all modules
        """
        # reset all modules
        for module in flatten(self.modules):
            module.setDefault()

        # update module chain, starting from top module
        self.topmodule.update_receivers()

        # update status line
        # self.processEvent(ModuleEvent("Application", EventType.STATUS, info="default", status_field="Workspace"))

    def _loadConfiguration(self, filename):
        """
        Load module configuration from XML file
        @param filename: Full qualified XML file name
        """
        ok = True
        cfg = objectify.parse(filename)
        # check application and version
        app = cfg.xpath("//PyCorderPlus")

        if (len(app) == 0) or (app[0].get("version") == None):
            # configuration data not found
            # self.processEvent(ModuleEvent("Load Configuration", EventType.ERROR, "%s is not a valid PyCorder configuration file"%(filename), severity=1))
            ok = False

        if ok:
            version = app[0].get("version")
            if cmpver(version, __version__, 2) > 0:
                # wrong version
                # self.processEvent(ModuleEvent("Load Configuration", EventType.ERROR, "%s wrong version %s > %s" % (filename, version, __version__), severity=ErrorSeverity.NOTIFY))
                ok = False

                # setup modules from configuration file
                if ok:
                    for module in flatten(self.modules):
                        module.setXML(cfg)

                # update module chain, starting from top module
                self.topmodule.update_receivers()

                # update status line
                file_name, ext = os.path.splitext(os.path.split(filename)[1])
                # self.processEvent(ModuleEvent("Application", EventType.STATUS, info=file_name, status_field="Workspace"))

    def loadPreferences(self):
        """
        Load preferences from XML file
        :return:
        """
        try:
            # preferences will be stored to user home directory
            homedir = QDir.home()
            appdir = "." + self.application_name
            if not homedir.cd(appdir):
                # activating the device selection dialog
                dlg = DlgAmpTypeSelection()
                dlg.exec()
                self.name_amplifier = dlg.name_amp
                return
            filename = homedir.absoluteFilePath("preferences.xml")

            # read XML file
            cfg = objectify.parse(filename)
            # check application and version
            app = cfg.xpath("//PyCorderPlus")
            if (len(app) == 0) or (app[0].get("version") is None):
                # configuration data not found
                # activating the device selection dialog
                dlg = DlgAmpTypeSelection()
                dlg.exec()
                # set amplifier type
                self.name_amplifier = dlg.name_amp
                return
                # check version
            version = app[0].get("version")

            flag = cmpver(version, __version__, 2)
            c = 1
            if cmpver(version, __version__, 2) > 0:
                # wrong version
                # activating the device selection dialog
                dlg = DlgAmpTypeSelection()
                dlg.exec()
                # set amplifier type
                self.name_amplifier = dlg.name_amp
                return

            # update preferences
            preferences = app[0].preferences
            self.configuration_dir = preferences.config_dir.pyval
            self.configuration_file = preferences.config_file.pyval
            self.name_amplifier = preferences.name_amplifier.pyval
            self.log_dir = preferences.log_dir.pyval
        except:
            # activating the device selection dialog
            dlg = DlgAmpTypeSelection()
            dlg.exec()
            # set amplifier type
            self.name_amplifier = dlg.name_amp

    def savePreferences(self):
        """
        Save preferences to XML file
        :return:
        """
        E = objectify.E
        preferences = E.preferences(E.config_dir(self.configuration_dir),
                                    E.config_file(self.configuration_file),
                                    E.name_amplifier(self.name_amplifier),
                                    E.log_dir(self.log_dir))
        root = E.PyCorderPlus(preferences, version=__version__)

        # preferences will be stored to user home directory
        try:
            homedir = QDir.home()
            appdir = "." + self.application_name
            if not homedir.cd(appdir):
                homedir.mkdir(appdir)
                homedir.cd(appdir)
            filename = homedir.absoluteFilePath("preferences.xml")
            etree.ElementTree(root).write(filename, pretty_print=True, encoding="UTF-8")
        except:
            pass

    def closeEvent(self, event):
        """
        Application wants to close, prevent closing if recording to file is still active
        """
        if not self.topmodule.query("Stop"):
            event.ignore()
        else:
            self.topmodule.stop()
            self.savePreferences()
            # clean up modules
            for module in flatten(self.modules):
                module.terminate()
            # terminate remote control server
            # if self.RC != None:
            #     self.RC.terminate()
            event.accept()

    def configurationClicked(self):
        """ Configuration button clicked
        - Open configuration dialog and add configuration panes for each module in the
        module chain, if available
        """
        dlg = DlgConfiguration()
        for module in flatten(self.modules):
            pane = module.get_configuration_pane()
            if pane is not None:
                dlg.addPane(pane)
        ok = dlg.exec()
        # if ok:
        # self.saveConfiguration()

    def defineModuleChain(self):
        """
        Instantiate and arrange module objects
        - Modules will be connected top -> down, starting with array index 0
        - Additional modules can be connected left -> right with tuples as list objects
        """
        self.modules = InstantiateModules()


'''
------------------------------------------------------------
MAIN CONFIGURATION DIALOG
------------------------------------------------------------
'''


class DlgConfiguration(QDialog, frmMainConfiguration.Ui_frmConfiguration):
    ''' Module main configuration dialog
    All module configuration panes will go here
    '''

    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.panes = []

    def addPane(self, pane):
        ''' Insert new tab and add module configuration pane
        @param pane: module configuration pane (QFrame object)
        '''
        if pane is None:
            return
        currenttabs = len(self.panes)
        if currenttabs > 0:
            # add new tab
            tab = QWidget()
            tab.setObjectName("tab%d" % (currenttabs + 1))
            gridLayout = QGridLayout(tab)
            gridLayout.setObjectName("gridLayout%d" % (currenttabs + 1))
            self.tabWidget.addTab(tab, "")
        else:
            gridLayout = self.gridLayout1
            tab = self.tab1

        self.panes.append(pane)
        gridLayout.addWidget(pane)
        self.tabWidget.setTabText(self.tabWidget.indexOf(tab), pane.windowTitle())


"""
Utilities.
"""


def cmpver(a, b, n=3):
    ''' Compare two version numbers
    @param a: version number 1
    @param b: version number 2
    @param n: number of categories to compare
    @return:  -1 if a<b, 0 if a=b, 1 if a>b
    '''

    def fixup(i):
        try:
            return int(i)
        except ValueError:
            return i

    a = list(map(fixup, re.findall(r"\d+|\w+", a)))
    b = list(map(fixup, re.findall(r"\d+|\w+", b)))
    return (a[:n] > b[:n]) - (a[:n] < b[:n])


def flatten(lst):
    """ Flatten a list containing lists or tuples
    """
    for elem in lst:
        if type(elem) in (tuple, list):
            for i in flatten(elem):
                yield i
        else:
            yield elem


"""
Amplifier type selection window.
"""

from PyQt6.QtCore import QCoreApplication


class DlgAmpTypeSelection(frmDialogSelectAmp.Ui_SelectAmps, QDialog):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        # default selected amplifier
        self.radioButton.setChecked(True)
        self.name_amp = AMP_ActiChamp.__name__

        self.buttonBox.clicked.connect(self.set_name)

    def set_name(self):
        # set name
        if self.radioButton.isChecked():
            self.name_amp = AMP_ActiChamp.__name__

        # chose amplifier neorec
        if self.radioButton_2.isChecked():
            self.name_amp = "AMP_NeoRec"

    def closeEvent(self, event):
        res = QMessageBox.warning(
            self,
            "Warning!",
            "Amplifier type not selected. "
            "The ActiCHamp Plus amplifier will be automatically selected. "
            "Do you want to continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if res == QMessageBox.StandardButton.No:
            event.ignore()

        if res == QMessageBox.StandardButton.Yes:
            self.close()


NAME_APPLICATION = "PyCorderPlus"
__version__ = "0.0.0"


def main(args):
    """
    Create and start up main application
    """

    # configuration_dir, \
    #     configuration_file, \
    #     name_amplifier, log_dir = load_preferences()
    #
    # app = QApplication(sys.argv)
    # dlg = DlgAmpTypeSelection()
    # dlg.show()
    # app.exec()
    # del app
    #
    # name_amplifier = dlg.name_amp

    app = QApplication(sys.argv)
    win = MainWindow()
    win.showMaximized()
    app.exec()


if __name__ == "__main__":
    main(sys.argv)
