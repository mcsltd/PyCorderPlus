import collections
import re

from PyQt6.QtWidgets import QApplication, QMainWindow, QDialog, QWidget, QGridLayout, QMessageBox, QFileDialog, \
    QVBoxLayout, QLabel
from PyQt6.QtGui import QPixmap, QFont, QScreen
from PyQt6.QtCore import QDir, pyqtSignal, QThread, pyqtSlot
from PyQt6.QtBluetooth import QBluetoothLocalDevice

"""
Import GUI resources.
"""

from res import frmMain
from res import frmMainConfiguration
from res import frmDialogSelectAmp
from res import frmDlgNeoRecConnection
from res import frmMainStatusBar
from res import frmLogView

"""
Import and instantiate recording modules.
"""
from modbase import *

from amp_actichamp.amplifier_actichamp import AMP_ActiChamp
from amp_neorec.amplifier_neorec import AMP_NeoRec
from montage import MNT_Recording
from display import DISP_Scope
from impedance import IMP_Display
from storage import StorageVision
from trigger import TRG_Eeg
from filter import FLT_Eeg


def InstantiateModules(name_amp):
    """
    Instantiate and arrange module objects.
    Modules will be connected top -> down, starting with array index 0.
    Additional modules can be connected left -> right with tuples as list objects.
    @return: list with instantiated module objects
    """
    # test modules for control amplifier
    # modules = [
    #     # AMP_ActiChamp(),
    #     AMP_NeoRec(),
    #     # MNT_Recording(),
    #     # TRG_Eeg(),
    #     # StorageVision(),
    #     # FLT_Eeg(),
    #     # IMP_Display(),
    #     DISP_Scope(instance=0),
    #     # Receiver()
    # ]
    modules = []

    if name_amp == AMP_ActiChamp.__name__:
        modules = [
            AMP_ActiChamp(),
            MNT_Recording(),
            TRG_Eeg(),
            StorageVision(),
            FLT_Eeg(),
            IMP_Display(),
            DISP_Scope(instance=0),
            # Receiver()
        ]
    elif name_amp == AMP_NeoRec.__name__:
        modules = [
            AMP_NeoRec(),
            MNT_Recording(),
            TRG_Eeg(),
            StorageVision(),
            FLT_Eeg(),
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
    signal_parentevent = pyqtSignal("PyQt_PyObject")

    RESTART = 1

    def __init__(self):
        super().__init__()
        self.setupUi(self)

        # create status bar
        self.statusWidget = StatusBarWidget()
        self.statusBar().addPermanentWidget(self.statusWidget, 1)

        # menu actions
        self.actionQuit.triggered.connect(self.close)
        self.actionLoad_Configuration.triggered.connect(self.loadConfiguration)
        self.actionSave_Configuration.triggered.connect(self.saveConfiguration)
        self.actionDefault_Configuration.triggered.connect(self.defaultConfiguration)

        # button actions
        self.pushButtonConfiguration.clicked.connect(self.configurationClicked)

        # buttons action to select amplifier type
        self.actionActiCHamp_Plus.triggered.connect(self._restart)
        self.actionNeoRec.triggered.connect(self._restart)

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

        # get events from module chain top module
        self.topmodule.signal_event.connect(self.processEvent)
        # tell the top module to get events from us
        self.signal_parentevent.connect(self.topmodule.parent_event, Qt.ConnectionType.QueuedConnection)

        # get the bottom module
        self.bottommodule = self.modules[-1]

        # get name class Amplifier, if current topmodule is NeoRec than begin search device
        if self.topmodule.__class__.__name__ == AMP_NeoRec.__name__:
            self.stop_search = False
            self.actionNeoRec.setDisabled(True)

            # show a window while searching for an amplifier
            self.dlgConn = DlgConnectionNeoRec(self)
            self.dlgConn.signal_hide.connect(self.dlgConn._hide)
            self.dlgConn.signal_stop_search.connect(self.change_stop_search)

            # activate search NeoRec
            self.neorec_search()

            # self.topmodule.disconnect_signal.connect(self.neorec_search)
            # # actions to find a NeoRec amplifier
            # self.signal_search.connect(self.neorec_search)

        elif self.topmodule.__class__.__name__ == AMP_ActiChamp.__name__:
            self.actionActiCHamp_Plus.setDisabled(True)

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
            self.defaultConfiguration()

        # update log text module info
        # self.updateModuleInfo()

        # update button states
        self.updateUI()

    def change_stop_search(self, flag):
        self.stop_search = flag

    def neorec_search(self):
        """
        Launching the NeoRec amplifier search window on the network
        :return:
        """
        # show window search amplifier NeoRec
        self.dlgConn.show()

        # start searching for an amplifier
        conn = threading.Thread(target=self._search)
        conn.start()
        # conn.join()
        pass

    def _reconnect(self):
        """
        :return:
        """
        # show window search amplifier NeoRec
        self.dlgConn.show()

        # start searching for an amplifier
        conn = threading.Thread(target=self._search)
        conn.start()
        pass

    def _search(self):
        """
        Activation of the NeoRec amplifier search thread
        :return:
        """
        if self.check_bluetooth() == QBluetoothLocalDevice.HostMode.HostPoweredOff:
            self.dlgConn.set_text_bluetooth_on()

        # checking when the user turns on bluetooth
        res = self.check_bluetooth()
        while res != QBluetoothLocalDevice.HostMode.HostConnectable and not self.stop_search:
            res = self.check_bluetooth()

        if self.stop_search:
            return

        if res == QBluetoothLocalDevice.HostMode.HostConnectable:
            self.dlgConn.set_text_bluetooth_search()

        # amplifier search
        res = self.topmodule.connection()

        if res:
            self.topmodule.set_info()
            self.dlgConn.signal_hide.emit()

    def check_bluetooth(self):
        """
        Checks Bluetooth status
        :return:
        """
        res = QBluetoothLocalDevice().hostMode()
        return res

    def _restart(self):
        """
        Restart MainWindow for new type amplifier
        :return:
        """
        if self.name_amplifier == AMP_NeoRec.__name__:
            self.name_amplifier = AMP_ActiChamp.__name__
        elif self.name_amplifier == AMP_ActiChamp.__name__:
            self.name_amplifier = AMP_NeoRec.__name__
        self.close()
        QApplication.exit(self.RESTART)

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

    def loadConfiguration(self):
        """ Menu "Load Configuration ...":
        Load module configuration from XML file
        """
        dlg = QFileDialog()
        dlg.setFileMode(QFileDialog.FileMode.ExistingFile)
        dlg.setAcceptMode(QFileDialog.AcceptMode.AcceptOpen)
        dlg.setNameFilter("Configuration files (*.xml)")
        dlg.setDefaultSuffix("xml")
        if len(self.configuration_dir) > 0:
            dlg.setDirectory(self.configuration_dir)
        dlg.selectFile(self.configuration_file)
        if dlg.exec():
            try:
                files = dlg.selectedFiles()
                file_name = files[0]
                # load configuration from XML file
                self._loadConfiguration(file_name)
                # set preferences
                dir, fn = os.path.split(file_name)
                self.configuration_file = fn
                self.configuration_dir = dir
            except Exception as e:
                tb = GetExceptionTraceBack()[0]
                self.processEvent(
                    ModuleEvent(
                        "Load Configuration",
                        EventType.ERROR,
                        tb + " -> %s " % file_name + str(e),
                        severity=ErrorSeverity.NOTIFY
                    )
                )

    def _loadConfiguration(self, filename):
        """
        Load module configuration from XML file
        @param filename: Full qualified XML file name
        """
        ok = True
        cfg = objectify.parse(filename)

        # check application and version
        app = cfg.xpath("//PyCorderPlus")

        if (len(app) == 0) or (app[0].get("version") is None):
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

    def saveConfiguration(self):
        """
        Menu "Save Configuration ...":
        Save module configuration to XML file
        """
        dlg = QFileDialog()
        dlg.setFileMode(QFileDialog.FileMode.AnyFile)
        dlg.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        dlg.setNameFilter("Configuration files (*.xml)")
        dlg.setDefaultSuffix("xml")
        if len(self.configuration_dir) > 0:
            dlg.setDirectory(self.configuration_dir)
        dlg.selectFile(self.configuration_file)
        if dlg.exec():
            try:
                files = dlg.selectedFiles()
                file_name = files[0]
                # save configuration to XML
                self._saveConfiguration(file_name)
                # set preferences
                dir, fn = os.path.split(file_name)
                self.configuration_file = fn
                self.configuration_dir = dir
                # update status line
                fn, ext = os.path.splitext(os.path.split(file_name)[1])
                self.processEvent(ModuleEvent("Application",
                                              EventType.STATUS,
                                              info=fn,
                                              status_field="Workspace"))
            except Exception as e:
                tb = GetExceptionTraceBack()[0]
                self.processEvent(ModuleEvent("Save Configuration", EventType.ERROR,
                                              tb + " -> %s " % file_name + str(e),
                                              severity=ErrorSeverity.NOTIFY))

    def _saveConfiguration(self, filename):
        """ Save module configuration to XML file
        @param filename: Full qualified XML file name
        """
        E = objectify.E
        modules = E.modules()
        # get configuration from each connected module
        for module in flatten(self.modules):
            cfg = module.getXML()
            if cfg is not None:
                modules.append(cfg)
        # build complete configuration tree
        root = E.PyCorderPlus(modules, version=__version__)
        # write it to file
        etree.ElementTree(root).write(filename, pretty_print=True, encoding="UTF-8")

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

    def processEvent(self, event):
        """
        Process events from module chain
        @param event: ModuleEvent object
        Stop acquisition on errors with a severity > 1
        """
        # recording mode changed?
        if event.type == EventType.STATUS:
            if event.status_field == "Mode":
                self.recording_mode = event.info
                self.updateUI(isRunning=(event.info >= 0))
                # self.updateModuleInfo()

        # recording mode changed?
        if event.type == EventType.STATUS:
            if event.status_field == "Mode":
                self.recording_mode = event.info
                self.updateUI(isRunning=(event.info >= 0))
                self.updateModuleInfo()

        # look for errors
        if (event.type == EventType.ERROR) and (event.severity > 1):
            self.topmodule.stop(force=True)

    def closeEvent(self, event):
        """
        Application wants to close, prevent closing if recording to file is still active
        """

        if not self.topmodule.query("Stop"):
            event.ignore()
        else:
            self.topmodule.stop(force=True)

            if self.topmodule.__class__.__name__ == AMP_NeoRec.__name__:
                # Shutting down the API and disabling the BLE device
                self.topmodule.amp.close()
                # self.dlgConn.close()

            self.savePreferences()
            # clean up modules
            for module in flatten(self.modules):
                module.terminate()
            # terminate remote control server
            # if self.RC != None:
            #     self.RC.terminate()
            event.accept()

    def sendEvent(self, event):
        """
        Send an event to the top module event chain
        """
        self.signal_parentevent.emit(event)

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
        if ok:
            self.saveConfiguration()

    def defineModuleChain(self):
        """
        Instantiate and arrange module objects
        - Modules will be connected top -> down, starting with array index 0
        - Additional modules can be connected left -> right with tuples as list objects
        """
        self.modules = InstantiateModules(self.name_amplifier)

    def updateModuleInfo(self):
        """
        Update the module information in the log text
        and propagate it to all connected modules as status information
        :return:
        """
        # get module information
        self.statusWidget.moduleinfo = ""
        for module in flatten(self.modules):
            info = module.get_module_info()
            if info is not None:
                self.statusWidget.moduleinfo += module._object_name + "\n"
                self.statusWidget.moduleinfo += info
        if len(self.statusWidget.moduleinfo) > 0:
            self.statusWidget.moduleinfo += "\n\n"

        # propagate status info to all connected modules
        moduleinfo = "PyCorderPlus V" + __version__ + "\n\n"
        moduleinfo += self.statusWidget.moduleinfo
        msg = ModuleEvent("PyCorderPlus",
                          EventType.STATUS,
                          info=moduleinfo,
                          status_field="ModuleInfo")
        self.sendEvent(msg)


"""
NeoRec amplifier search window
"""


class DlgConnectionNeoRec(frmDlgNeoRecConnection.Ui_DlgNeoRecConnection, QDialog):
    signal_hide = pyqtSignal()
    signal_on = pyqtSignal()
    signal_stop_search = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setupUi(self)
        self.setWindowTitle("Connection to NeoRec")

        self.label.setPixmap(QPixmap("res/press_button.png"))

        # self.label_2.setText("Please check if Bluetooth and NeoRec amplifier are turned on.")
        # set text by default in label
        self.set_text_bluetooth_search()
        self.label_2.setFont(QFont("Ms Shell Dlg 2", 8))

        self.setFixedSize(self.size())
        # screen_size = QApplication.screen()[1].availableSize()
        # screen_size = parent.size()
        # x = (screen_size.width() - parent.width()) // 2
        # y = (screen_size.height() - parent.height()) // 2
        # self.move(x, y)

    def set_text_bluetooth_on(self):
        self.label_2.setText("Please turn on Bluetooth...")

    def set_text_bluetooth_search(self):
        self.label_2.setText("The Bluetooth network is searching for a NeoRec amplifier...")

    def _hide(self):
        self.hide()

    def closeEvent(self, event):
        result = QMessageBox.question(self, "Window close confirmation",
                                      "Are you sure you want to close the window and stop searching for NeoRec devices?",
                                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                      QMessageBox.StandardButton.No)
        if result == QMessageBox.StandardButton.Yes:
            self.signal_stop_search.emit(True)
            self.close()
        else:
            event.ignore()


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
    """ Compare two version numbers
    @param a: version number 1
    @param b: version number 2
    @param n: number of categories to compare
    @return:  -1 if a<b, 0 if a=b, 1 if a>b
    """

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


"""
Status Bar
"""


class StatusBarWidget(QWidget, frmMainStatusBar.Ui_frmStatusBar):
    """
    Main window status bar
    """

    def __init__(self):
        super().__init__()
        self.setupUi(self)

        # info label color and click
        self.labelInfo.setAutoFillBackground(True)
        self.labelInfo.mouseReleaseEvent = self.labelInfoClicked
        self.defaultBkColor = self.labelInfo.palette().color(self.labelInfo.backgroundRole())
        self.labelInfo.setText("Medical Computer Systems Ltd, PyCorderPlus V" + __version__)
        self.labelStatus_4.setAutoFillBackground(True)

        # log entries
        self.logFifo = collections.deque(maxlen=10000)
        self.lockError = False
        self.moduleinfo = ""

        # number of channels and reference channel names
        self.status_channels = ""
        self.status_reference = ""

        # utilization progressbar fifo
        self.resetUtilization()

    def resetUtilization(self):
        """
        Reset utilization parameters
        :return:
        """
        pass

    def updateUtilization(self, utilization):
        """
        Update the utilization progressbar
        :param utilization: percentage of utilization
        :return:
        """
        pass

    def updateEventStatus(self, event):
        """
        Update status info field and put events into the log fifo
        :param event: ModuleEvent object
        :return:
        """

        # put events into log fifo
        if event.type != EventType.MESSAGE:
            self.logFifo.append(event)

    def showLogEntries(self):
        """
        Show the event log content
        :return:
        """
        pass

    def getLogText(self):
        """
        Get the log entries as plain text
        :return:
        """
        pass

    def labelInfoClicked(self, mouse_event):
        """
        Mouse click into info label
        Show the event log content
        :param mouse_event:
        :return:
        """

    def resetErrorState(self):
        """
        Reset error lock and info display
        :return:
        """
        pass


"""
Log Entry Dialog
"""


class DlgLogView(QDialog, frmLogView.Ui_frmLogView):
    """
    Show all log entries as plain text
    """

    def __init__(self, *args):
        super().__init__(*args)
        self.setupUi(self)

    def setLogEntry(self, entry):
        self.labelView.setPlainText(entry)


NAME_APPLICATION = "PyCorderPlus"
__version__ = "0.0.0"


def main(args):
    """
    Create and start up main application
    """

    res = MainWindow.RESTART
    while res == MainWindow.RESTART:
        app = QApplication(sys.argv)
        win = MainWindow()
        win.showMaximized()
        res = app.exec()

        del app
        del win


if __name__ == "__main__":
    main(sys.argv)
