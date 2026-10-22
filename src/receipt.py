import locale
import os
# import pyi_splash
import subprocess
import sys
import tempfile


from mailmerge import MailMerge
from PyQt6 import uic
from PyQt6.QtCore import QCoreApplication, QDate, QEvent, Qt, QSettings
from PyQt6.QtGui import QGuiApplication, QStandardItem, QStandardItemModel
from PyQt6.QtPrintSupport import QPrintDialog, QPrinter
from PyQt6.QtWidgets import *
from win32com import client
import win32print

import application_dialog
import application_pdf
import covers
import datafile
import names
import packages
import policy_extractor
from helpers import (
    Calculator,
    DarkCheckBoxBorderStyle,
    ThemeSwitch,
    apply_theme,
    extract_text_from_pdf,
    resource_path,
    show_message,
    windows_is_dark,
)

UI_FILE = resource_path("receipt.ui")
DATA_FILE = r"\\DOM-SRV-01\DominoInsurance\software\record.json"
ARCHIVE_ROOT = r"\\DOM-SRV-01\DominoInsurance\Αρχείο"
SIGNOSIGN_EXE = r"C:\Program Files\signotec\signoSign2\signoSign2.exe"
TEMPLATE_EISPRAXI = resource_path("resource", "eispraxi_template.docx")
TEMPLATE_PARALABI = resource_path("resource", "paralabi_template.docx")
RADIO_GRP_MAPPING = {
    -2: 1,
    -3: 3,
    -4: 6,
    -5: 12,
    -6: 0
}
VERSION = "2.4.0"


CUSTOMER_KEY_ROLE = Qt.ItemDataRole.UserRole + 1


def open_pdf(pdf_filepath):
    """Open in signoSign2 if installed, otherwise in the default PDF viewer."""
    if os.path.isfile(SIGNOSIGN_EXE):
        subprocess.Popen([SIGNOSIGN_EXE, pdf_filepath])
    else:
        os.startfile(pdf_filepath)


class CustomerCompleter(QCompleter):
    """Matches typed text against name keys, but inserts the real name."""

    def splitPath(self, path):
        return [names.name_key(path)]

    def pathFromIndex(self, index):
        return index.data(Qt.ItemDataRole.DisplayRole)


