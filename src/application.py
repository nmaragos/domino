import json
import os
import sys
 
from PyQt6 import uic
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtWidgets import *

from helpers import show_message


UI_FILE = os.path.join(os.path.dirname(__file__), "application.ui")
DATA_FILE = os.path.join(os.path.dirname(__file__), "record.json")

class Application(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.parent = parent
        ui_file = os.path.join(os.path.dirname(__file__), "application.ui")
        uic.loadUi(ui_file, self)

        self.customers = []
        self.insurance_companies = []

        self.import_data(DATA_FILE)

        self.set_ui()
        self.set_signals()

    def set_ui(self):
        self.lbl_date.setText(QDate.currentDate().toString("dd/MM/yyyy"))
        self.lineedit_customer.setFocus()
        self.lineedit_customer.setCompleter(QCompleter(self.customers))
        self.cmb_ins_company_1.addItems(self.insurance_companies)
        self.cmb_ins_company_2.addItems(self.insurance_companies)
        self.cmb_ins_company_3.addItems(self.insurance_companies)
        self.dateedit_start.setDate(QDate.currentDate())
        self.dateedit_end.setDate(QDate.currentDate().addMonths(6))

        for cmb in self.findChildren(QComboBox):
            cmb.setCurrentIndex(-1)

    def set_signals(self):
        self.btn_exit.clicked.connect(self.close)

    def import_data(self, json_file):
        try:
            with open(json_file) as file_to_read:
                self.json_data = json.load(file_to_read)
        except OSError as e:
            show_message(
                "Unable to open data file. \n{0}".format(e),
                msg_title="Error",
                msg_type="Critical",
            )
            return

        self.receipt_number = int(self.json_data["id"]) + 1

        customers = []
        for customer in self.json_data["customer"]:
            customers.append(customer["name"])
        self.customers = sorted(customers)

        insurance_companies = []
        for company in self.json_data["insurance_company"]:
            insurance_companies.append(company["name"])
        self.insurance_companies = sorted(insurance_companies)

        insurance_ra = []
        for company in self.json_data["insurance_ra"]:
            insurance_ra.append(company["name"])
        self.insurance_ra = sorted(insurance_ra)

        insurance_legal = []
        for company in self.json_data["insurance_legal"]:
            insurance_legal.append(company["name"])
        self.insurance_legal = sorted(insurance_legal)

        insurance_types = []
        for ins_type in self.json_data["insurance_type"]:
            insurance_types.append(ins_type["name"])
        self.insurance_types = insurance_types

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # app.setStyle(QStyleFactory.create("Fusion"))

    # dark_palette = QPalette()
    # dark_palette.setColor(QPalette.ColorRole.Window, QColor(45, 45, 45))
    # dark_palette.setColor(QPalette.ColorRole.WindowText, QColor(208, 208, 208))
    # dark_palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25))
    # dark_palette.setColor(QPalette.ColorRole.AlternateBase, QColor(208, 208, 208))
    # dark_palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(208, 208, 208))
    # dark_palette.setColor(QPalette.ColorRole.Text, QColor(208, 208, 208))
    # dark_palette.setColor(QPalette.ColorRole.Button, QColor(45, 45, 45))
    # dark_palette.setColor(QPalette.ColorRole.ButtonText, QColor(208, 208, 208))
    # dark_palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
    # dark_palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
    # dark_palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))

    # app.setPalette(dark_palette)

    window = Application()
    window.show()
    app.exec()
