# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'calculator.ui'
##
## Created by: Qt User Interface Compiler version 6.7.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QAbstractButton, QApplication, QDialog, QDialogButtonBox,
    QFormLayout, QFrame, QHBoxLayout, QLabel,
    QLineEdit, QSizePolicy, QVBoxLayout, QWidget)
import resources_rc

class Ui_Calculator(object):
    def setupUi(self, Calculator):
        if not Calculator.objectName():
            Calculator.setObjectName(u"Calculator")
        Calculator.setWindowModality(Qt.ApplicationModal)
        Calculator.resize(345, 225)
        Calculator.setLocale(QLocale(QLocale.Greek, QLocale.Greece))
        self.buttonBox = QDialogButtonBox(Calculator)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setGeometry(QRect(20, 170, 271, 32))
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok|QDialogButtonBox.Reset)
        self.label_6 = QLabel(Calculator)
        self.label_6.setObjectName(u"label_6")
        self.label_6.setGeometry(QRect(40, 40, 61, 61))
        self.label_6.setTextFormat(Qt.RichText)
        self.label_6.setPixmap(QPixmap(u"resource/accounting.png"))
        self.label_6.setScaledContents(True)
        self.layoutWidget = QWidget(Calculator)
        self.layoutWidget.setObjectName(u"layoutWidget")
        self.layoutWidget.setGeometry(QRect(120, 30, 180, 115))
        self.verticalLayout = QVBoxLayout(self.layoutWidget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.formLayout = QFormLayout()
        self.formLayout.setObjectName(u"formLayout")
        self.label = QLabel(self.layoutWidget)
        self.label.setObjectName(u"label")

        self.formLayout.setWidget(0, QFormLayout.LabelRole, self.label)

        self.lineedit_auto = QLineEdit(self.layoutWidget)
        self.lineedit_auto.setObjectName(u"lineedit_auto")
        self.lineedit_auto.setLocale(QLocale(QLocale.Greek, QLocale.Greece))
        self.lineedit_auto.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)
        self.lineedit_auto.setClearButtonEnabled(False)

        self.formLayout.setWidget(0, QFormLayout.FieldRole, self.lineedit_auto)

        self.label_2 = QLabel(self.layoutWidget)
        self.label_2.setObjectName(u"label_2")

        self.formLayout.setWidget(1, QFormLayout.LabelRole, self.label_2)

        self.lineedit_ra = QLineEdit(self.layoutWidget)
        self.lineedit_ra.setObjectName(u"lineedit_ra")
        self.lineedit_ra.setLocale(QLocale(QLocale.Greek, QLocale.Greece))
        self.lineedit_ra.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)
        self.lineedit_ra.setClearButtonEnabled(False)

        self.formLayout.setWidget(1, QFormLayout.FieldRole, self.lineedit_ra)

        self.label_3 = QLabel(self.layoutWidget)
        self.label_3.setObjectName(u"label_3")

        self.formLayout.setWidget(2, QFormLayout.LabelRole, self.label_3)

        self.lineedit_legal = QLineEdit(self.layoutWidget)
        self.lineedit_legal.setObjectName(u"lineedit_legal")
        self.lineedit_legal.setLocale(QLocale(QLocale.Greek, QLocale.Greece))
        self.lineedit_legal.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)
        self.lineedit_legal.setClearButtonEnabled(False)

        self.formLayout.setWidget(2, QFormLayout.FieldRole, self.lineedit_legal)


        self.verticalLayout.addLayout(self.formLayout)

        self.line = QFrame(self.layoutWidget)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.verticalLayout.addWidget(self.line)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.label_4 = QLabel(self.layoutWidget)
        self.label_4.setObjectName(u"label_4")
        self.label_4.setAlignment(Qt.AlignLeading|Qt.AlignLeft|Qt.AlignVCenter)

        self.horizontalLayout.addWidget(self.label_4)

        self.lbl_total_amount = QLabel(self.layoutWidget)
        self.lbl_total_amount.setObjectName(u"lbl_total_amount")
        font = QFont()
        font.setBold(True)
        self.lbl_total_amount.setFont(font)
        self.lbl_total_amount.setLayoutDirection(Qt.LeftToRight)
        self.lbl_total_amount.setAutoFillBackground(False)
        self.lbl_total_amount.setLocale(QLocale(QLocale.Greek, QLocale.Greece))
        self.lbl_total_amount.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)

        self.horizontalLayout.addWidget(self.lbl_total_amount)


        self.verticalLayout.addLayout(self.horizontalLayout)

        QWidget.setTabOrder(self.lineedit_auto, self.lineedit_ra)
        QWidget.setTabOrder(self.lineedit_ra, self.lineedit_legal)

        self.retranslateUi(Calculator)
        self.buttonBox.accepted.connect(Calculator.accept)
        self.buttonBox.rejected.connect(Calculator.reject)

        QMetaObject.connectSlotsByName(Calculator)
    # setupUi

    def retranslateUi(self, Calculator):
        Calculator.setWindowTitle(QCoreApplication.translate("Calculator", u"\u03a5\u03c0\u03bf\u03bb\u03bf\u03b3\u03b9\u03c3\u03c4\u03ae\u03c2 \u0391\u03c3\u03c6\u03b1\u03bb\u03af\u03c3\u03c4\u03c1\u03c9\u03bd", None))
        self.label_6.setText("")
        self.label.setText(QCoreApplication.translate("Calculator", u"\u0392\u03b1\u03c3\u03b9\u03ba\u03cc \u0391\u03c3\u03c6\u03ac\u03bb\u03b9\u03c3\u03c4\u03c1\u03bf", None))
        self.label_2.setText(QCoreApplication.translate("Calculator", u"\u039f\u03b4\u03b9\u03ba\u03ae \u0392\u03bf\u03ae\u03b8\u03b5\u03b9\u03b1", None))
        self.label_3.setText(QCoreApplication.translate("Calculator", u"\u039d\u03bf\u03bc\u03b9\u03ba\u03ae \u03a0\u03c1\u03bf\u03c3\u03c4\u03b1\u03c3\u03af\u03b1", None))
        self.label_4.setText(QCoreApplication.translate("Calculator", u"\u03a3\u03cd\u03bd\u03bf\u03bb\u03bf :", None))
        self.lbl_total_amount.setText(QCoreApplication.translate("Calculator", u"0,00", None))
    # retranslateUi

