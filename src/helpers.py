import os

from PyQt6.QtCore import QLocale, QPoint, QRectF, QSize, Qt
from PyQt6.QtGui import (
    QColor,
    QDoubleValidator,
    QGuiApplication,
    QPainter,
    QPalette,
)
from PyQt6 import uic
from PyQt6.QtWidgets import *


def dark_palette():
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(45, 45, 45))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(208, 208, 208))
    palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(208, 208, 208))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(25, 25, 25))
    palette.setColor(QPalette.ColorRole.Text, QColor(208, 208, 208))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(128, 128, 128))
    palette.setColor(QPalette.ColorRole.Button, QColor(45, 45, 45))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(208, 208, 208))
    palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
    palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Light, QColor(75, 75, 75))
    palette.setColor(QPalette.ColorRole.Midlight, QColor(60, 60, 60))
    palette.setColor(QPalette.ColorRole.Mid, QColor(95, 95, 95))
    palette.setColor(QPalette.ColorRole.Dark, QColor(30, 30, 30))
    palette.setColor(QPalette.ColorRole.Shadow, QColor(20, 20, 20))

    disabled = QPalette.ColorGroup.Disabled
    palette.setColor(disabled, QPalette.ColorRole.WindowText, QColor(110, 110, 110))
    palette.setColor(disabled, QPalette.ColorRole.Text, QColor(110, 110, 110))
    palette.setColor(disabled, QPalette.ColorRole.ButtonText, QColor(110, 110, 110))
    palette.setColor(disabled, QPalette.ColorRole.Base, QColor(45, 45, 45))
    return palette


def light_palette():
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(240, 240, 240))
    palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.black)
    palette.setColor(QPalette.ColorRole.Base, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(245, 245, 245))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 220))
    palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.black)
    palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.black)
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(128, 128, 128))
    palette.setColor(QPalette.ColorRole.Button, QColor(240, 240, 240))
    palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.black)
    palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
    palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Light, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Midlight, QColor(227, 227, 227))
    palette.setColor(QPalette.ColorRole.Mid, QColor(160, 160, 160))
    palette.setColor(QPalette.ColorRole.Dark, QColor(160, 160, 160))
    palette.setColor(QPalette.ColorRole.Shadow, QColor(105, 105, 105))

    disabled = QPalette.ColorGroup.Disabled
    palette.setColor(disabled, QPalette.ColorRole.WindowText, QColor(150, 150, 150))
    palette.setColor(disabled, QPalette.ColorRole.Text, QColor(150, 150, 150))
    palette.setColor(disabled, QPalette.ColorRole.ButtonText, QColor(150, 150, 150))
    palette.setColor(disabled, QPalette.ColorRole.Base, QColor(240, 240, 240))
    return palette


def apply_theme(dark):
    QApplication.instance().setPalette(dark_palette() if dark else light_palette())


def windows_is_dark():
    """True/False for the Windows light/dark setting, None if unknown."""
    scheme = QGuiApplication.styleHints().colorScheme()
    if scheme == Qt.ColorScheme.Dark:
        return True
    if scheme == Qt.ColorScheme.Light:
        return False
    return None


class DarkCheckBoxBorderStyle(QProxyStyle):
    """Fusion style that draws the check box border in the same color as the
    other controls' outlines on light themes (Fusion draws it lighter)."""

    def __init__(self):
        super().__init__("Fusion")

    def drawPrimitive(self, element, option, painter, widget=None):
        super().drawPrimitive(element, option, painter, widget)

        if element == QStyle.PrimitiveElement.PE_IndicatorCheckBox and \
          option.palette.color(QPalette.ColorRole.Window).lightness() > 128:
            painter.save()
            painter.setBrush(Qt.BrushStyle.NoBrush)
            # same outline color Fusion uses for line edits and combo boxes
            painter.setPen(
                option.palette.color(QPalette.ColorRole.Window).darker(140)
            )
            painter.drawRect(option.rect.adjusted(0, 0, -1, -1))
            painter.restore()


class ThemeSwitch(QCheckBox):
    """Sliding on/off switch. Checked means dark mode."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Light / Dark mode")

    def sizeHint(self):
        return QSize(36, 18)

    def hitButton(self, pos: QPoint):
        return self.contentsRect().contains(pos)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        if not self.isEnabled():
            painter.setOpacity(0.5)

        rect = QRectF(self.contentsRect())
        radius = rect.height() / 2

        if self.isChecked():
            track_color = self.palette().color(QPalette.ColorRole.Highlight)
        else:
            track_color = self.palette().color(QPalette.ColorRole.Mid)
        painter.setBrush(track_color)
        painter.drawRoundedRect(rect, radius, radius)

        knob_margin = 2
        knob_diameter = rect.height() - 2 * knob_margin
        knob_x = rect.right() - knob_margin - knob_diameter if self.isChecked() \
            else rect.left() + knob_margin
        painter.setBrush(QColor(255, 255, 255))
        painter.drawEllipse(
            QRectF(knob_x, rect.top() + knob_margin, knob_diameter, knob_diameter)
        )
        painter.end()


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
        msg_box.setStyleSheet("QDialog {border: 1px solid palette(mid);}")

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