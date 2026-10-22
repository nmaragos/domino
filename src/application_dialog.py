"""Dialog that collects the data of an insurance application (Αίτηση)."""
import re
from html import escape

from PyQt6.QtCore import QDate, QEvent, QPoint, QRect, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QGuiApplication, QStandardItem, QStandardItemModel
from PyQt6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from application_pdf import (
    BASE_COVERS,
    CUSTOMER_FIELDS,
    OPTIONAL_COVERS,
    VEHICLE_FIELDS,
    VEHICLE_TYPE,
    WIDE_FIELDS,
)
from helpers import DarkCheckBoxBorderStyle, show_message
import names
from policy_extractor import canonical_usage, normalise_plate

FIELD_WIDTH = 230
MIN_WIDTH = 760
PDF_FILLED_STYLE = "QLineEdit {background-color: rgba(46, 160, 67, 0.18);}"
PDF_NOTE_STYLE = "QLabel {background-color: rgba(240, 160, 0, 0.25); padding: 6px; border-radius: 4px;}"
PDF_CONFLICT_STYLE = "QLineEdit {background-color: rgba(240, 160, 0, 0.25);}"
DATE_KEYS = ("birth", "license_date", "other_driver_birth", "other_driver_license_date")


class DateLineEdit(QLineEdit):
    """Date field that adds the slashes while typing: 01021980 -> 01/02/1980."""

    def __init__(self, text=""):
        super().__init__()
        self.setPlaceholderText("ηη/μμ/εεεε")
        self.setMaxLength(10)
        self.setText(text)
        self.textEdited.connect(self._format)

    def _format(self, text):
        digits = "".join(c for c in text if c.isdigit())[:8]
        parts = [digits[:2], digits[2:4], digits[4:]]
        formatted = "/".join(part for part in parts if part)
        if formatted != text:
            self.setText(formatted)


class FlowLayout(QLayout):
    """Lays widgets out left to right and wraps them onto new lines."""

    def __init__(self, parent=None, spacing=6):
        super().__init__(parent)
        self._items = []
        self.setSpacing(spacing)
        self.setContentsMargins(0, 0, 0, 0)

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, index):
        return self._items[index] if 0 <= index < len(self._items) else None

    def takeAt(self, index):
        return self._items.pop(index) if 0 <= index < len(self._items) else None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._arrange(QRect(0, 0, width, 0), apply=False)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._arrange(rect, apply=True)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        return size + QSize(margins.left() + margins.right(), margins.top() + margins.bottom())

    def _arrange(self, rect, apply):
        """Place the items inside `rect`; return the height used."""
        x, y, line_height = rect.x(), rect.y(), 0
        for item in self._items:
            hint = item.sizeHint()
            if x + hint.width() > rect.right() + 1 and line_height > 0:
                x, y, line_height = rect.x(), y + line_height + self.spacing(), 0
            if apply:
                item.setGeometry(QRect(QPoint(x, y), hint))
            x += hint.width() + self.spacing()
            line_height = max(line_height, hint.height())
        return y + line_height - rect.y()


class CheckableComboBox(QComboBox):
    """Drop-down with a check box per item; the list stays open while ticking."""

    changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._model = QStandardItemModel(self)
        self.setModel(self._model)
        self.setEditable(True)
        self.lineEdit().setReadOnly(True)
        self.lineEdit().setPlaceholderText("Επιλογή καλύψεων...")
        self.view().viewport().installEventFilter(self)
        self.lineEdit().installEventFilter(self)

    def set_items(self, names):
        self._model.clear()
        for name in names:
            item = QStandardItem(name)
            item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self._model.appendRow(item)
        self._refresh()

    def checked(self):
        return [
            self._model.item(i).text()
            for i in range(self._model.rowCount())
            if self._model.item(i).checkState() == Qt.CheckState.Checked
        ]

    def uncheck(self, name):
        for i in range(self._model.rowCount()):
            if self._model.item(i).text() == name:
                self._model.item(i).setCheckState(Qt.CheckState.Unchecked)
        self._refresh()
        self.changed.emit()

    def _refresh(self):
        self.setCurrentIndex(-1)
        count = len(self.checked())
        self.lineEdit().setText(f"Επιλεγμένες: {count}" if count else "")

    def eventFilter(self, watched, event):
        if watched is self.lineEdit() and event.type() == QEvent.Type.MouseButtonPress:
            self.showPopup()
            return True
        if watched is self.view().viewport() and event.type() == QEvent.Type.MouseButtonRelease:
            index = self.view().indexAt(event.position().toPoint())
            if index.isValid():
                item = self._model.itemFromIndex(index)
                item.setCheckState(
                    Qt.CheckState.Unchecked
                    if item.checkState() == Qt.CheckState.Checked
                    else Qt.CheckState.Checked
                )
                self._refresh()
                self.changed.emit()
            return True  # keep the popup open
        return super().eventFilter(watched, event)


