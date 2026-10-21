"""Self-checks for the application form (temp dir only). Run: uv run python tools\test_application.py"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import fitz  # noqa: E402
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication  # noqa: E402

import application_dialog  # noqa: E402
import application_pdf  # noqa: E402
import covers  # noqa: E402
import datafile  # noqa: E402

app = QApplication([])

CUSTOMER = {"name": "ΠΑΠΑΔΟΠΟΥΛΟΣ ΙΩΑΝΝΗΣ", "tin": "123456789", "address": "ΕΡΜΟΥ 10"}
CTX = {
    "type": "ΑΥΤΟΚΙΝΗΤΟΥ", "company": "ΕΘΝΙΚΗ", "start": "01/11/2026", "end": "01/05/2027",
    "amount": "345,60", "date": "21/10/2026", "customer": CUSTOMER, "plate": "ΗΑΜ1234",
    "extra_companies": ["ΕΛΠΑ", "ΕΡΜΗΣ", "EXTRA"], "extra_rows": ["ΕΛΠΑ"],
    "catalogs": covers.load_catalogs(),
}

# catalogues
catalogs = covers.load_catalogs()
assert {"ΕΛΠΑ", "INTERFAST_ASSISTANCE"} <= set(catalogs) and "ΕΡΜΗΣ" not in catalogs, set(catalogs)
assert any(c["name"].startswith("ERMIS") for c in catalogs["ΕΛΠΑ"]) and len(catalogs["ΕΛΠΑ"]) == 21
assert all(c["name"] and c["total"] >= c["net"] > 0 for items in catalogs.values() for c in items)

# a property application ignores the extra companies chosen in the receipt window
prop_dialog = application_dialog.ApplicationDialog(dict(CTX, type="ΠΕΡΙΟΥΣΙΑΣ"))
prop_dialog.edit_package.setText("ΣΠΙΤΙ PLUS")
assert prop_dialog.application_data()["package"] == "ΣΠΙΤΙ PLUS"

# plates: matched ignoring case, spaces and Latin/Greek lookalikes; correcting one asks first
import policy_extractor  # noqa: E402
from PyQt6.QtWidgets import QMessageBox  # noqa: E402

assert policy_extractor.normalise_plate(" ham-1234 ") == "ΗΑΜ1234"
saved = dict(CUSTOMER, vehicles=[{"plate": "ΗΑΜ1234", "make": "TOYOTA"}, {"plate": "ΗΑΜ9999", "make": "FIAT"}])
car = application_dialog.ApplicationDialog(dict(CTX, customer=saved, plate="ham 1234"))
assert car.vehicle_edits["make"].text() == "TOYOTA" and car.loaded_plate == "ΗΑΜ1234"
assert car.vehicle_fields()["plate"] == "ΗΑΜ1234"  # stored normalised
car.base_buttons["ΠΥΡΟΣ - ΚΛΟΠΗ"].setChecked(True)
car.vehicle_edits["plate"].setText("ηαμ 1235")  # typo corrected
answers = iter([QMessageBox.StandardButton.Cancel, QMessageBox.StandardButton.No, QMessageBox.StandardButton.Yes])
application_dialog.show_message = lambda *a, **k: next(answers)
car._finish(car.PDF)
assert car.result() == 0 and car.replaced_plate is None  # cancelled: stays open
car._finish(car.PDF)
assert car.result() == car.PDF and car.replaced_plate is None  # "new vehicle"
car2 = application_dialog.ApplicationDialog(dict(CTX, customer=saved, plate="ΗΑΜ1234"))
car2.base_buttons["ΠΥΡΟΣ - ΚΛΟΠΗ"].setChecked(True)
car2.vehicle_edits["plate"].setText("ΗΑΜ1235")
car2._finish(car2.PDF)
assert car2.replaced_plate == "ΗΑΜ1234"  # "correction"
car3 = application_dialog.ApplicationDialog(dict(CTX, customer=dict(CUSTOMER), plate="ΗΑΜ1234"))
assert car3.loaded_plate is None  # unknown car: nothing to replace, no question
car3.base_buttons["ΠΥΡΟΣ - ΚΛΟΠΗ"].setChecked(True)
car3.vehicle_edits["plate"].setText("ΗΑΜ5555")
car3._finish(car3.PDF)  # would raise StopIteration if it asked
assert car3.result() == car3.PDF

# dialog -> data
dialog = application_dialog.ApplicationDialog(CTX)
dialog.base_buttons["ΠΥΡΟΣ - ΚΛΟΠΗ"].setChecked(True)
dialog.optional_checks["ΟΔΙΚΗ ΒΟΗΘΕΙΑ"].setChecked(True)
dialog.edit_package.setText("ΚΛΑΣΙΚΟ")
# date fields add the slashes while typing
from PyQt6.QtTest import QTest  # noqa: E402

birth = dialog.customer_edits["birth"]
birth.clear()
QTest.keyClicks(birth, "01021980")
assert birth.text() == "01/02/1980", birth.text()
QTest.keyClick(birth, Qt.Key.Key_Backspace)
QTest.keyClick(birth, Qt.Key.Key_Backspace)
assert birth.text() == "01/02/19", birth.text()
birth.clear()
QTest.keyClicks(birth, "0102")
QTest.keyClick(birth, Qt.Key.Key_Backspace)
assert birth.text() == "01/0", birth.text()
birth.clear()
QTest.keyClicks(birth, "01/02/1980")  # typing the slashes anyway is harmless
assert birth.text() == "01/02/1980", birth.text()


def tick(row, *names):
    """Tick covers in a row the way the popup does."""
    model = row.cmb_covers._model
    for i in range(model.rowCount()):
        if model.item(i).text() in names:
            model.item(i).setCheckState(Qt.CheckState.Checked)
    row.cmb_covers._refresh()
    row.cmb_covers.changed.emit()


assert len(dialog.extra_rows) == 1 and not dialog.extra_rows[0].covers()
tick(dialog.extra_rows[0], "Νομική Προστασία 3.000€", "ERMIS33 ΕΛΛΑΔΑ")
assert dialog.extra_rows[0].covers() == ["Νομική Προστασία 3.000€", "ERMIS33 ΕΛΛΑΔΑ"]
assert len(dialog.extra_rows) == 1  # no line is added automatically
assert dialog.extra_rows[0].chips_layout.count() == 2  # one chip per ticked cover
dialog.extra_rows[0].chips_layout.itemAt(0).widget().click()  # chip removes its cover
assert dialog.extra_rows[0].covers() == ["ERMIS33 ΕΛΛΑΔΑ"]
tick(dialog.extra_rows[0], "Νομική Προστασία 3.000€", "Θραύση καθρεπτών μόνο τζάμι έως 50€")
dialog.add_extra_row("ΕΛΠΑ")
tick(dialog.extra_rows[1], "ERMIS55 ΕΛΛΑΔΑ")
dialog.add_extra_row("EXTRA")  # no catalogue: typed text
dialog.extra_rows[2].edit_cover.setText("ΠΑΚΕΤΟ 1")
dialog.customer_edits["birth"].setText("31/02/2000")
assert dialog._problem() is not None  # invalid date
dialog.customer_edits["birth"].setText("01/02/1980")
dialog.customer_edits["tin"].setText("12345")
assert dialog._problem() is not None  # TIN must be 9 digits
dialog.customer_edits["tin"].setText("123456789")
assert dialog._problem() is None
data = dialog.application_data()
assert data["base_cover"] == "ΠΥΡΟΣ - ΚΛΟΠΗ" and data["optional_covers"] == ["ΟΔΙΚΗ ΒΟΗΘΕΙΑ"]
assert data["asset"]["plate"] == "ΗΑΜ1234" and len(data["extras"]) == 3
assert data["extras"][2] == {"company": "EXTRA", "covers": ["ΠΑΚΕΤΟ 1"]}

with tempfile.TemporaryDirectory() as d:
    # pdf: one page, shows the data
    path = os.path.join(d, "car.pdf")
    application_pdf.write_pdf(data, path)
    pdf = fitz.open(path)
    assert len(pdf) == 1, len(pdf)
    text = pdf[0].get_text()
    for expected in ("ΑΙΤΗΣΗ ΑΣΦΑΛΙΣΗΣ ΑΥΤΟΚΙΝΗΤΟΥ", "ΠΑΠΑΔΟΠΟΥΛΟΣ", "123456789", "ΗΑΜ1234", "ΚΛΑΣΙΚΟ",
                     "Νομική Προστασία 3.000€", "ERMIS33", "ERMIS55", "ΠΑΚΕΤΟ 1", "345,60"):
        assert expected in text, expected
    pdf.close()

    prop = dict(data, type="ΠΕΡΙΟΥΣΙΑΣ", asset={"description": "ΚΑΤΟΙΚΙΑ", "insured_value": "60.000"})
    application_pdf.write_pdf(prop, os.path.join(d, "prop.pdf"))
    pdf = fitz.open(os.path.join(d, "prop.pdf"))
    text = pdf[0].get_text()
    assert len(pdf) == 1 and "ΚΑΤΟΙΚΙΑ" in text and "ΚΛΑΣΙΚΟ" in text  # package of the car data
    assert "Άλλος οδηγός" not in text and "ΚΑΛΥΨΕΙΣ" not in text
    pdf.close()

    # customer details round trip (cp1253 like the real file)
    record = os.path.join(d, "record.json")
    memory = {"id": 5, "customer": [dict(CUSTOMER), {"name": "ΑΛΛΟΣ ΠΕΛΑΤΗΣ"}]}
    datafile.write_data(record, memory, "cp1253")
    merged = datafile.update_customer(
        record, CUSTOMER["name"],
        {"tin": "987654321", "address": "", "vehicles": [{"plate": "ΗΑΜ1234"}]}, memory, "cp1253",
    )
    saved, enc = datafile.read_data(record)
    assert enc == "cp1253" and saved == merged
    entry = saved["customer"][0]
    assert entry == {"name": CUSTOMER["name"], "tin": "987654321", "vehicles": [{"plate": "ΗΑΜ1234"}]}, entry
    assert saved["customer"][1] == {"name": "ΑΛΛΟΣ ΠΕΛΑΤΗΣ"}
    datafile.update_customer(record, "ΝΕΟΣ", {"tin": "111111111"}, merged, "cp1253")
    assert datafile.read_data(record)[0]["customer"][-1] == {"name": "ΝΕΟΣ", "tin": "111111111"}

print("ok")
