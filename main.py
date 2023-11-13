import sys
from PyQt6.QtWidgets import QApplication, QMainWindow

"""
Import GUI resources.
"""
from res import frmMain

"""
Import and instantiate recording modules.
"""
from amplifier import AMP_ActiChamp, Receiver


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
        Receiver()
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

        # create module chain (top = index 0, bottom = last index)
        self.defineModuleChain()

        # connect modules
        for idx_vertical in range(len(self.modules) - 1):
            self.modules[idx_vertical].add_receiver(self.modules[idx_vertical + 1])

        # get the top module
        self.topmodule = self.modules[0]

        # get the bottom module
        self.bottommodule = self.modules[-1]

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


    def defineModuleChain(self):
        """
        Instantiate and arrange module objects
        - Modules will be connected top -> down, starting with array index 0
        - Additional modules can be connected left -> right with tuples as list objects
        """
        self.modules = InstantiateModules()


"""
Utilities.
"""


def flatten(lst):
    """ Flatten a list containing lists or tuples
    """
    for elem in lst:
        if type(elem) in (tuple, list):
            for i in flatten(elem):
                yield i
        else:
            yield elem


def main(args):
    """
    Create and start up main application
    """
    app = QApplication(sys.argv)
    win = MainWindow()

    # win.showMaximized()
    win.show()

    app.exec()


if __name__ == "__main__":
    main(sys.argv)
