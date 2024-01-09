# Form implementation generated from reading ui file '.\res\frmMain.ui'
#
# Created by: PyQt6 UI code generator 6.6.0
#
# WARNING: Any manual changes made to this file will be lost when pyuic6 is
# run again.  Do not edit this file unless you know what you are doing.


from importlib.resources import path
from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(862, 604)
        icon = QtGui.QIcon()
        with path("res", "PyCorderPlus.ico") as f_path:
            icon.addPixmap(QtGui.QPixmap(str(f_path)), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        MainWindow.setWindowIcon(icon)
        self.centralwidget = QtWidgets.QWidget(parent=MainWindow)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.centralwidget.sizePolicy().hasHeightForWidth())
        self.centralwidget.setSizePolicy(sizePolicy)
        self.centralwidget.setObjectName("centralwidget")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.centralwidget)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.horizontalLayout_SignalPane = QtWidgets.QHBoxLayout()
        self.horizontalLayout_SignalPane.setContentsMargins(-1, 5, -1, -1)
        self.horizontalLayout_SignalPane.setObjectName("horizontalLayout_SignalPane")
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_SignalPane.addItem(spacerItem)
        self.horizontalLayout.addLayout(self.horizontalLayout_SignalPane)
        self.scrollArea = QtWidgets.QScrollArea(parent=self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.scrollArea.sizePolicy().hasHeightForWidth())
        self.scrollArea.setSizePolicy(sizePolicy)
        self.scrollArea.setMinimumSize(QtCore.QSize(300, 0))
        self.scrollArea.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.scrollArea.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scrollArea.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setObjectName("scrollArea")
        self.scrollAreaWidgetContents = QtWidgets.QWidget()
        self.scrollAreaWidgetContents.setGeometry(QtCore.QRect(0, 0, 300, 532))
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.scrollAreaWidgetContents.sizePolicy().hasHeightForWidth())
        self.scrollAreaWidgetContents.setSizePolicy(sizePolicy)
        self.scrollAreaWidgetContents.setMinimumSize(QtCore.QSize(300, 0))
        self.scrollAreaWidgetContents.setObjectName("scrollAreaWidgetContents")
        self.verticalLayout_OnlinePane = QtWidgets.QVBoxLayout(self.scrollAreaWidgetContents)
        self.verticalLayout_OnlinePane.setObjectName("verticalLayout_OnlinePane")
        self.pushButtonConfiguration = QtWidgets.QPushButton(parent=self.scrollAreaWidgetContents)
        self.pushButtonConfiguration.setStyleSheet("text-align: left; padding-left: 10px; padding-top: 5px; padding-bottom: 5px")
        icon1 = QtGui.QIcon()
        with path("res", "process.png") as f_path:
            icon1.addPixmap(QtGui.QPixmap(str(f_path)), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.pushButtonConfiguration.setIcon(icon1)
        self.pushButtonConfiguration.setIconSize(QtCore.QSize(32, 32))
        self.pushButtonConfiguration.setObjectName("pushButtonConfiguration")
        self.verticalLayout_OnlinePane.addWidget(self.pushButtonConfiguration)
        spacerItem1 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Expanding)
        self.verticalLayout_OnlinePane.addItem(spacerItem1)
        self.scrollArea.setWidget(self.scrollAreaWidgetContents)
        self.horizontalLayout.addWidget(self.scrollArea)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(parent=MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 862, 25))
        self.menubar.setObjectName("menubar")
        self.menuApplication = QtWidgets.QMenu(parent=self.menubar)
        self.menuApplication.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.NoContextMenu)
        self.menuApplication.setTearOffEnabled(False)
        self.menuApplication.setObjectName("menuApplication")
        self.menuEdit = QtWidgets.QMenu(parent=self.menubar)
        self.menuEdit.setObjectName("menuEdit")
        self.menuSelect_Amplifier = QtWidgets.QMenu(parent=self.menuEdit)
        self.menuSelect_Amplifier.setObjectName("menuSelect_Amplifier")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(parent=MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)
        self.actionQuit = QtGui.QAction(parent=MainWindow)
        self.actionQuit.setObjectName("actionQuit")
        self.actionShow_Log = QtGui.QAction(parent=MainWindow)
        self.actionShow_Log.setObjectName("actionShow_Log")
        self.actionLoad_Configuration = QtGui.QAction(parent=MainWindow)
        self.actionLoad_Configuration.setObjectName("actionLoad_Configuration")
        self.actionSave_Configuration = QtGui.QAction(parent=MainWindow)
        self.actionSave_Configuration.setObjectName("actionSave_Configuration")
        self.actionDefault_Configuration = QtGui.QAction(parent=MainWindow)
        self.actionDefault_Configuration.setObjectName("actionDefault_Configuration")
        self.actionNeoRec = QtGui.QAction(parent=MainWindow)
        self.actionNeoRec.setObjectName("actionNeoRec")
        self.actionActiCHamp_Plus = QtGui.QAction(parent=MainWindow)
        self.actionActiCHamp_Plus.setObjectName("actionActiCHamp_Plus")
        self.menuApplication.addAction(self.actionLoad_Configuration)
        self.menuApplication.addAction(self.actionSave_Configuration)
        self.menuApplication.addAction(self.actionDefault_Configuration)
        self.menuApplication.addSeparator()
        self.menuApplication.addAction(self.actionShow_Log)
        self.menuApplication.addSeparator()
        self.menuApplication.addAction(self.actionQuit)
        self.menuSelect_Amplifier.addAction(self.actionNeoRec)
        self.menuSelect_Amplifier.addAction(self.actionActiCHamp_Plus)
        self.menuEdit.addAction(self.menuSelect_Amplifier.menuAction())
        self.menubar.addAction(self.menuApplication.menuAction())
        self.menubar.addAction(self.menuEdit.menuAction())

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "PyCorderPlus"))
        self.pushButtonConfiguration.setText(_translate("MainWindow", "Configuration ..."))
        self.menuApplication.setTitle(_translate("MainWindow", "File"))
        self.menuEdit.setTitle(_translate("MainWindow", "View"))
        self.menuSelect_Amplifier.setTitle(_translate("MainWindow", "Select Amplifier"))
        self.actionQuit.setText(_translate("MainWindow", "Quit"))
        self.actionShow_Log.setText(_translate("MainWindow", "Show Log"))
        self.actionLoad_Configuration.setText(_translate("MainWindow", "Load Configuration ..."))
        self.actionSave_Configuration.setText(_translate("MainWindow", "Save Configuration ..."))
        self.actionDefault_Configuration.setText(_translate("MainWindow", "Reset Configuration"))
        self.actionNeoRec.setText(_translate("MainWindow", "NeoRec (NeoRec cap, NeoRec 21)"))
        self.actionActiCHamp_Plus.setText(_translate("MainWindow", "actiCHamp Plus"))

