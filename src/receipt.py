import json
import locale
import os
import subprocess
import sys

from mailmerge import MailMerge
from PyQt6 import uic
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtCore import QCoreApplication, QDate, QEvent, Qt, QLocale
from PyQt6.QtWidgets import *
from win32com import client
import win32print

from helpers import Calculator, show_message

UI_FILE = os.path.join(os.path.dirname(__file__), "receipt.ui")
DATA_FILE = os.path.join(os.path.dirname(__file__), "record.json")
TEMPLATE_EISPRAXI = os.path.join(
    os.path.dirname(__file__),
    "resource",
    "eispraxi_template.docx"
)
TEMPLATE_PARALABI = os.path.join(
    os.path.dirname(__file__),
    "resource",
    "paralabi_template.docx"
)
RADIO_GRP_MAPPING = {
    -2: 1,
    -3: 3,
    -4: 6,
    -5: 12,
    -6: 0
}
VERSION = "1.3.0"


# def show_message(
#         msg_text,
#         msg_details=None,
#         msg_title="DOMINO Insurance",
#         msg_type="Information"
# ):
#     msg_box = QMessageBox(QMessageBox.Icon.Information, msg_title, msg_text)

#     if msg_type == "Question":
#         msg_box.setIcon(QMessageBox.Icon.Question)
#         msg_box.setStandardButtons(
#             QMessageBox.StandardButton.Yes |
#             QMessageBox.StandardButton.No |
#             QMessageBox.StandardButton.Cancel
#         )
#     elif msg_type == "Critical":
#         msg_box.setIcon(QMessageBox.Icon.Critical)
#     elif msg_type == "Warning":
#         msg_box.setIcon(QMessageBox.Icon.Warning)

#     msg_box.setText(msg_text)
#     if msg_details:
#         msg_box.setDetailedText(msg_details)
#     return msg_box.exec()


# def double_validator():
#     double_validator = QDoubleValidator()
#     double_validator.setDecimals(2)
#     double_validator.setLocale(
#         QLocale(QLocale.Language.Greek, QLocale.Country.Greece)
#     )
#     double_validator.setNotation(QDoubleValidator.Notation.StandardNotation)
#     return double_validator


