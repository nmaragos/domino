import os

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

from PyQt6.QtCore import QLocale
from PyQt6.QtGui import QDoubleValidator
from PyQt6 import uic
from PyQt6.QtWidgets import *


def extract_text_from_pdf(pdf_path):
    if fitz is None:
        return (
            "",
            "",
            "PyMuPDF is not installed. Install package 'PyMuPDF' to enable PDF extraction.",
        )

    try:
        text_chunks = []
        ocr_pages = 0
        total_pages = 0
        ocr_errors = []
        with fitz.open(pdf_path) as pdf_doc:
            for page in pdf_doc:
                total_pages += 1
                page_text = page.get_text("text").strip()
                if page_text:
                    text_chunks.append(page_text)
                    continue

                ocr_text, ocr_error = extract_text_with_ocr(page)
                if ocr_text:
                    ocr_pages += 1
                    text_chunks.append(ocr_text)
                elif ocr_error:
                    ocr_errors.append(ocr_error)

        extracted_text = "\n".join(text_chunks).strip()
        if not extracted_text:
            if ocr_errors:
                return (
                    "",
                    "",
                    "No selectable text found. PyMuPDF OCR failed. Ensure Tesseract OCR is installed and accessible in PATH.",
                )
            return "", "", "No selectable text found in this PDF. It may be scanned, image-only, or protected."

        if ocr_pages:
            status_message = (
                f"Text extraction completed using OCR on {ocr_pages}/{total_pages} pages."
            )
        else:
            status_message = "Text extraction completed from embedded PDF text."
        return extracted_text, status_message, ""
    except Exception as exc:
        return "", "", f"Failed to extract text from PDF:\n{exc}"


def extract_text_with_ocr(page):
    try:
        if not hasattr(page, "get_textpage_ocr"):
            return "", "Installed PyMuPDF version does not support OCR API."

        text_page = page.get_textpage_ocr(language="ell+eng", dpi=300)
        ocr_text = page.get_text("text", textpage=text_page).strip()
        return ocr_text, ""
    except Exception as exc:
        return "", str(exc)


def show_pdf_text_preview(parent, pdf_path, extracted_text, status_message="", error_message=""):
    dialog = QDialog(parent)
    dialog.setWindowTitle("PDF Text Preview")
    dialog.resize(900, 650)

    layout = QVBoxLayout(dialog)

    file_label = QLabel(f"File: {pdf_path}")
    file_label.setWordWrap(True)
    layout.addWidget(file_label)

    if status_message:
        status_label = QLabel(status_message)
        status_label.setWordWrap(True)
        layout.addWidget(status_label)

    if error_message:
        error_label = QLabel(error_message)
        error_label.setWordWrap(True)
        layout.addWidget(error_label)

    text_preview = QPlainTextEdit(dialog)
    text_preview.setReadOnly(True)
    text_preview.setPlainText(extracted_text)
    layout.addWidget(text_preview)

    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
    buttons.rejected.connect(dialog.reject)
    buttons.accepted.connect(dialog.accept)
    buttons.button(QDialogButtonBox.StandardButton.Close).clicked.connect(dialog.close)
    layout.addWidget(buttons)

    dialog.exec()


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
        for lineedit in self.findChildren(QLineEdit):
            lineedit.setValidator(double_validator())

    def set_signals(self):
        self.buttonBox.accepted.connect(self.update_total) 
        self.lineedit_auto.textChanged.connect(self.calculate_total)
        self.lineedit_legal.textChanged.connect(self.calculate_total)
        self.lineedit_ra.textChanged.connect(self.calculate_total)
        self.lineedit_extra_covers.textChanged.connect(self.calculate_total)
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
            + float(self.lineedit_ra.text().replace(",", ".") or 0.00) \
            + float(self.lineedit_extra_covers.text().replace(",", ".") or 0.00)
        total_cost = "{:.2f}".format(total_cost)
        self.lbl_total_amount.setText(total_cost.replace(".", ","))