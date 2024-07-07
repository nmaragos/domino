import os

from PyQt6.QtCore import QLocale
from PyQt6.QtGui import QDoubleValidator
from PyQt6 import uic
from PyQt6.QtWidgets import *


def show_message(
        msg_text,
        msg_details=None,
        msg_title="DOMINO Insurance",
        msg_type="Information"
):
    msg_box = QMessageBox(QMessageBox.Icon.Information, msg_title, msg_text)

    if msg_type == "Question":
        msg_box.setIcon(QMessageBox.Icon.Question)
        msg_box.setStandardButtons(
            QMessageBox.StandardButton.Yes |
            QMessageBox.StandardButton.No |
            QMessageBox.StandardButton.Cancel
        )
    elif msg_type == "Critical":
        msg_box.setIcon(QMessageBox.Icon.Critical)
    elif msg_type == "Warning":
        msg_box.setIcon(QMessageBox.Icon.Warning)
    elif msg_type == "no_buttons":
        msg_box.setStandardButtons(QMessageBox.StandardButton.NoButton)
        msg_box.setStyleSheet("QDialog {border: 1px solid black;}")

    msg_box.setText(msg_text)
    if msg_details:
        msg_box.setDetailedText(msg_details)

    if msg_type == "no_buttons":
        msg_box.show()
        return msg_box

    return msg_box.exec()


def double_validator():
    double_validator = QDoubleValidator()
    double_validator.setDecimals(2)
    double_validator.setLocale(
        QLocale(QLocale.Language.Greek, QLocale.Country.Greece)
    )
    double_validator.setNotation(QDoubleValidator.Notation.StandardNotation)
    return double_validator


class Calculator(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.parent = parent
        ui_file = os.path.join(os.path.dirname(__file__), "calculator.ui")
        uic.loadUi(ui_file, self)

        self.set_ui()
        self.set_signals()

    def set_ui(self):
        self.lineedit_auto.setFocus()
        self.lineedit_auto.setValidator(double_validator())
        self.lineedit_legal.setValidator(double_validator())
        self.lineedit_ra.setValidator(double_validator())

    def set_signals(self):
        self.buttonBox.accepted.connect(self.update_total)
        self.lineedit_auto.textChanged.connect(self.calculate_total)
        self.lineedit_legal.textChanged.connect(self.calculate_total)
        self.lineedit_ra.textChanged.connect(self.calculate_total)
        self.buttonBox.button(
            QDialogButtonBox.StandardButton.Reset
        ).clicked.connect(self.reset_form)

    def reset_form(self):
        for lineedit in self.findChildren(QLineEdit):
            lineedit.clear()

        self.lineedit_auto.setFocus()

    def update_total(self):
        self.parent.lineedit_amount.setText(
            self.lbl_total_amount.text()
        )

    def calculate_total(self):
        total_cost = float(self.lineedit_auto.text().replace(",", ".") or 0.00) \
            + float(self.lineedit_legal.text().replace(",", ".") or 0.00) \
            + float(self.lineedit_ra.text().replace(",", ".") or 0.00)
        total_cost = "{:.2f}".format(total_cost)
        self.lbl_total_amount.setText(total_cost.replace(".", ","))