class Receipt(QMainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        uic.loadUi(UI_FILE, self)

        self.receipt_number = 0
        self.insurance_companies = []
        self.insurance_ra = []
        self.insurance_legal = []
        self.insurance_types = []
        self.customers = []
        self.json_data = None
        self.doc_entries = []

        self.import_data(DATA_FILE)
        
        self.set_ui()
        self.set_signals()

    def set_ui(self):
        self.action_tray1.setChecked(False)
        self.lbl_date.setText(QDate.currentDate().toString("dd/MM/yyyy"))
        self.lbl_receipt_number.setText(str(self.receipt_number))
        self.lineedit_amount.installEventFilter(self)
        # self.lineedit_amount.setValidator(double_validator())
        self.lineedit_customer.setCompleter(QCompleter(self.customers))
        self.lineedit_customer.setFocus()
        self.lineedit_legal_policy.setEnabled(False)
        self.lineedit_ra_policy.setEnabled(False)
        self.cmb_insurance_company.addItems(self.insurance_companies)
        self.cmb_insurance_type.addItems(self.insurance_types)
        self.cmb_insurance_ra.addItems(self.insurance_ra)
        self.cmb_insurance_legal.addItems(self.insurance_legal)
        self.radio6.setChecked(True)
        self.date_start.setDate(QDate.currentDate())
        self.date_end.setDate(QDate.currentDate().addMonths(6))

        for cmb in self.findChildren(QComboBox):
            cmb.setCurrentIndex(-1)

    def set_signals(self):
        self.action_quick_receipt.triggered.connect(self.print_quick_receipt)
        self.action_version.triggered.connect(self.about)
        self.cmb_insurance_company.currentTextChanged.connect(self.check_insurance)
        self.cmb_insurance_legal.currentIndexChanged.connect(self.check_legal)
        self.cmb_insurance_ra.currentIndexChanged.connect(self.check_ra)
        self.cmb_insurance_type.currentTextChanged.connect(self.check_type)
        self.lineedit_amount.editingFinished.connect(self.format_currency)
        self.lineedit_customer.editingFinished.connect(self.update_customer_list)
        self.button_grp_length.buttonClicked.connect(self.calculate_end_date)
        self.date_start.editingFinished.connect(self.calculate_end_date)
        self.btn_reset.clicked.connect(self.clear_ui)
        self.btn_e_sign.clicked.connect(self.e_sign)
        self.btn_exit.clicked.connect(QCoreApplication.instance().quit)
        self.btn_print.clicked.connect(self.print_receipt)

    def eventFilter(self, watched, event):
        if watched == self.lineedit_amount and \
          event.type() == QEvent.Type.MouseButtonDblClick:
            self.open_calculator()
        return QWidget.eventFilter(self, watched, event)

    def clear_ui(self):
        for lineedit in self.findChildren(QLineEdit):
            lineedit.clear()

        for cmb in self.findChildren(QComboBox):
            cmb.clear()

        for chk in self.findChildren(QCheckBox):
            chk.setChecked(False)

        for dates in self.findChildren(QDateEdit):
            dates.clear()

        self.set_ui()

    def open_calculator(self):
        calc_window = Calculator(self)
        calc_window.show()

    def format_currency(self):  # TODO: Make this a custom validator class
        locale.setlocale(locale.LC_ALL, "el_GR.UTF-8")
        formatted_number = locale.format_string(
            "%.2f",
            float(self.lineedit_amount.text().replace(",", ".") or 0.00),
            grouping=True
        )
        self.lineedit_amount.setText(formatted_number)

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

    def update_customer_list(self):
        customer_name = self.lineedit_customer.text()
        if customer_name and customer_name not in self.customers:
            ans = show_message(
                f"Ο Πελάτης {customer_name} δεν βρέθηκε στη λίστα... \nΝα γίνει νέα εγγραφή;",
                msg_type="Question"
            ) 
            if ans == QMessageBox.StandardButton.Yes:
                self.customers.append(customer_name)
                self.lineedit_customer.setCompleter(QCompleter(self.customers))

                new_customer = {"name": customer_name}
                self.json_data["customer"].append(new_customer)
                self.update_data_file()
            elif ans == QMessageBox.StandardButton.Cancel:
                self.lineedit_customer.setFocus()

    def calculate_end_date(self):
        self.date_end.setDate(
            self.date_start.date().addMonths(RADIO_GRP_MAPPING.get(
                self.button_grp_length.checkedId())
            )
        )

    def prepare_printing(self, receipt_only=False):
        print_docs = []

        company_text = self.cmb_insurance_company.currentText()
        policy_text = self.lineedit_policy.text()

        if self.lineedit_ra_policy.text():
            company_text = company_text + \
                ", " + self.cmb_insurance_ra.currentText()
            policy_text = policy_text + \
                ", " + self.lineedit_ra_policy.text()

        if self.lineedit_legal_policy.text():
            company_text = company_text + \
                ", " + self.cmb_insurance_legal.currentText()
            policy_text = policy_text + \
                ", " + self.lineedit_legal_policy.text()

        if self.lineedit_ra_policy.text() or self.lineedit_legal_policy.text():
            split_company_text = company_text.split()
            split_company_text.insert(-1, "και")
            split_company_text.append("αντίστοιχα")
            company_text = " ".join(split_company_text)
            split_company_text = company_text.rsplit(",", 1)
            company_text = split_company_text[0] + split_company_text[1]

            split_policy_text = policy_text.split()
            split_policy_text.insert(-1, "και")
            policy_text = " ".join(split_policy_text)
            split_policy_text = policy_text.rsplit(",", 1)
            policy_text = split_policy_text[0] + split_policy_text[1]

        # create template dict
        self.doc_entries = {
            "amount": self.lineedit_amount.text(),
            "branch": self.cmb_insurance_type.currentText(),
            "company": company_text,
            "customer": self.lineedit_customer.text(),
            "description": "",
            "end": self.date_end.date().toString("dd/MM/yyyy"),
            "plate": self.lineedit_plate.text(),
            "policy": policy_text,
            "receipt": self.lbl_receipt_number.text(),
            "start": self.date_start.date().toString("dd/MM/yyyy"),
        }

        # create output files from templates
        if not receipt_only:
            with MailMerge(TEMPLATE_PARALABI) as document:
                document.merge(**self.doc_entries)
                document.write("print_paralabi.docx")

            print_docs.append(
                os.path.join(
                    os.path.dirname(os.path.realpath(__file__)),
                    "print_paralabi.docx"
                )
            )

        if self.chk_money_receipt.isChecked() or receipt_only:
            if self.lineedit_ra_policy.text() or \
              self.lineedit_legal_policy.text():
                self.doc_entries["company"] = company_text.replace(
                    ",", " /"
                ).replace(
                    "και", "/"
                ).replace(
                    "αντίστοιχα", ""
                )
                self.doc_entries["policy"] = policy_text.replace(
                    ",", " /"
                ).replace(
                    "και", "/"
                )

            if self.cmb_insurance_type.currentIndex() == 0:
                self.doc_entries["description"] = "το όχημα με αρ. κυκλοφορίας " + \
                    self.lineedit_plate.text()
            elif self.cmb_insurance_type.currentIndex() == 4:
                self.doc_entries["description"] = \
                    "οδική βοήθεια για το όχημα με αρ. κυκλοφορίας " + \
                    self.lineedit_plate.text()
            else:
                self.doc_entries["description"] = "συμβόλαιο κλάδου " + \
                    self.cmb_insurance_type.currentText()

            with MailMerge(
                TEMPLATE_EISPRAXI,
                remove_empty_tables=False,
                auto_update_fields_on_open="no"
            ) as document:
                document.merge(**self.doc_entries)
                document.write("print_eispraxi.docx")

            print_docs.append(
                os.path.join(
                    os.path.dirname(os.path.realpath(__file__)),
                    "print_eispraxi.docx"
                )
            )
        return print_docs

    def update_data_file(self):
        try:
            with open(DATA_FILE, "w") as file_to_write:
                json.dump(
                    self.json_data,
                    file_to_write,
                    ensure_ascii=False,
                    indent=4
                )
        except OSError as e:
            show_message(
                "Unable to update data file. \n{}".format(e),
                msg_type="Warning"
            )

    def update_receipt_number(self):
        self.json_data["id"] = self.receipt_number
        self.update_data_file()
        self.receipt_number += 1
        self.lbl_receipt_number.setText(str(self.receipt_number))

    def print_quick_receipt(self):
        print_docs = self.prepare_printing(receipt_only=True)
        self.print_document(print_docs[0], tray_number=260, black_ink_only=True)
        self.update_receipt_number()

    def print_receipt(self):
        # self.update_receipt_number()
        print_docs = self.prepare_printing()

        print_tray = 259
        if self.action_tray1.isChecked():
            print_tray = 260

        self.print_document(print_docs[0], print_tray, black_ink_only=True)

        if self.chk_money_receipt.isChecked():
            self.print_document(print_docs[1], tray_number=260, black_ink_only=True)
            self.update_receipt_number()

    def print_document(self, document, tray_number, black_ink_only):
        printer_defaults = {
            "DesiredAccess": win32print.PRINTER_ALL_ACCESS
        }

        printer_name = win32print.GetDefaultPrinter()
        printer_handle = win32print.OpenPrinter(
            printer_name,
            printer_defaults
        )

        properties = win32print.GetPrinter(printer_handle, 2)
        devmode = properties["pDevMode"]

        reset_printer_source = devmode.DefaultSource
        reset_printer_color = devmode.Color
        reset_printer_duplex = devmode.Duplex

        devmode.DefaultSource = tray_number
        devmode.Color = 1 if black_ink_only else 0
        devmode.Duplex = 1

        win32print.DocumentProperties(
            None,
            printer_handle,
            printer_name,
            devmode,
            devmode,
            0
        )
        win32print.SetPrinter(printer_handle, 2, properties, 0)

        word = client.Dispatch("Word.Application")
        w_doc = word.Documents.Open(document)
        word.ActiveDocument.PrintOut()
        word.ActiveDocument.Close()
        word.Quit()

        # reset printer settings
        devmode.DefaultSource = reset_printer_source
        devmode.Color = reset_printer_color
        devmode.Duplex = reset_printer_duplex
        win32print.SetPrinter(printer_handle, 2, properties, 0)

    def e_sign(self):

        info_w = show_message(msg_text="Προετοιμασία εγγράφων...", msg_type="no_buttons")

        def _open_pdf_file(pdf_filepath):
            try:
                word = client.Dispatch("Word.Application")
                doc = word.Documents.Open(print_docs[0])
                doc.SaveAs(pdf_filepath, FileFormat=17)  # FileFormat for PDF
                doc.Close()
                word.Quit()
            except Exception as e:
                show_message(
                    "Unable to save file\n{0}\n{1}".format(pdf_filepath, e),
                    msg_title="Error",
                    msg_type="Critical"
                )
                doc.Close()
                word.Quit()
                return

            subprocess.Popen(
                [pdf_filepath],
                shell=True
            )

        print_docs = self.prepare_printing()

        pdf_dir = os.path.join(
            "\\\\DOM-SRV-01\\DominoInsurance\\Αρχείο",
            self.doc_entries["customer"],
            "receipts",
        )

        date_format = self.doc_entries["start"].split("/")
        date_format.reverse()
        date_format = ".".join(date_format)

        if self.doc_entries["plate"]:
            pdf_filename = self.doc_entries["plate"] + "_" + date_format + \
                " - signed.pdf"
        else:
            pdf_filename = self.doc_entries["branch"] + "_" + date_format + \
                " - signed.pdf"

        pdf_filepath = os.path.join(pdf_dir, pdf_filename)

        if not os.path.isdir(pdf_dir):
            msg_reply = show_message(
                "New directory will be created:\n{0}".format(pdf_dir),
                msg_type="Question"
            )
            if msg_reply == QMessageBox.StandardButton.Yes:
                try:
                    os.makedirs(pdf_dir)
                except OSError as e:
                    show_message(
                        "Unable to create directories\n{0}".format(pdf_dir),
                        msg_type="Critical",
                        msg_title="Error",
                        msg_details="{}".format(e)
                    )
                    return
                _open_pdf_file(pdf_filepath)
            elif msg_reply == QMessageBox.StandardButton.No:
                doc_path = print_docs[0].rsplit(".", 1)
                pdf_tmp_filepath = doc_path[0] + ".pdf"
                _open_pdf_file(pdf_tmp_filepath)
        else:
            _open_pdf_file(pdf_filepath)

        if self.chk_money_receipt.isChecked():
            self.print_document(print_docs[1], tray_number=260, black_ink_only=True)
            self.update_receipt_number()

        info_w.accept()

    def check_insurance(self, insurance):
        if insurance in ["ARAG", "MEDITERRANIA"]:
            self.cmb_insurance_type.setCurrentText("ΝΟΜΙΚΗΣ ΠΡΟΣΤΑΣΙΑΣ")
        elif insurance == "MONDIAL ASSISTANCE":
            self.cmb_insurance_type.setCurrentText("ΤΑΞΙΔΙΩΤΙΚΗΣ ΑΣΦΑΛΙΣΗΣ")
        else:
            self.cmb_insurance_type.setCurrentText("ΑΥΤΟΚΙΝΗΤΟΥ")

    def check_type(self, ins_type):
        if ins_type not in ["ΑΥΤΟΚΙΝΗΤΟΥ", "ΝΟΜΙΚΗΣ ΠΡΟΣΤΑΣΙΑΣ", "ΟΔΙΚΗΣ ΒΟΗΘΕΙΑΣ"]:
            self.lineedit_plate.setEnabled(False)
        else:
            self.lineedit_plate.setEnabled(True)

    def check_ra(self, ra):
        if ra == -1:
            self.lineedit_ra_policy.setEnabled(False)
        else:
            self.lineedit_ra_policy.setEnabled(True)

    def check_legal(self, legal):
        if legal == -1:
            self.lineedit_legal_policy.setEnabled(False)
        else:
            self.lineedit_legal_policy.setEnabled(True)

    def about(self):
        show_message(
            f"Απόδειξη Παραλαβής και Είσπραξης Ασφαλιστηρίου Συμβολαίου \
                v{VERSION} - DOMINO GROUP (2023)"
        )


# class Calculator(QDialog):
#     def __init__(self, parent=None):
#         super().__init__(parent)
#         self.parent = parent

#         ui_file = os.path.join(os.path.dirname(__file__), "calculator.ui")
#         uic.loadUi(ui_file, self)

#         self.set_ui()
#         self.set_signals()

#     def set_ui(self):
#         self.lineedit_auto.setFocus()
#         self.lineedit_auto.setValidator(double_validator())
#         self.lineedit_legal.setValidator(double_validator())
#         self.lineedit_ra.setValidator(double_validator())

#     def set_signals(self):
#         self.buttonBox.accepted.connect(self.update_total)
#         self.lineedit_auto.textChanged.connect(self.calculate_total)
#         self.lineedit_legal.textChanged.connect(self.calculate_total)
#         self.lineedit_ra.textChanged.connect(self.calculate_total)
#         self.buttonBox.button(
#             QDialogButtonBox.StandardButton.Reset
#         ).clicked.connect(self.reset_form)

#     def reset_form(self):
#         for lineedit in self.findChildren(QLineEdit):
#             lineedit.clear()

#         self.lineedit_auto.setFocus()

#     def update_total(self):
#         self.parent.lineedit_amount.setText(
#             self.lbl_total_amount.text()
#         )

#     def calculate_total(self):
#         total_cost = float(self.lineedit_auto.text().replace(",", ".") or 0.00) \
#             + float(self.lineedit_legal.text().replace(",", ".") or 0.00) \
#             + float(self.lineedit_ra.text().replace(",", ".") or 0.00)
#         total_cost = "{:.2f}".format(total_cost)
#         self.lbl_total_amount.setText(total_cost.replace(".", ","))


if __name__ == "__main__":
    app = QApplication(sys.argv)

    app.setStyle(QStyleFactory.create("Fusion"))

    dark_palette = QPalette()
    dark_palette.setColor(QPalette.ColorRole.Window, QColor(45, 45, 45))
    dark_palette.setColor(QPalette.ColorRole.WindowText, QColor(208, 208, 208))
    dark_palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25))
    dark_palette.setColor(QPalette.ColorRole.AlternateBase, QColor(208, 208, 208))
    dark_palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(208, 208, 208))
    dark_palette.setColor(QPalette.ColorRole.Text, QColor(208, 208, 208))
    dark_palette.setColor(QPalette.ColorRole.Button, QColor(45, 45, 45))
    dark_palette.setColor(QPalette.ColorRole.ButtonText, QColor(208, 208, 208))
    dark_palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
    dark_palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))

    app.setPalette(dark_palette)

    window = Receipt()
    window.show()
    app.exec()
