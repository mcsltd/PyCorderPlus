# Form implementation generated from reading ui file '.\res\frmScopeOnline.ui'
#
# Created by: PyQt6 UI code generator 6.6.0
#
# WARNING: Any manual changes made to this file will be lost when pyuic6 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_frmScopeOnline(object):
    def setupUi(self, frmScopeOnline):
        frmScopeOnline.setObjectName("frmScopeOnline")
        frmScopeOnline.resize(280, 186)
        frmScopeOnline.setFrameShape(QtWidgets.QFrame.Shape.Panel)
        frmScopeOnline.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.gridLayout = QtWidgets.QGridLayout(frmScopeOnline)
        self.gridLayout.setObjectName("gridLayout")
        self.groupBox = QtWidgets.QGroupBox(parent=frmScopeOnline)
        self.groupBox.setObjectName("groupBox")
        self.gridLayout_2 = QtWidgets.QGridLayout(self.groupBox)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.gridLayout_OnlineScope = QtWidgets.QGridLayout()
        self.gridLayout_OnlineScope.setContentsMargins(4, -1, 4, -1)
        self.gridLayout_OnlineScope.setHorizontalSpacing(12)
        self.gridLayout_OnlineScope.setObjectName("gridLayout_OnlineScope")
        self.label = QtWidgets.QLabel(parent=self.groupBox)
        self.label.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeading|QtCore.Qt.AlignmentFlag.AlignLeft|QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.label.setObjectName("label")
        self.gridLayout_OnlineScope.addWidget(self.label, 0, 0, 1, 1)
        self.comboBoxTime = QtWidgets.QComboBox(parent=self.groupBox)
        self.comboBoxTime.setMaximumSize(QtCore.QSize(80, 16777215))
        self.comboBoxTime.setObjectName("comboBoxTime")
        self.comboBoxTime.addItem("")
        self.comboBoxTime.addItem("")
        self.comboBoxTime.addItem("")
        self.comboBoxTime.addItem("")
        self.comboBoxTime.addItem("")
        self.comboBoxTime.addItem("")
        self.comboBoxTime.addItem("")
        self.comboBoxTime.addItem("")
        self.comboBoxTime.addItem("")
        self.gridLayout_OnlineScope.addWidget(self.comboBoxTime, 0, 1, 1, 1)
        self.label_2 = QtWidgets.QLabel(parent=self.groupBox)
        self.label_2.setMaximumSize(QtCore.QSize(100, 16777215))
        self.label_2.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeading|QtCore.Qt.AlignmentFlag.AlignLeft|QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.label_2.setObjectName("label_2")
        self.gridLayout_OnlineScope.addWidget(self.label_2, 1, 0, 1, 1)
        self.comboBoxScale = QtWidgets.QComboBox(parent=self.groupBox)
        self.comboBoxScale.setMaximumSize(QtCore.QSize(80, 16777215))
        self.comboBoxScale.setMaxVisibleItems(16)
        self.comboBoxScale.setObjectName("comboBoxScale")
        self.comboBoxScale.addItem("")
        self.comboBoxScale.addItem("")
        self.comboBoxScale.addItem("")
        self.comboBoxScale.addItem("")
        self.comboBoxScale.addItem("")
        self.comboBoxScale.addItem("")
        self.comboBoxScale.addItem("")
        self.comboBoxScale.addItem("")
        self.comboBoxScale.addItem("")
        self.comboBoxScale.addItem("")
        self.comboBoxScale.addItem("")
        self.comboBoxScale.addItem("")
        self.comboBoxScale.addItem("")
        self.comboBoxScale.addItem("")
        self.comboBoxScale.addItem("")
        self.comboBoxScale.addItem("")
        self.gridLayout_OnlineScope.addWidget(self.comboBoxScale, 1, 1, 1, 1)
        self.label_3 = QtWidgets.QLabel(parent=self.groupBox)
        self.label_3.setObjectName("label_3")
        self.gridLayout_OnlineScope.addWidget(self.label_3, 0, 2, 1, 1)
        self.label_4 = QtWidgets.QLabel(parent=self.groupBox)
        self.label_4.setObjectName("label_4")
        self.gridLayout_OnlineScope.addWidget(self.label_4, 1, 2, 1, 1)
        self.label_5 = QtWidgets.QLabel(parent=self.groupBox)
        self.label_5.setObjectName("label_5")
        self.gridLayout_OnlineScope.addWidget(self.label_5, 2, 0, 1, 1)
        self.comboBoxChannels = QtWidgets.QComboBox(parent=self.groupBox)
        self.comboBoxChannels.setMaximumSize(QtCore.QSize(400, 16777215))
        self.comboBoxChannels.setMaxVisibleItems(20)
        self.comboBoxChannels.setSizeAdjustPolicy(QtWidgets.QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.comboBoxChannels.setObjectName("comboBoxChannels")
        self.gridLayout_OnlineScope.addWidget(self.comboBoxChannels, 2, 1, 1, 1)
        self.comboBoxGroupSize = QtWidgets.QComboBox(parent=self.groupBox)
        self.comboBoxGroupSize.setMaximumSize(QtCore.QSize(50, 16777215))
        self.comboBoxGroupSize.setObjectName("comboBoxGroupSize")
        self.comboBoxGroupSize.addItem("")
        self.comboBoxGroupSize.addItem("")
        self.comboBoxGroupSize.addItem("")
        self.comboBoxGroupSize.addItem("")
        self.comboBoxGroupSize.addItem("")
        self.comboBoxGroupSize.addItem("")
        self.gridLayout_OnlineScope.addWidget(self.comboBoxGroupSize, 2, 2, 1, 1)
        self.gridLayout_2.addLayout(self.gridLayout_OnlineScope, 0, 0, 1, 1)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setContentsMargins(-1, 5, -1, -1)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.checkBoxBaseline = QtWidgets.QCheckBox(parent=self.groupBox)
        self.checkBoxBaseline.setObjectName("checkBoxBaseline")
        self.horizontalLayout.addWidget(self.checkBoxBaseline)
        self.pushButton_Now = QtWidgets.QPushButton(parent=self.groupBox)
        self.pushButton_Now.setObjectName("pushButton_Now")
        self.horizontalLayout.addWidget(self.pushButton_Now)
        self.gridLayout_2.addLayout(self.horizontalLayout, 1, 0, 1, 1)
        self.gridLayout.addWidget(self.groupBox, 0, 0, 1, 1)

        self.retranslateUi(frmScopeOnline)
        self.comboBoxTime.setCurrentIndex(6)
        self.comboBoxScale.setCurrentIndex(7)
        self.comboBoxChannels.setCurrentIndex(-1)
        self.comboBoxGroupSize.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(frmScopeOnline)

    def retranslateUi(self, frmScopeOnline):
        _translate = QtCore.QCoreApplication.translate
        frmScopeOnline.setWindowTitle(_translate("frmScopeOnline", "Display"))
        self.groupBox.setTitle(_translate("frmScopeOnline", "Display"))
        self.label.setText(_translate("frmScopeOnline", "Timebase"))
        self.comboBoxTime.setItemText(0, _translate("frmScopeOnline", "0.1"))
        self.comboBoxTime.setItemText(1, _translate("frmScopeOnline", "0.2"))
        self.comboBoxTime.setItemText(2, _translate("frmScopeOnline", "0.5"))
        self.comboBoxTime.setItemText(3, _translate("frmScopeOnline", "1.0"))
        self.comboBoxTime.setItemText(4, _translate("frmScopeOnline", "2.0"))
        self.comboBoxTime.setItemText(5, _translate("frmScopeOnline", "5.0"))
        self.comboBoxTime.setItemText(6, _translate("frmScopeOnline", "10.0"))
        self.comboBoxTime.setItemText(7, _translate("frmScopeOnline", "20.0"))
        self.comboBoxTime.setItemText(8, _translate("frmScopeOnline", "50.0"))
        self.label_2.setText(_translate("frmScopeOnline", "Scale"))
        self.comboBoxScale.setItemText(0, _translate("frmScopeOnline", "0.5"))
        self.comboBoxScale.setItemText(1, _translate("frmScopeOnline", "1"))
        self.comboBoxScale.setItemText(2, _translate("frmScopeOnline", "2"))
        self.comboBoxScale.setItemText(3, _translate("frmScopeOnline", "5"))
        self.comboBoxScale.setItemText(4, _translate("frmScopeOnline", "10"))
        self.comboBoxScale.setItemText(5, _translate("frmScopeOnline", "20"))
        self.comboBoxScale.setItemText(6, _translate("frmScopeOnline", "50"))
        self.comboBoxScale.setItemText(7, _translate("frmScopeOnline", "100"))
        self.comboBoxScale.setItemText(8, _translate("frmScopeOnline", "200"))
        self.comboBoxScale.setItemText(9, _translate("frmScopeOnline", "500"))
        self.comboBoxScale.setItemText(10, _translate("frmScopeOnline", "1000"))
        self.comboBoxScale.setItemText(11, _translate("frmScopeOnline", "2000"))
        self.comboBoxScale.setItemText(12, _translate("frmScopeOnline", "5000"))
        self.comboBoxScale.setItemText(13, _translate("frmScopeOnline", "10000"))
        self.comboBoxScale.setItemText(14, _translate("frmScopeOnline", "20000"))
        self.comboBoxScale.setItemText(15, _translate("frmScopeOnline", "50000"))
        self.label_3.setText(_translate("frmScopeOnline", "/Page"))
        self.label_4.setText(_translate("frmScopeOnline", "/Div"))
        self.label_5.setText(_translate("frmScopeOnline", "Channels"))
        self.comboBoxGroupSize.setItemText(0, _translate("frmScopeOnline", "1"))
        self.comboBoxGroupSize.setItemText(1, _translate("frmScopeOnline", "2"))
        self.comboBoxGroupSize.setItemText(2, _translate("frmScopeOnline", "4"))
        self.comboBoxGroupSize.setItemText(3, _translate("frmScopeOnline", "8"))
        self.comboBoxGroupSize.setItemText(4, _translate("frmScopeOnline", "16"))
        self.comboBoxGroupSize.setItemText(5, _translate("frmScopeOnline", "32"))
        self.checkBoxBaseline.setText(_translate("frmScopeOnline", "Baseline Correction"))
        self.pushButton_Now.setText(_translate("frmScopeOnline", "Now"))
