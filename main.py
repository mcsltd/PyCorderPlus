import re
import sys
from filecmp import cmp

from lxml import objectify, etree

from PyQt6.QtWidgets import QApplication, QMainWindow, QDialog, QWidget, QGridLayout
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


def load_preferences():
    """
    Load preferences from XML file
    :return:
    """

    configuration_dir = ""
    configuration_file = ""
    name_amplifier = ""
    log_dir = ""

    try:
        # preferences will be stored to user home directory
        homedir = QDir.home()
        appdir = "." + NAME_APPLICATION
        if not homedir.cd(appdir):
            return
        filename = homedir.absoluteFilePath("preferences.xml")

        # read XML file
        cfg = objectify.parse(filename)
        # check application and version
        app = cfg.xpath("//PyCorderPlus")
        if (len(app) == 0) or (app[0].get("version") is None):
            # configuration data not found
            return
            # check version
        version = app[0].get("version")
        if cmpver(version, VERSION, 2) > 0:
            # wrong version
            return

        # update preferences
        preferences = app[0].preferences
        configuration_dir = preferences.config_dir.pyval
        configuration_file = preferences.config_file.pyval
        name_amplifier = preferences.name_amplifier.pyval
        log_dir = preferences.log_dir.pyval

        return configuration_dir, configuration_file, name_amplifier, log_dir
    except Exception as err:

        return configuration_dir, configuration_file, name_amplifier, log_dir


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

    def __init__(self, config_dir, config_file, name_amplifier, log_dir):
        super().__init__()
        self.setupUi(self)

        # set config
        self.config_dir = config_dir
        self.config_file = config_file
        self.name_amplifier = name_amplifier
        self.log_dir = log_dir

        # menu actions
        self.actionQuit.triggered.connect(self.close)
        # button actions
        self.pushButtonConfiguration.clicked.connect(self.configurationClicked)

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

    def save_preferences(self):
        """
        Save preferences to XML file
        :return:
        """
        E = objectify.E
        preferences = E.preferences(E.config_dir(self.config_dir),
                                    E.config_file(self.config_file),
                                    E.name_amplifier(self.name_amplifier),
                                    E.log_dir(self.log_dir))
        root = E.PyCorderPlus(preferences, version=VERSION)

        # preferences will be stored to user home directory
        try:
            homedir = QDir.home()
            appdir = "." + NAME_APPLICATION
            if not homedir.cd(appdir):
                homedir.mkdir(appdir)
                homedir.cd(appdir)
            filename = homedir.absoluteFilePath("preferences.xml")
            etree.ElementTree(root).write(filename, pretty_print=True, encoding="UTF-8")
        except:
            pass

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

    a = map(fixup, re.findall("\d+|\w+", a))
    b = map(fixup, re.findall("\d+|\w+", b))
    return cmp(a[:n], b[:n])


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


NAME_APPLICATION = "PyCorderPlus"
VERSION = "0.0.0"


def main(args):
    """
    Create and start up main application
    """

    configuration_dir, \
        configuration_file, \
        name_amplifier, log_dir = load_preferences()

    app = QApplication(sys.argv)

    # win = MainWindow(
    #     config_dir=configuration_dir,
    #     config_file=configuration_file,
    #     name_amplifier=name_amplifier,
    #     log_dir=log_dir
    # )

    dlg = DlgAmpTypeSelection()
    dlg.show()
    # win.showMaximized()
    # win.show()
    app.exec()
    print(dlg)


if __name__ == "__main__":
    main(sys.argv)
