import sys
from PyQt6.QtWidgets import QApplication, QMainWindow

"""
Import GUI resources
"""
from res import frmMain


class MainWindow(QMainWindow, frmMain.Ui_MainWindow):
    """
    Application Main Window Class
    includes main menu, status bar and module handling
    """
    def __init__(self):
        super().__init__()

        self.setupUi(self)


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