class ExtraRow(QWidget):
    """One extra-cover line: company + covers (ticked from its catalogue or typed)."""

    def __init__(self, dialog, company=""):
        super().__init__()
        self.dialog = dialog
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.cmb_company = QComboBox()
        self.cmb_company.addItems([""] + dialog.extra_companies)
        self.cmb_company.setMinimumWidth(180)
        self.cmb_covers = CheckableComboBox()  # company has a catalogue
        self.edit_cover = QLineEdit()  # company without a catalogue
        self.covers_stack = QStackedWidget()
        self.covers_stack.addWidget(self.cmb_covers)
        self.covers_stack.addWidget(self.edit_cover)
        self.chips = QWidget()  # one removable tag per ticked cover
        self.chips_layout = FlowLayout(self.chips)
        covers_column = QVBoxLayout()
        covers_column.setSpacing(4)
        covers_column.addWidget(self.covers_stack)
        covers_column.addWidget(self.chips)
        self.btn_remove = QPushButton("✕")
        self.btn_remove.setFixedWidth(30)
        self.btn_remove.setToolTip("Αφαίρεση")

        layout.addWidget(self.cmb_company, 0, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(covers_column, 1)
        layout.addWidget(self.btn_remove, 0, Qt.AlignmentFlag.AlignTop)

        self.cmb_company.currentTextChanged.connect(self._company_changed)
        self.cmb_covers.changed.connect(self._rebuild_chips)
        self.btn_remove.clicked.connect(lambda: dialog.remove_extra_row(self))

        self.cmb_company.setCurrentIndex(max(self.cmb_company.findText(company), 0))
        self._company_changed(self.cmb_company.currentText())

    def _company_changed(self, company):
        catalog = self.dialog.catalogs.get(company)
        self.edit_cover.clear()
        if catalog:
            self.cmb_covers.set_items([c["name"] for c in catalog])
            self._rebuild_chips()
            self.covers_stack.setCurrentWidget(self.cmb_covers)
        else:
            self.covers_stack.setCurrentWidget(self.edit_cover)

    def _rebuild_chips(self):
        while self.chips_layout.count():
            self.chips_layout.takeAt(0).widget().deleteLater()
        for name in self.cmb_covers.checked():
            chip = QPushButton(f"{name}   ✕")
            chip.setFlat(True)
            chip.setCursor(Qt.CursorShape.PointingHandCursor)
            chip.setToolTip("Αφαίρεση")
            chip.setStyleSheet(
                "QPushButton {border: 1px solid palette(mid); border-radius: 10px;"
                " padding: 2px 10px; background: palette(alternate-base);}"
                "QPushButton:hover {border-color: palette(highlight);}"
            )
            chip.clicked.connect(lambda _=False, n=name: self.cmb_covers.uncheck(n))
            self.chips_layout.addWidget(chip)
        self.chips.updateGeometry()

    def company(self):
        return self.cmb_company.currentText().strip()

    def covers(self):
        if self.covers_stack.currentWidget() is self.cmb_covers:
            return self.cmb_covers.checked()
        text = self.edit_cover.text().strip()
        return [text] if text else []

    def values(self):
        return {"company": self.company(), "covers": self.covers()}


class ApplicationDialog(QDialog):
    PDF, PRINT = 1, 2

    def __init__(self, ctx, parent=None):
        """`ctx`: type, company, start, end, amount, date, customer (saved dict with
        "name"), plate, extra_companies, extra_rows (companies), catalogs."""
        super().__init__(parent)
        self.ctx = ctx
        self.is_vehicle = ctx["type"] == VEHICLE_TYPE
        self.extra_companies = ctx["extra_companies"]
        self.catalogs = ctx["catalogs"]
        self.customer = ctx["customer"]
        self.packages = ctx.get("packages", [])
        self.setWindowTitle("Αίτηση ασφάλισης " + ctx["type"])
        self._checkbox_style = DarkCheckBoxBorderStyle()  # setStyle() doesn't take ownership

        self.customer_edits = {}
        self.vehicle_edits = {}
        self.extra_rows = []

        content = QWidget()
        form = QVBoxLayout(content)
        form.addWidget(self._summary())
        self.conflict_note = QLabel()
        self.conflict_note.setTextFormat(Qt.TextFormat.RichText)
        self.conflict_note.setWordWrap(True)
        self.conflict_note.setStyleSheet(PDF_NOTE_STYLE)
        self.conflict_note.hide()
        form.addWidget(self.conflict_note)
        form.addWidget(self._customer_group())
        form.addWidget(self._asset_group())
        if self.is_vehicle:
            form.addWidget(self._covers_group())
        form.addStretch(1)

        self.content = content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(content)

        self.btn_pdf = QPushButton("Δημιουργία PDF")
        self.btn_print = QPushButton("Εκτύπωση")
        self.btn_cancel = QPushButton("Ακύρωση")
        self.btn_pdf.setDefault(True)
        self.btn_pdf.clicked.connect(lambda: self._finish(self.PDF))
        self.btn_print.clicked.connect(lambda: self._finish(self.PRINT))
        self.btn_cancel.clicked.connect(self.reject)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        for button in (self.btn_pdf, self.btn_print, self.btn_cancel):
            buttons.addWidget(button)

        layout = QVBoxLayout(self)
        layout.addWidget(scroll, 1)
        layout.addLayout(buttons)

        self._restore_vehicle(ctx.get("plate", ""))
        if self.is_vehicle:
            for company in ctx.get("extra_rows", ()):
                self.add_extra_row(company)
        self.pdf_conflicts = self._apply_pdf_details(ctx.get("pdf_details") or {})
        self._show_conflicts()
        self._fitted = False

    def showEvent(self, event):
        super().showEvent(event)
        if not self._fitted:  # sizes are only reliable once the widgets are shown
            self._fitted = True
            self._fit_to_content()

    @staticmethod
    def _same_value(a, b, key=""):
        if key == "usage":  # periods, spaces, Latin/Greek letters and "Ιδιωτική" = "ΕΙΧ" do not matter
            a, b = canonical_usage(a), canonical_usage(b)
        digits_a, digits_b = re.sub(r"\D", "", a), re.sub(r"\D", "", b)
        return names.name_key(a) == names.name_key(b) or (bool(digits_a) and digits_a == digits_b)

    def _apply_pdf_details(self, details):
        """Fill blank fields from the policy PDF (highlighted); keep what is already there.

        Returns [(label, current value, PDF value)] for fields where the PDF differs.
        """
        edits = dict(self.customer_edits)
        edits.update(self.vehicle_edits)
        labels = dict(CUSTOMER_FIELDS + VEHICLE_FIELDS)
        conflicts = []
        for key, value in details.items():
            edit = edits.get(key)
            if edit is None:
                continue
            current = edit.text().strip()
            if key == "plate":  # prefilled from the receipt window: green if the PDF gave it for a new car
                if not self.loaded_plate and normalise_plate(current) == normalise_plate(value):
                    edit.setToolTip("Από το PDF")
                    edit.setStyleSheet(PDF_FILLED_STYLE)
                    edit.textEdited.connect(lambda _text, e=edit: e.setStyleSheet(""))
                continue
            if not current:
                edit.setText(value)
                edit.setToolTip("Από το PDF")
                edit.setStyleSheet(PDF_FILLED_STYLE)
            elif not self._same_value(current, value, key):
                conflicts.append((labels[key], current, value))
                edit.setToolTip(f"PDF: {value}")
                edit.setStyleSheet(PDF_CONFLICT_STYLE)
            else:
                continue
            edit.textEdited.connect(lambda _text, e=edit: e.setStyleSheet(""))
        return conflicts

    def _show_conflicts(self):
        """Note at the top listing what the PDF says where it differs from the saved value."""
        if not self.pdf_conflicts:
            return
        lines = [
            f"<b>{escape(label)}</b>: αποθηκευμένο «{escape(current)}» - PDF «{escape(pdf)}»"
            for label, current, pdf in self.pdf_conflicts
        ]
        self.conflict_note.setText(
            "Διαφορές από το PDF (κρατήθηκαν οι αποθηκευμένες τιμές):<br>" + "<br>".join(lines)
        )
        self.conflict_note.show()

    def _fit_to_content(self):
        """Open large enough to show everything; scroll only if the screen is too small."""
        margins = self.layout().contentsMargins()
        hint = self.content.sizeHint()
        wanted = QSize(
            max(MIN_WIDTH, hint.width() + margins.left() + margins.right()),
            hint.height() + self.btn_pdf.sizeHint().height() + self.layout().spacing()
            + margins.top() + margins.bottom(),
        )
        screen = (self.screen() or QGuiApplication.primaryScreen()).availableGeometry()
        self.resize(wanted.boundedTo(QSize(screen.width(), screen.height() - 60)))
        frame = self.frameGeometry()
        self.move(
            max(screen.left(), min(frame.left(), screen.right() - frame.width())),
            max(screen.top(), min(frame.top(), screen.bottom() - frame.height())),
        )

    # ---- construction -------------------------------------------------

    def _summary(self):
        ctx = self.ctx
        text = (
            f"<b>{ctx['customer']['name']}</b> &nbsp;·&nbsp; {ctx['company']} &nbsp;·&nbsp; "
            f"{ctx['start']} - {ctx['end']} &nbsp;·&nbsp; Συνολικό ποσό: <b>{ctx['amount']} €</b>"
        )
        label = QLabel(text)
        label.setTextFormat(Qt.TextFormat.RichText)
        label.setWordWrap(True)
        return label

    @staticmethod
    def _two_column_grid(group, fields, edits, initial):
        """Two label/edit pairs per row; WIDE_FIELDS get a row of their own."""
        grid = QGridLayout(group)
        row = column = 0
        for key, label in fields:
            if key in WIDE_FIELDS and column:
                row, column = row + 1, 0
            edit = (DateLineEdit if key in DATE_KEYS else QLineEdit)(initial.get(key, ""))
            edit.setMaximumWidth(FIELD_WIDTH)
            edits[key] = edit
            grid.addWidget(QLabel(label), row, column * 2)
            grid.addWidget(edit, row, column * 2 + 1)
            column += 1
            if column == 2 or key in WIDE_FIELDS:
                row, column = row + 1, 0
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)
        return grid

    def _customer_group(self):
        group = QGroupBox("Στοιχεία λήπτη ασφάλισης - ασφαλιζομένου")
        fields = [
            (key, label) for key, label in CUSTOMER_FIELDS
            if self.is_vehicle or not (key.startswith("other_driver") or key == "license_date")
        ]
        self._two_column_grid(group, fields, self.customer_edits, self.customer)
        return group

    def _asset_group(self):
        if self.is_vehicle:
            group = QGroupBox("Στοιχεία οχήματος")
            grid = self._two_column_grid(group, VEHICLE_FIELDS, self.vehicle_edits, {})
            row = grid.rowCount()
            self.edit_insured_value = QLineEdit()
            self.edit_insured_value.setMaximumWidth(FIELD_WIDTH)
            grid.addWidget(QLabel("Ασφαλιζόμενη αξία"), row, 0)
            grid.addWidget(self.edit_insured_value, row, 1)
            return group

        group = QGroupBox("Στοιχεία ασφαλιζομένου")
        grid = QGridLayout(group)
        self.edit_description = QPlainTextEdit()
        self.edit_description.setFixedHeight(70)
        self.edit_description.setPlaceholderText("π.χ. διεύθυνση και περιγραφή κατοικίας, στοιχεία σκάφους")
        self.cmb_package = self._package_combo()
        self.edit_insured_value = QLineEdit()
        for edit in (self.cmb_package, self.edit_insured_value):
            edit.setMaximumWidth(FIELD_WIDTH)
        grid.addWidget(QLabel("Περιγραφή"), 0, 0)
        grid.addWidget(self.edit_description, 0, 1)
        grid.addWidget(QLabel(f"Πακέτο εταιρίας ({self.ctx['company']})"), 1, 0)
        grid.addWidget(self.cmb_package, 1, 1)
        grid.addWidget(QLabel("Ασφαλιζόμενη αξία"), 2, 0)
        grid.addWidget(self.edit_insured_value, 2, 1)
        grid.setColumnStretch(1, 1)
        return group

    def _covers_group(self):
        group = QGroupBox("Καλύψεις")
        layout = QVBoxLayout(group)

        package = QHBoxLayout()
        package.addWidget(QLabel(f"Πακέτο εταιρίας ({self.ctx['company']})"))
        self.cmb_package = self._package_combo()
        package.addWidget(self.cmb_package, 1)
        layout.addLayout(package)

        covers = QHBoxLayout()
        self.base_group = QButtonGroup(self)
        base_box = QVBoxLayout()
        self.base_buttons = {}
        for name in BASE_COVERS:
            radio = QRadioButton(name)
            self.base_group.addButton(radio)
            base_box.addWidget(radio)
            self.base_buttons[name] = radio
        optional_box = QVBoxLayout()
        self.optional_checks = {}
        for name in OPTIONAL_COVERS:
            check = QCheckBox(name)
            check.setStyle(self._checkbox_style)
            optional_box.addWidget(check)
            self.optional_checks[name] = check
        covers.addLayout(base_box, 1)
        covers.addLayout(optional_box, 1)
        layout.addLayout(covers)

        layout.addWidget(QLabel("Επιπλέον καλύψεις"))
        self.extras_layout = QVBoxLayout()
        layout.addLayout(self.extras_layout)
        btn_add = QPushButton("+ Προσθήκη κάλυψης")
        btn_add.clicked.connect(lambda: self.add_extra_row())
        layout.addWidget(btn_add, 0, Qt.AlignmentFlag.AlignLeft)
        return group

    # ---- behaviour ----------------------------------------------------

    def _package_combo(self):
        """Company packages to pick from; any other name can still be typed."""
        combo = QComboBox()
        combo.setEditable(True)
        combo.addItems([p["name"] for p in self.packages])
        combo.setCurrentIndex(-1)
        combo.lineEdit().setPlaceholderText("Επιλογή ή πληκτρολόγηση πακέτου...")
        combo.textActivated.connect(self._package_chosen)
        return combo

    def _package_chosen(self, name):
        """A package fills in its covers; they can still be changed for this application."""
        package = next(
            (p for p in self.packages if names.name_key(p["name"]) == names.name_key(name)), None
        )
        if package is None or not self.is_vehicle:
            return
        if package["base_cover"]:
            self.base_buttons[package["base_cover"]].setChecked(True)
        for cover, check in self.optional_checks.items():
            check.setChecked(cover in package["optional_covers"])

    def add_extra_row(self, company=""):
        row = ExtraRow(self, company)
        self.extra_rows.append(row)
        self.extras_layout.addWidget(row)

    def remove_extra_row(self, row):
        self.extra_rows.remove(row)
        self.extras_layout.removeWidget(row)
        row.deleteLater()

    def _restore_vehicle(self, plate):
        """Prefill the vehicle fields from what was saved for this plate."""
        self.loaded_plate = None  # plate of the saved vehicle the fields came from
        self.replaced_plate = None  # saved plate that this application corrects
        if not self.is_vehicle:
            return
        saved = next(
            (
                v for v in self.customer.get("vehicles", [])
                if normalise_plate(v.get("plate")) == normalise_plate(plate)
            ),
            None,
        )
        if saved:
            self.loaded_plate = normalise_plate(saved["plate"])
        saved = saved or {}
        for key, edit in self.vehicle_edits.items():
            edit.setText(saved.get(key, plate if key == "plate" else ""))
        self.edit_insured_value.setText(saved.get("insured_value", ""))

    def _problem(self):
        """First reason the form cannot be used, or None."""
        for key in DATE_KEYS:
            edit = self.customer_edits.get(key)
            text = edit.text().strip() if edit else ""
            if text and not QDate.fromString(text, "dd/MM/yyyy").isValid():
                return f"Μη έγκυρη ημερομηνία ({text}). Μορφή: ηη/μμ/εεεε", edit
        tin = self.customer_edits["tin"]
        if tin.text().strip() and not re.fullmatch(r"\d{9}", tin.text().strip()):
            return "Ο Α.Φ.Μ. πρέπει να έχει 9 ψηφία.", tin
        if self.is_vehicle:
            if not any(r.isChecked() for r in self.base_buttons.values()):
                return "Επιλέξτε μία από τις βασικές καλύψεις.", None
        return None

    def _finish(self, action):
        problem = self._problem()
        if problem:
            message, widget = problem
            show_message(message, msg_type="Warning")
            if widget is not None:
                widget.setFocus()
            return
        if not self._confirm_plate_change():
            return
        self.done(action)

    def _confirm_plate_change(self):
        """A loaded car whose plate was edited: correct that car or add a new one?"""
        if not self.loaded_plate:
            return True
        plate = normalise_plate(self.vehicle_edits["plate"].text())
        if plate == self.loaded_plate:
            return True
        answer = show_message(
            f"Ο αριθμός κυκλοφορίας άλλαξε από {self.loaded_plate} σε {plate}.\n\n"
            f"Ναι: διόρθωση - το όχημα {self.loaded_plate} αντικαθίσταται.\n"
            f"Όχι: νέο όχημα - το {self.loaded_plate} παραμένει αποθηκευμένο.",
            msg_type="Question",
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.replaced_plate = self.loaded_plate
        return answer != QMessageBox.StandardButton.Cancel

    # ---- result -------------------------------------------------------

    def customer_fields(self):
        """Extra customer data to store in record.json (empty values clear a key)."""
        return {key: edit.text().strip() for key, edit in self.customer_edits.items()}

    def vehicle_fields(self):
        """The vehicle as stored per customer."""
        vehicle = {key: edit.text().strip() for key, edit in self.vehicle_edits.items()}
        vehicle["plate"] = normalise_plate(vehicle["plate"])
        vehicle["insured_value"] = self.edit_insured_value.text().strip()
        return vehicle

    def application_data(self):
        """Everything application_pdf needs."""
        ctx = self.ctx
        data = {
            "type": ctx["type"],
            "company": ctx["company"],
            "start": ctx["start"],
            "end": ctx["end"],
            "amount": ctx["amount"],
            "date": ctx["date"],
            "customer": dict(self.customer_fields(), name=self.customer["name"]),
            "package": self.cmb_package.currentText().strip(),
        }
        if self.is_vehicle:
            data["asset"] = self.vehicle_fields()
            data["base_cover"] = next(
                (n for n, r in self.base_buttons.items() if r.isChecked()), None
            )
            data["optional_covers"] = [n for n, c in self.optional_checks.items() if c.isChecked()]
            data["extras"] = [row.values() for row in self.extra_rows]
        else:
            data["asset"] = {
                "description": self.edit_description.toPlainText().strip(),
                "insured_value": self.edit_insured_value.text().strip(),
            }
        return data