class Receipt(QMainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        uic.loadUi(UI_FILE, self)

        self.receipt_number = 0
        self.insurance_companies = []
        self.insurance_ra = []
        self.insurance_legal = []
        self.insurance_extra_covers = []
        self.insurance_types = []
        self.customers = []
        self.customer_index = {}
        self.json_data = None
        self.data_encoding = datafile.LEGACY_ENCODING
        self.doc_entries = []

        self.settings = QSettings("DOMINO", "Receipt")
        self.files_by_group = {
            "main": [],
            "extra": [],
        }
        self.amounts = {}
        self.used_files = {}
        self.pdf_details = {}  # application-form data of the last main policy PDF
        self.pdf_details_customer = ""  # customer in the form when that PDF was read

        self.data_file = str(self.settings.value("data_file", DATA_FILE))
        self.templates_dir = str(
            self.settings.value("templates_dir", policy_extractor.TEMPLATES_DIR)
        )
        if not os.path.isdir(self.templates_dir):
            self.templates_dir = policy_extractor.TEMPLATES_DIR
        self.archive_root = str(
            self.settings.value("archive_root", ARCHIVE_ROOT)
        )
        self.templates = policy_extractor.load_templates(self.templates_dir)
        if not self.import_data(self.data_file, quiet=self.data_file != DATA_FILE):
            if self.data_file != DATA_FILE:
                self.data_file = DATA_FILE
                self.import_data(self.data_file)

        self.set_theme_switch()
        self.set_ui()
        self.set_signals()

    def set_theme_switch(self):
        self.action_follow_windows.setChecked(
            self.settings.value("follow_windows", True, type=bool)
        )

        self.theme_switch = ThemeSwitch()

        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(6, 0, 8, 0)
        layout.setSpacing(4)
        layout.addWidget(QLabel("☀"))
        layout.addWidget(self.theme_switch)
        layout.addWidget(QLabel("☾"))
        self.menubar.setCornerWidget(container, Qt.Corner.TopRightCorner)

        # keep a reference; setStyle() doesn't take ownership
        self.chk_money_receipt_style = DarkCheckBoxBorderStyle()
        self.chk_money_receipt.setStyle(self.chk_money_receipt_style)

        self.update_theme()

    def update_theme(self):
        follow_windows = self.action_follow_windows.isChecked()
        dark_mode = windows_is_dark() if follow_windows else None
        if dark_mode is None:
            dark_mode = self.settings.value("dark_mode", True, type=bool)

        # don't let the switch save the Windows mode as the manual choice
        self.theme_switch.blockSignals(True)
        self.theme_switch.setChecked(dark_mode)
        self.theme_switch.blockSignals(False)
        self.theme_switch.setEnabled(not follow_windows)

        apply_theme(dark_mode)

    def set_ui(self):
        self.action_tray1.setChecked(False)
        self.lbl_date.setText(QDate.currentDate().toString("dd/MM/yyyy"))
        self.lineedit_amount.installEventFilter(self)
        self._enable_drop_target(self.groupBox)
        self._enable_drop_target(self.groupBox_3)
        # self.lineedit_amount.setValidator(double_validator())
        self.lineedit_customer.setFocus()
        self.lineedit_legal_policy.setEnabled(False)
        self.lineedit_ra_policy.setEnabled(False)
        self.populate_from_data()
        self.radio6.setChecked(True)
        self.date_start.setDate(QDate.currentDate())
        self.date_end.setDate(QDate.currentDate().addMonths(6))

        for cmb in self.findChildren(QComboBox):
            cmb.setCurrentIndex(-1)

    def set_signals(self):
        self.action_print_doc_receipt.triggered.connect(self.print_doc_receipt)
        self.action_print_money_receipt.triggered.connect(self.print_money_receipt)
        self.action_version.triggered.connect(self.about)
        self.action_json.triggered.connect(self.choose_data_file)
        self.actionOCR_Templates.triggered.connect(self.choose_templates_dir)
        self.action_archive_root.triggered.connect(self.choose_archive_root)
        self.cmb_insurance_company.currentTextChanged.connect(self.check_insurance)
        self.cmb_insurance_extra_covers.currentIndexChanged.connect(self.check_extra_covers)
        self.cmb_insurance_legal.currentIndexChanged.connect(self.check_legal)
        self.cmb_insurance_ra.currentIndexChanged.connect(self.check_ra)
        self.cmb_insurance_type.currentTextChanged.connect(self.check_type)
        self.lineedit_amount.editingFinished.connect(self.format_currency)
        self.lineedit_customer.editingFinished.connect(self.update_customer_list)
        self.button_grp_length.buttonClicked.connect(self.calculate_end_date)
        self.date_start.editingFinished.connect(self.calculate_end_date)
        self.btn_reset.clicked.connect(self.clear_ui)
        self.btn_create_documents.clicked.connect(self.create_documents)
        self.btn_exit.clicked.connect(QCoreApplication.instance().quit)
        self.btn_print.clicked.connect(self.open_application)
        self.theme_switch.toggled.connect(self.toggle_theme)
        self.action_follow_windows.toggled.connect(self.toggle_follow_windows)
        QGuiApplication.styleHints().colorSchemeChanged.connect(
            self.windows_theme_changed
        )

    def toggle_theme(self, dark_mode):
        apply_theme(dark_mode)
        self.settings.setValue("dark_mode", dark_mode)

    def toggle_follow_windows(self, follow_windows):
        self.settings.setValue("follow_windows", follow_windows)
        self.update_theme()

    def windows_theme_changed(self):
        if self.action_follow_windows.isChecked():
            self.update_theme()

    def eventFilter(self, watched, event):
        if watched == self.lineedit_amount and \
          event.type() == QEvent.Type.MouseButtonDblClick:
            self.open_calculator()

        drop_group = self._get_drop_group(watched)
        if drop_group:
            if event.type() in (
                QEvent.Type.DragEnter,
                QEvent.Type.DragMove,
            ) and event.mimeData().hasUrls():
                event.acceptProposedAction()
                return True

            if event.type() == QEvent.Type.Drop and event.mimeData().hasUrls():
                dropped_urls = event.mimeData().urls()
                dropped_files = self._extract_local_file_paths(dropped_urls)
                pdf_paths = [
                    path for path in dropped_files
                    if path.lower().endswith(".pdf")
                ]
                if pdf_paths:
                    self._autofill_from_pdfs(pdf_paths, drop_group)
                    event.acceptProposedAction()
                    return True

        return super().eventFilter(watched, event)

    def _autofill_from_pdfs(self, pdf_paths, zone):
        """Fill the form from every dropped PDF that has a template.

        Main box: one policy only, so only the last PDF is used. Extra box: any
        number of PDFs; each fills the RA / legal / extra-covers row of its own
        kind (a later PDF of the same kind replaces the earlier one).
        """
        notes = []
        if zone == "main" and len(pdf_paths) > 1:
            notes.append(
                "Χρησιμοποιήθηκε μόνο το τελευταίο αρχείο: "
                + os.path.basename(pdf_paths[-1])
            )
            pdf_paths = pdf_paths[-1:]

        unmatched, missing_msgs, kinds_seen = [], [], {}
        for path in pdf_paths:
            name = os.path.splitext(os.path.basename(path))[0]
            text, _status, error = extract_text_from_pdf(path)
            result = self._autofill_from_text(text, zone)
            if result is None:
                unmatched.append(f"{name} ({error})" if error else name)
                continue

            kind = result["kind"]
            if kind in kinds_seen:
                notes.append(
                    f"Τα αρχεία {kinds_seen[kind]} και {name} είναι ίδιου τύπου - "
                    f"χρησιμοποιήθηκε το {name}"
                )
            kinds_seen[kind] = name
            self.used_files[kind] = name
            if result["missing"]:
                missing_msgs.append(f"{name}: " + ", ".join(result["missing"]))

        self.files_by_group["main"] = [self.used_files["main"]] if "main" in self.used_files else []
        self.files_by_group["extra"] = sorted(
            (name for kind, name in self.used_files.items() if kind != "main"),
            key=str.casefold,
        )
        self._update_files_used_label()

        status = notes + (["Δεν βρέθηκαν: " + " | ".join(missing_msgs)] if missing_msgs else [])
        if status:
            self.statusbar.showMessage(" - ".join(status), 15000)
        if unmatched:
            show_message(
                "Δεν βρέθηκε πρότυπο για: " + ", ".join(unmatched) + "\n"
                "Παρακαλώ συμπληρώστε τη φόρμα χειροκίνητα.",
                msg_details="\n".join(notes) or None,
                msg_type="Warning",
            )

    @staticmethod
    def _parse_amount(text):
        """'1.234,56' -> 1234.56"""
        return float(text.replace(".", "").replace(",", "."))

    def _update_total(self):
        """Show the sum of the amounts of all policies filled from PDFs."""
        if not self.amounts:
            return
        total = f"{sum(self.amounts.values()):,.2f}"
        self.lineedit_amount.setText(
            total.replace(",", "_").replace(".", ",").replace("_", ".")
        )

    def _autofill_from_text(self, text, zone):
        """Fill the form from a matching template.

        Returns None if no template applies to this zone, else
        {"kind": "main"|"ra"|"legal"|"extra_covers", "missing": [fields]}.
        """
        template = policy_extractor.detect(text, self.templates)
        if not template or template.get("zone", "main") != zone:
            return None

        values = policy_extractor.extract(text, template)
        details = policy_extractor.extract_details(text, template)  # `text` is reused below
        missing = [field for field, value in values.items() if value is None]

        if zone == "main":
            kind = "main"
            self._select_combo(self.cmb_insurance_company, template.get("company"))
            # selecting the company resets the type, so set the type afterwards
            self._select_combo(self.cmb_insurance_type, template.get("insurance_type"))
            policy_edit = self.lineedit_policy
        else:
            kind = template.get("extra_kind")
            combo, policy_edit = {
                "ra": (self.cmb_insurance_ra, self.lineedit_ra_policy),
                "legal": (self.cmb_insurance_legal, self.lineedit_legal_policy),
                "extra_covers": (
                    self.cmb_insurance_extra_covers,
                    self.lineedit_extra_covers_policy,
                ),
            }.get(kind, (None, None))
            if combo is None:
                return None
            self._select_combo(combo, template.get("company"))

        simple_fields = {
            "policy": policy_edit,
            "plate": self.lineedit_plate if zone == "main" else None,
            "customer": self.lineedit_customer if zone == "main" else None,
        }
        for field, widget in simple_fields.items():
            if widget is not None and values.get(field):
                text = values[field]
                if field == "customer":
                    text = names.find_name(self.customer_index, text) or text
                widget.setText(text)

        if zone == "main":
            self.pdf_details = dict(details, plate=values["plate"]) if values.get("plate") else details
            self.pdf_details_customer = self.lineedit_customer.text().strip()

        self.amounts.pop(kind, None)
        if values.get("amount"):
            self.amounts[kind] = self._parse_amount(values["amount"])
        self._update_total()

        if zone == "main" and (values.get("start") or values.get("end")):
            start = QDate.fromString(values["start"], "dd/MM/yyyy") if values.get("start") else None
            end = QDate.fromString(values["end"], "dd/MM/yyyy") if values.get("end") else None
            # setChecked() doesn't emit buttonClicked, so the PDF's end date is kept
            if start:
                self.date_start.setDate(start)
            if start and end:
                self.date_end.setDate(end)
                self._duration_radio(start, end).setChecked(True)
            elif end:
                self.date_end.setDate(end)
                self.radio_free.setChecked(True)
            else:
                self.calculate_end_date()  # only a start date: end = start + selected duration

        return {"kind": kind, "missing": missing}

    def _duration_radio(self, start, end):
        """Radio matching the policy length, or radio_free if it fits none."""
        for radio, months in (
            (self.radio1, 1),
            (self.radio3, 3),
            (self.radio6, 6),
            (self.radio12, 12),
        ):
            if start.addMonths(months) == end:
                return radio
        return self.radio_free

    def _select_combo(self, combo, name):
        if not name:
            return
        index = combo.findText(name, Qt.MatchFlag.MatchFixedString)  # case-insensitive
        if index >= 0:
            combo.setCurrentIndex(index)
        else:
            self.statusbar.showMessage(f"Δεν βρέθηκε στη λίστα: {name}", 10000)

    def _enable_drop_target(self, widget):
        widget.setAcceptDrops(True)
        widget.installEventFilter(self)

        for child in widget.findChildren(QWidget):
            child.setAcceptDrops(True)
            child.installEventFilter(self)

    def _get_drop_group(self, widget):
        current_widget = widget

        while current_widget:
            if current_widget == self.groupBox_3:
                return "main"
            if current_widget == self.groupBox:
                return "extra"
            current_widget = current_widget.parentWidget()

        return None

    def _extract_file_stems(self, urls):
        return [
            os.path.splitext(os.path.basename(url.toLocalFile()))[0]
            for url in urls
            if url.isLocalFile()
        ]

    def _extract_local_file_paths(self, urls):
        return [
            url.toLocalFile()
            for url in urls
            if url.isLocalFile()
        ]

    def _update_files_used_label(self):
        label_files = self.files_by_group["main"] + self.files_by_group["extra"]
        self.lbl_files_used.setText(" | ".join(label_files) if label_files else "-")

    def clear_ui(self):
        self.files_by_group = {
            "main": [],
            "extra": [],
        }
        self.amounts = {}
        self.used_files = {}
        self.pdf_details = {}
        self.pdf_details_customer = ""
        self.statusbar.clearMessage()
        self._update_files_used_label()

        for lineedit in self.findChildren(QLineEdit):
            lineedit.clear()

        for cmb in self.findChildren(QComboBox):
            cmb.clear()

        for chk in self.findChildren(QCheckBox):
            if chk is not self.theme_switch:
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

    def import_data(self, json_file, quiet=False):
        """Load json_file; on failure keep current data and return False."""
        try:
            data, encoding = datafile.read_data(json_file)
            receipt_number = datafile.next_number(data)
            lists = {
                key: [item["name"] for item in data[key]]
                for key in (
                    "customer",
                    "insurance_company",
                    "insurance_ra",
                    "insurance_legal",
                    "insurance_extra_covers",
                    "insurance_type",
                )
            }
        except (OSError, ValueError, KeyError, TypeError) as e:
            if not quiet:
                show_message(
                    f"Unable to open data file. \n{e!r}",
                    msg_title="Error",
                    msg_type="Critical",
                )
            return False

        self.json_data = data
        self.data_encoding = encoding
        self.receipt_number = receipt_number
        self.customers = sorted(lists["customer"])
        self.insurance_companies = sorted(lists["insurance_company"])
        self.insurance_ra = sorted(lists["insurance_ra"])
        self.insurance_legal = sorted(lists["insurance_legal"])
        self.insurance_extra_covers = sorted(lists["insurance_extra_covers"])
        self.insurance_types = lists["insurance_type"]
        return True

    def populate_from_data(self):
        self.lbl_receipt_number.setText(str(self.receipt_number))
        self._refresh_customers()
        for cmb, items in (
            (self.cmb_insurance_company, self.insurance_companies),
            (self.cmb_insurance_type, self.insurance_types),
            (self.cmb_insurance_ra, self.insurance_ra),
            (self.cmb_insurance_legal, self.insurance_legal),
            (self.cmb_insurance_extra_covers, self.insurance_extra_covers),
        ):
            cmb.blockSignals(True)
            cmb.clear()
            cmb.addItems(items)
            cmb.setCurrentIndex(-1)
            cmb.blockSignals(False)

    def choose_data_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Διαδρομή αρχείου json",
            self.data_file,
            "JSON (*.json);;Όλα τα αρχεία (*)",
        )
        if not path:
            return
        if not self.import_data(path):
            return
        self.data_file = path
        self.settings.setValue("data_file", path)
        self.populate_from_data()

    def choose_templates_dir(self):
        path = QFileDialog.getExistingDirectory(
            self, "Διαδρομή φακέλου templates", self.templates_dir
        )
        if not path:
            return
        templates = policy_extractor.load_templates(path)
        if not templates:
            show_message(
                "Δεν βρέθηκαν templates (*.json) στον φάκελο.",
                msg_type="Warning",
            )
            return
        self.templates_dir = path
        self.templates = templates
        self.settings.setValue("templates_dir", path)

    def choose_archive_root(self):
        path = QFileDialog.getExistingDirectory(
            self, "Διαδρομή φακέλου αποθήκευσης αρχείων", self.archive_root
        )
        if not path:
            return
        self.archive_root = os.path.normpath(path)
        self.settings.setValue("archive_root", self.archive_root)

    def _refresh_customers(self):
        """Rebuild the match index and the accent/case-insensitive completer."""
        self.customer_index = names.build_index(self.customers)
        model = QStandardItemModel(self)
        for name in self.customers:
            item = QStandardItem(name)
            item.setData(names.name_key(name), CUSTOMER_KEY_ROLE)
            model.appendRow(item)
        completer = CustomerCompleter(model, self)
        completer.setCompletionRole(CUSTOMER_KEY_ROLE)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.lineedit_customer.setCompleter(completer)

    def update_customer_list(self):
        customer_name = self.lineedit_customer.text().strip()
        canonical = names.find_name(self.customer_index, customer_name)
        if canonical:
            if canonical != self.lineedit_customer.text():
                self.lineedit_customer.setText(canonical)
            return
        if customer_name and customer_name not in self.customers:
            ans = show_message(
                f"Ο Πελάτης {customer_name} δεν βρέθηκε στη λίστα... \nΝα γίνει νέα εγγραφή;",
                msg_type="Question"
            )
            if ans == QMessageBox.StandardButton.Yes:
                self.customers.append(customer_name)
                self._refresh_customers()

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

    def prepare_printing(self, paralabi=True, eispraxi=False):
        """Build the requested documents; returned in order PARALABI, EISPRAXI."""
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

        if self.lineedit_extra_covers_policy.text():
            company_text = company_text + ", " + self.cmb_insurance_extra_covers.currentText()
            policy_text = policy_text + ", " + self.lineedit_extra_covers_policy.text()

        if self.lineedit_ra_policy.text() or self.lineedit_legal_policy.text() or self.lineedit_extra_covers_policy.text():
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

        if paralabi:
            doc_path = os.path.join(tempfile.gettempdir(), "print_paralabi.docx")
            with MailMerge(TEMPLATE_PARALABI) as document:
                document.merge(**self.doc_entries)
                document.write(doc_path)

            print_docs.append(doc_path)
            #     os.path.join(
            #         os.path.dirname(os.path.realpath(__file__)),
            #         "print_paralabi.docx"
            #     )
            # )

        if eispraxi:
            if self.lineedit_ra_policy.text() or \
              self.lineedit_legal_policy.text() or \
                self.lineedit_extra_covers_policy.text():
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

            doc_path = os.path.join(tempfile.gettempdir(), "print_eispraxi.docx")

            with MailMerge(
                TEMPLATE_EISPRAXI,
                remove_empty_tables=False
            ) as document:
                document.merge(**self.doc_entries)
                document.write(doc_path)

            print_docs.append(doc_path)
        return print_docs

    def update_data_file(self):
        """Merge-save to disk; return True on success."""
        try:
            merged = datafile.save_merged(
                self.data_file, self.json_data, self.data_encoding
            )
        except (OSError, ValueError, KeyError, TypeError) as e:
            show_message(
                f"Unable to update data file. \n{e}",
                msg_type="Warning"
            )
            return False
        self._apply_saved(merged)
        return True

    def _apply_saved(self, merged):
        self.json_data = merged
        self.customers = sorted(c["name"] for c in merged["customer"])
        self._refresh_customers()
        self.receipt_number = datafile.next_number(merged)

    def reserve_receipt_number(self):
        """Claim a receipt number on disk before it is printed.

        Returns the number, or None (and prints nothing) if the reservation
        cannot be saved, so two instances never print the same number.
        """
        try:
            merged, number = datafile.reserve_id(
                self.data_file, self.json_data, self.data_encoding
            )
        except (OSError, ValueError, KeyError, TypeError) as e:
            show_message(
                f"Unable to reserve receipt number. \n{e}",
                msg_type="Warning"
            )
            return None
        self._apply_saved(merged)
        self.lbl_receipt_number.setText(str(number))
        return number

    def release_receipt_number(self, number):
        """Return an unprinted receipt number to the pool so it is not skipped."""
        try:
            merged = datafile.release_id(
                self.data_file, number, self.json_data, self.data_encoding
            )
        except (OSError, ValueError, KeyError, TypeError) as e:
            show_message(
                f"Receipt number {number} was not printed and could not be "
                f"released. It will be skipped. \n{e}",
                msg_type="Warning"
            )
            return
        self._apply_saved(merged)
        self.show_next_receipt_number()

    def show_next_receipt_number(self):
        self.lbl_receipt_number.setText(str(self.receipt_number))

    def print_money_receipt(self):
        """Print only the EISPRAXI document, regardless of the checkbox."""
        number = self.reserve_receipt_number()
        if number is None:
            return
        printed = False
        try:
            print_docs = self.prepare_printing(paralabi=False, eispraxi=True)
            self.print_document(
                print_docs[0],
                tray_number=260,
                black_ink_only=True
            )
            printed = True
        finally:
            if printed:
                self.show_next_receipt_number()
            else:
                self.release_receipt_number(number)

    def print_doc_receipt(self):
        """Print only the PARALABI document, regardless of the checkbox."""
        print_docs = self.prepare_printing(paralabi=True, eispraxi=False)

        print_tray = 259
        if self.action_tray1.isChecked():
            print_tray = 260

        self.print_document(print_docs[0], print_tray, black_ink_only=True)

    def print_document(self, document, tray_number, black_ink_only):
        info_w = show_message(
            msg_text="Εκτύπωση εγγράφων...",
            msg_type="no_buttons"
        )

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

        info_w.accept()

    def create_documents(self):

        info_w = show_message(
            msg_text="Προετοιμασία εγγράφων...",
            msg_type="no_buttons"
        )

        money_receipt = self.chk_money_receipt.isChecked()
        number = None
        if money_receipt:
            number = self.reserve_receipt_number()
            if number is None:
                info_w.accept()
                return

        printed = False
        try:
            printed = self._print_documents(info_w, money_receipt)
        finally:
            if money_receipt:
                if printed:
                    self.show_next_receipt_number()
                else:
                    self.release_receipt_number(number)

    def _archive_location(self, prefix):
        """(folder, file name) in the archive for a document of the current form."""
        pdf_dir = os.path.join(
            self.archive_root,
            self.lineedit_customer.text(),
            "receipts",
        )
        date_format = ".".join(
            reversed(self.date_start.date().toString("dd/MM/yyyy").split("/"))
        )
        subject = self.lineedit_plate.text() or self.cmb_insurance_type.currentText()
        return pdf_dir, f"{prefix}{subject}_{date_format}.pdf"

    def _saved_customer(self, name):
        """The customer's entry in the data file (name only if never stored)."""
        return next(
            (c for c in self.json_data["customer"] if c["name"] == name),
            {"name": name},
        )

    def _pdf_details_for(self, customer_name):
        """Details of the dropped policy PDF, unless the customer was changed since."""
        changed = self.pdf_details_customer and (
            names.name_key(self.pdf_details_customer) != names.name_key(customer_name)
        )
        if changed:
            return {}
        return self.pdf_details

    def open_application(self):
        """Collect the data of an insurance application, then save or print it."""
        customer_name = self.lineedit_customer.text().strip()
        insurance_type = self.cmb_insurance_type.currentText()
        if not customer_name or not insurance_type or not self.cmb_insurance_company.currentText():
            show_message(
                "Συμπληρώστε πελάτη, ασφαλιστική εταιρία και κλάδο πριν την αίτηση.",
                msg_type="Warning",
            )
            return

        extra_companies = sorted(
            set(self.insurance_ra + self.insurance_legal + self.insurance_extra_covers)
        )
        extra_rows = [
            cmb.currentText()
            for cmb in (
                self.cmb_insurance_ra,
                self.cmb_insurance_legal,
                self.cmb_insurance_extra_covers,
            )
            if cmb.currentText()
        ]
        company = self.cmb_insurance_company.currentText()
        # packages and cover catalogues live next to record.json and are read on every use
        company_packages, problems = packages.load(packages.path(self.data_file))
        cover_catalogs, cover_problems = covers.load(self.data_file)
        problems += cover_problems
        if problems:
            show_message(
                "Προβλήματα στα αρχεία πακέτων / καλύψεων (τα στοιχεία αυτά δεν εμφανίζονται):",
                msg_details="\n".join(problems),
                msg_type="Warning",
            )
        dialog = application_dialog.ApplicationDialog(
            {
                "type": insurance_type,
                "company": self.cmb_insurance_company.currentText(),
                "start": self.date_start.date().toString("dd/MM/yyyy"),
                "end": self.date_end.date().toString("dd/MM/yyyy"),
                "amount": self.lineedit_amount.text(),
                "date": QDate.currentDate().toString("dd/MM/yyyy"),
                "customer": self._saved_customer(customer_name),
                "plate": self.lineedit_plate.text().strip(),
                "packages": packages.for_company(company_packages, company, insurance_type),
                "pdf_details": self._pdf_details_for(customer_name),
                "extra_companies": extra_companies,
                "extra_rows": extra_rows,
                "catalogs": cover_catalogs,
            },
            self,
        )
        action = dialog.exec()
        if not action:
            return

        self._save_customer_details(
            customer_name,
            dialog.customer_fields(),
            dialog.vehicle_fields(),
            dialog.replaced_plate,
        )
        data = dialog.application_data()
        if action == dialog.PRINT:
            printer = QPrinter()
            if QPrintDialog(printer, self).exec():
                application_pdf.print_document(application_pdf.build_document(data), printer)
        else:
            self._archive_application(data)

    def _save_customer_details(self, name, fields, vehicle, replaced_plate=None):
        """Store the application data on the customer; failures are only reported.

        The vehicle replaces the saved one with the same plate (ignoring case,
        spaces and Latin/Greek lookalike letters), and `replaced_plate` if given.
        """
        fields = dict(fields)
        if vehicle is not None and vehicle.get("plate"):
            replaced = {policy_extractor.normalise_plate(p) for p in (vehicle["plate"], replaced_plate)}
            vehicles = [
                v for v in self._saved_customer(name).get("vehicles", [])
                if policy_extractor.normalise_plate(v.get("plate")) not in replaced
            ]
            fields["vehicles"] = vehicles + [{k: v for k, v in vehicle.items() if v}]
        try:
            merged = datafile.update_customer(
                self.data_file, name, fields, self.json_data, self.data_encoding
            )
        except (OSError, ValueError, KeyError, TypeError) as e:
            show_message(
                f"Δεν αποθηκεύτηκαν τα στοιχεία του πελάτη.\n{e}",
                msg_type="Warning",
            )
            return
        self._apply_saved(merged)

    def _archive_application(self, data):
        pdf_dir, pdf_filename = self._archive_location("ΑΙΤΗΣΗ_")
        pdf_filepath = os.path.join(pdf_dir, pdf_filename)

        if not os.path.isdir(pdf_dir):
            reply = show_message(
                f"New directory will be created:\n{pdf_dir}",
                msg_type="YesNo",
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
            try:
                os.makedirs(pdf_dir)
            except OSError as e:
                show_message(
                    f"Unable to create directories\n{pdf_dir}",
                    msg_type="Critical",
                    msg_title="Error",
                    msg_details=f"{e}",
                )
                return
        elif os.path.exists(pdf_filepath):
            reply = show_message(
                f"Το αρχείο υπάρχει ήδη:\n{pdf_filepath}\n\nΑντικατάσταση;",
                msg_type="YesNo",
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        try:
            application_pdf.write_pdf(data, pdf_filepath)
        except OSError as e:
            show_message(
                f"Unable to save file\n{pdf_filepath}\n{e}",
                msg_title="Error",
                msg_type="Critical",
            )
            return

        reply = show_message(
            f"Το αρχείο PDF αποθηκεύτηκε:\n{pdf_filepath}\n\nΆνοιγμα για υπογραφή τώρα;",
            msg_type="YesNo",
        )
        if reply == QMessageBox.StandardButton.Yes:
            open_pdf(pdf_filepath)

    def _print_documents(self, info_w, money_receipt):
        """Build, archive and print the documents; True if the money receipt printed."""

        def _save_pdf_file(pdf_filepath):
            """Save the paralabi as PDF; False if it failed (already reported)."""
            word = doc = None
            try:
                word = client.Dispatch("Word.Application")
                doc = word.Documents.Open(print_docs[0])
                doc.SaveAs(pdf_filepath, FileFormat=17)  # FileFormat for PDF
            except Exception as e:
                show_message(
                    f"Unable to save file\n{pdf_filepath}\n{e}",
                    msg_title="Error",
                    msg_type="Critical"
                )
                return False
            finally:
                # Best effort: only close what was actually opened.
                if doc is not None:
                    try:
                        doc.Close()
                    except Exception:
                        pass
                if word is not None:
                    try:
                        word.Quit()
                    except Exception:
                        pass

            msg_reply = show_message(
                f"Το αρχείο PDF αποθηκεύτηκε:\n{pdf_filepath}\n\n"
                "Άνοιγμα για υπογραφή τώρα;",
                msg_type="YesNo"
            )
            if msg_reply == QMessageBox.StandardButton.Yes:
                open_pdf(pdf_filepath)
            return True

        print_docs = self.prepare_printing(paralabi=True, eispraxi=money_receipt)

        pdf_dir, pdf_filename = self._archive_location("ΑΠΟΔΕΙΞΗ_")
        pdf_filepath = os.path.join(pdf_dir, pdf_filename)

        if os.path.isdir(pdf_dir):
            target_pdf = pdf_filepath
        else:
            msg_reply = show_message(
                f"New directory will be created:\n{pdf_dir}",
                msg_type="Question"
            )
            if msg_reply == QMessageBox.StandardButton.Yes:
                try:
                    os.makedirs(pdf_dir)
                except OSError as e:
                    show_message(
                        f"Unable to create directories\n{pdf_dir}",
                        msg_type="Critical",
                        msg_title="Error",
                        msg_details=f"{e}"
                    )
                    info_w.accept()
                    return False
                target_pdf = pdf_filepath
            elif msg_reply == QMessageBox.StandardButton.No:
                doc_path = print_docs[0].rsplit(".", 1)
                target_pdf = doc_path[0] + ".pdf"
            else:
                # Cancel: nothing archived, nothing printed.
                info_w.accept()
                return False

        # A failed save stops the action here, so no receipt number is used
        # for a document that was never archived.
        if not _save_pdf_file(target_pdf):
            info_w.accept()
            return False

        printed = False
        if money_receipt:
            self.print_document(
                print_docs[1],
                tray_number=260,
                black_ink_only=True
            )
            printed = True

        info_w.accept()
        return printed

    def check_insurance(self, insurance):
        if insurance in ["ARAG", "MEDITERRANIA"]:
            self.cmb_insurance_type.setCurrentText("ΝΟΜΙΚΗΣ ΠΡΟΣΤΑΣΙΑΣ")
        elif insurance == "MONDIAL ASSISTANCE":
            self.cmb_insurance_type.setCurrentText("ΤΑΞΙΔΙΩΤΙΚΗΣ ΑΣΦΑΛΙΣΗΣ")
        else:
            self.cmb_insurance_type.setCurrentText("ΑΥΤΟΚΙΝΗΤΟΥ")

    def check_type(self, ins_type):
        if ins_type not in [
            "ΑΥΤΟΚΙΝΗΤΟΥ",
            "ΝΟΜΙΚΗΣ ΠΡΟΣΤΑΣΙΑΣ","ΟΔΙΚΗΣ ΒΟΗΘΕΙΑΣ"
        ]:
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

    def check_extra_covers(self, extra_covers):
        if extra_covers == -1:
            self.lineedit_extra_covers_policy.setEnabled(False)
        else:
            self.lineedit_extra_covers_policy.setEnabled(True)

    def about(self):
        show_message(
            f"Απόδειξη Παραλαβής και Είσπραξης Ασφαλιστηρίου Συμβολαίου \
                v{VERSION} - DOMINO GROUP (2023)"
        )


if __name__ == "__main__":
    app = QApplication(sys.argv)

    app.setStyle(QStyleFactory.create("Fusion"))

    # pyi_splash.close()

    window = Receipt()
    window.show()
    app.exec()
