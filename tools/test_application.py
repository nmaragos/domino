"""Self-checks for the application form (temp dir only). Run: uv run python tools\test_application.py"""
import json
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
import packages  # noqa: E402
import datafile  # noqa: E402

app = QApplication([])

CUSTOMER = {"name": "ΠΑΠΑΔΟΠΟΥΛΟΣ ΙΩΑΝΝΗΣ", "tin": "123456789", "address": "ΕΡΜΟΥ 10"}
CTX = {
    "type": "ΑΥΤΟΚΙΝΗΤΟΥ", "company": "ΕΘΝΙΚΗ", "start": "01/11/2026", "end": "01/05/2027",
    "amount": "345,60", "date": "21/10/2026", "customer": CUSTOMER, "plate": "ΗΑΜ1234",
    "extra_companies": ["ΕΛΠΑ", "ΕΡΜΗΣ", "EXTRA"], "extra_rows": ["ΕΛΠΑ"],
    "catalogs": covers.load_catalogs()[0],
}

# catalogues
catalogs, catalog_problems = covers.load_catalogs()
assert catalog_problems == []
assert {"ΕΛΠΑ", "INTERFAST_ASSISTANCE"} <= set(catalogs) and "ΕΡΜΗΣ" not in catalogs, set(catalogs)
assert any(c["name"].startswith("ERMIS") for c in catalogs["ΕΛΠΑ"]) and len(catalogs["ΕΛΠΑ"]) == 21
assert all(c["name"] and c["total"] >= c["net"] > 0 for items in catalogs.values() for c in items)

# a property application ignores the extra companies chosen in the receipt window
prop_dialog = application_dialog.ApplicationDialog(dict(CTX, type="ΠΕΡΙΟΥΣΙΑΣ"))
prop_dialog.cmb_package.setCurrentText("ΣΠΙΤΙ PLUS")
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

# policy PDF details: fill blanks only, keep saved values, report differences
pdf = {"tin": "123456789", "address": "ΕΡΜΟΥ 10", "city": "ΠΥΡΓΟΣ", "mobile": "6900000000",
       "make": "TOYOTA", "model": "YARIS", "hp": "13"}
saved = dict(CUSTOMER, address="Ερμού 10", city="ΑΘΗΝΑ", vehicles=[{"plate": "ΗΑΜ1234", "model": "COROLLA"}])
d = application_dialog.ApplicationDialog(dict(CTX, customer=saved, pdf_details=pdf))
assert d.customer_edits["tin"].text() == "123456789"  # same as saved: untouched
assert d.customer_edits["address"].text() == "Ερμού 10"  # same up to case/accents: no conflict
assert d.customer_edits["city"].text() == "ΑΘΗΝΑ"  # saved value kept
assert d.customer_edits["mobile"].text() == "6900000000" and d.customer_edits["mobile"].toolTip() == "Από το PDF"
assert d.vehicle_edits["make"].text() == "TOYOTA" and d.vehicle_edits["hp"].text() == "13"
assert d.vehicle_edits["model"].text() == "COROLLA"  # saved vehicle kept
assert sorted(c[0] for c in d.pdf_conflicts) == ["Μοντέλο", "Πόλη"], d.pdf_conflicts
assert not d.conflict_note.isHidden()
note = d.conflict_note.text()
assert "ΑΘΗΝΑ" in note and "ΠΥΡΓΟΣ" in note and "COROLLA" in note and "Πόλη" in note
assert application_dialog.ApplicationDialog(dict(CTX, pdf_details=pdf)).conflict_note.isHidden()  # no saved values: no conflicts
usage = application_dialog.ApplicationDialog(
    dict(CTX, customer=dict(CUSTOMER, vehicles=[{"plate": "ΗΑΜ1234", "usage": "ΕΙΧ"}]), pdf_details={"usage": "Ε.Ι.Χ."})
)
assert usage.pdf_conflicts == [] and usage.conflict_note.isHidden()  # periods do not count as a difference
latin = application_dialog.ApplicationDialog(
    dict(CTX, customer=dict(CUSTOMER, vehicles=[{"plate": "ΗΑΜ1234", "usage": "Ε.Ι.Χ."}]), pdf_details={"usage": "E.I.X."})
)  # the PDF prints Latin letters
assert latin.pdf_conflicts == []
assert policy_extractor.normalise_details({"usage": "E.I.X."}) == {"usage": "ΕΙΧ"}
assert policy_extractor.normalise_details({"usage": "Ιδιωτική"}) == {"usage": "ΕΙΧ"}
assert policy_extractor.normalise_details({"email": "maragos.asfaleies@gmail.com"}) == {}  # the office's own address
assert policy_extractor.normalise_details({"email": "info@dominogroup.gr"}) == {}
assert policy_extractor.normalise_details({"email": "Someone@Example.gr"}) == {"email": "someone@example.gr"}
assert policy_extractor.normalise_details({"make": "Toyota", "model": "Other Model"}) == {"make": "TOYOTA"}  # placeholders are not data
assert policy_extractor.normalise_details({"usage": "Ε.Ι.Χ.ΜΟΤ"}) == {"usage": "Ε.Ι.Χ.ΜΟΤ"}  # other usages stay
for saved_usage, pdf_usage in (("ΙΔΙΩΤΙΚΗ", "ΕΙΧ"), ("ΕΙΧ", "ΙΔΙΩΤΙΚΗ"), ("Ε.Ι.Χ.", "ΙΔΙΩΤΙΚΗ")):
    same = application_dialog.ApplicationDialog(
        dict(CTX, customer=dict(CUSTOMER, vehicles=[{"plate": "ΗΑΜ1234", "usage": saved_usage}]), pdf_details={"usage": pdf_usage})
    )
    assert same.pdf_conflicts == [], (saved_usage, pdf_usage)
# the plate is green when it came from the PDF for a car that is not saved yet
fresh = application_dialog.ApplicationDialog(dict(CTX, customer=dict(CUSTOMER), pdf_details={"plate": "ΗΑΜ1234"}))
assert fresh.vehicle_edits["plate"].styleSheet() == application_dialog.PDF_FILLED_STYLE and fresh.pdf_conflicts == []
known = application_dialog.ApplicationDialog(
    dict(CTX, customer=dict(CUSTOMER, vehicles=[{"plate": "ΗΑΜ1234"}]), pdf_details={"plate": "ΗΑΜ1234"})
)
assert known.vehicle_edits["plate"].styleSheet() == ""  # saved car: nothing new
typed = application_dialog.ApplicationDialog(dict(CTX, customer=dict(CUSTOMER), pdf_details={}))
assert typed.vehicle_edits["plate"].styleSheet() == ""  # typed by hand, not from a PDF
usage = application_dialog.ApplicationDialog(
    dict(CTX, customer=dict(CUSTOMER, vehicles=[{"plate": "ΗΑΜ1234", "usage": "ΕΙΧ"}]), pdf_details={"usage": "ΦΙΧ"})
)
assert [c[0] for c in usage.pdf_conflicts] == ["Χρήση"]
d.customer_edits["mobile"].textEdited.emit("x")
assert d.customer_edits["mobile"].styleSheet() == ""  # highlight goes once the user edits
prop_pdf = application_dialog.ApplicationDialog(dict(CTX, type="ΠΕΡΙΟΥΣΙΑΣ", pdf_details=pdf))
assert prop_pdf.customer_edits["tin"].text() == "123456789" and not prop_pdf.vehicle_edits  # no vehicle keys
assert policy_extractor.extract_details("", {"details": {"tin": r"ΑΦΜ (\d+)"}}) == {}
assert policy_extractor.extract_details("ΑΦΜ 12345", {"details": {"tin": r"ΑΦΜ (\d+)"}}) == {}  # not 9 digits
assert policy_extractor.normalise_details({"phone": "6912345678", "mobile": "2621012345"}) == {"mobile": "6912345678", "phone": "2621012345"}

# extra-cover catalogues: the covers folder next to record.json wins, the bundled one is the fallback
with tempfile.TemporaryDirectory() as d:
    record = os.path.join(d, "record.json")
    bundled, _ = covers.load_catalogs()
    assert covers.load(record) == (bundled, [])  # no folder next to the data file
    live = os.path.join(d, "covers")
    os.mkdir(live)
    with open(os.path.join(live, "elpa.json"), "w", encoding="utf-8") as f:
        json.dump({"company": "ΕΛΠΑ", "covers": [{"name": "Νέα κάλυψη"}, {"code": "X"}]}, f, ensure_ascii=False)
    with open(os.path.join(live, "broken.json"), "w", encoding="utf-8") as f:
        f.write("{oops")
    with open(os.path.join(live, "old.json"), "w", encoding="cp1253") as f:  # legacy encoding is read too
        json.dump({"company": "EXTRA", "covers": [{"name": "Κάλυψη Α"}]}, f, ensure_ascii=False)
    with open(os.path.join(live, "packages.json"), "w", encoding="utf-8") as f:  # same folder, not a catalogue
        json.dump({"packages": []}, f)
    live_catalogs, live_problems = covers.load(record)
    assert live_catalogs == {"ΕΛΠΑ": [{"name": "Νέα κάλυψη"}], "EXTRA": [{"name": "Κάλυψη Α"}]}, live_catalogs
    assert len(live_problems) == 2 and any("broken.json" in p for p in live_problems) and any("without a name" in p for p in live_problems)

# company packages: packages.json in the covers folder next to record.json
assert packages.path(os.path.join("srv", "software", "record.json")) == os.path.join("srv", "software", "covers", "packages.json")
with tempfile.TemporaryDirectory() as d:
    path = os.path.join(d, "packages.json")
    assert packages.load(path) == ([], [])  # no file, no packages
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"packages": [
            {"company": "ΔΥΝΑΜΙΣ", "type": "ΑΥΤΟΚΙΝΗΤΟΥ", "name": "Drive Basic", "base_cover": "ΑΣΤΙΚΗ ΕΥΘΥΝΗ", "optional_covers": []},
            {"company": "ΔΥΝΑΜΙΣ", "type": "ΑΥΤΟΚΙΝΗΤΟΥ", "name": "Drive Plus", "base_cover": "ΠΥΡΟΣ - ΚΛΟΠΗ", "optional_covers": ["ΘΡΑΥΣΗ ΚΡΥΣΤΑΛΛΩΝ"]},
            {"company": "HELLAS DIRECT", "name": "Blue Cars", "base_cover": "ΙΔΙΕΣ ΖΗΜΙΕΣ", "optional_covers": ["ΝΟΜΙΚΗ ΠΡΟΣΤΑΣΙΑ", "ΟΔΙΚΗ ΒΟΗΘΕΙΑ"]},
            {"company": "ΔΥΝΑΜΙΣ", "type": "ΑΥΤΟΚΙΝΗΤΟΥ", "name": "Drive Typo", "base_cover": "ΠΥΡΟΣ ΚΛΟΠΗ", "optional_covers": []},
            {"company": "ΔΥΝΑΜΙΣ", "type": "ΠΕΡΙΟΥΣΙΑΣ", "name": "Σπίτι Plus", "base_cover": "", "optional_covers": []},
            {"name": "No company"},
        ]}, f, ensure_ascii=False)
    loaded, problems = packages.load(path)
    assert [p["name"] for p in loaded] == ["Drive Basic", "Drive Plus", "Blue Cars", "Σπίτι Plus"], loaded
    assert len(problems) == 2 and "Drive Typo" in problems[0] and "required" in problems[1], problems
    car_packages = packages.for_company(loaded, "δυναμις", "ΑΥΤΟΚΙΝΗΤΟΥ")  # case and accents do not matter
    assert [p["name"] for p in car_packages] == ["Drive Basic", "Drive Plus"]
    assert [p["name"] for p in packages.for_company(loaded, "HELLAS DIRECT", "ΑΥΤΟΚΙΝΗΤΟΥ")] == ["Blue Cars"]  # no type: any
    assert [p["name"] for p in packages.for_company(loaded, "ΔΥΝΑΜΙΣ", "ΠΕΡΙΟΥΣΙΑΣ")] == ["Σπίτι Plus"]
    with open(path, "w", encoding="utf-8") as f:
        f.write("{not json")
    assert packages.load(path)[0] == [] and packages.load(path)[1]  # reported, not raised

pk = application_dialog.ApplicationDialog(dict(CTX, packages=car_packages))
assert [pk.cmb_package.itemText(i) for i in range(pk.cmb_package.count())] == ["Drive Basic", "Drive Plus"]
assert pk.cmb_package.currentText() == ""
pk.cmb_package.textActivated.emit("Drive Plus")
assert pk.base_buttons["ΠΥΡΟΣ - ΚΛΟΠΗ"].isChecked() and pk.optional_checks["ΘΡΑΥΣΗ ΚΡΥΣΤΑΛΛΩΝ"].isChecked()
pk.optional_checks["ΟΔΙΚΗ ΒΟΗΘΕΙΑ"].setChecked(True)  # adjusted by hand for this application
pk.cmb_package.textActivated.emit("Drive Basic")  # another package replaces the ticks
assert pk.base_buttons["ΑΣΤΙΚΗ ΕΥΘΥΝΗ"].isChecked() and not any(c.isChecked() for c in pk.optional_checks.values())
pk.cmb_package.setCurrentText("My own package")  # typed names are fine and change nothing
pk.cmb_package.textActivated.emit("My own package")
assert pk.application_data()["package"] == "My own package" and pk.base_buttons["ΑΣΤΙΚΗ ΕΥΘΥΝΗ"].isChecked()

# dialog -> data
dialog = application_dialog.ApplicationDialog(CTX)
dialog.base_buttons["ΠΥΡΟΣ - ΚΛΟΠΗ"].setChecked(True)
dialog.optional_checks["ΟΔΙΚΗ ΒΟΗΘΕΙΑ"].setChecked(True)
dialog.cmb_package.setCurrentText("ΚΛΑΣΙΚΟ")
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
elpa_order = [c["name"] for c in catalogs["ΕΛΠΑ"]]  # the list shows covers in catalogue order


def in_catalogue_order(*names):
    return sorted(names, key=elpa_order.index)


first_two = in_catalogue_order("Νομική Προστασία 3.000€", "ERMIS33 ΕΛΛΑΔΑ")
tick(dialog.extra_rows[0], "Νομική Προστασία 3.000€", "ERMIS33 ΕΛΛΑΔΑ")
assert dialog.extra_rows[0].covers() == first_two
assert len(dialog.extra_rows) == 1  # no line is added automatically
assert dialog.extra_rows[0].chips_layout.count() == 2  # one chip per ticked cover
dialog.extra_rows[0].chips_layout.itemAt(0).widget().click()  # chip removes its cover
assert dialog.extra_rows[0].covers() == first_two[1:]
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
    text = pdf[0].get_text().replace(chr(160), " ")  # the title uses non-breaking spaces
    for expected in ("ΑΙΤΗΣΗ ΑΣΦΑΛΙΣΗΣ ΑΥΤΟΚΙΝΗΤΟΥ", "ΠΑΠΑΔΟΠΟΥΛΟΣ", "123456789", "ΗΑΜ1234", "ΚΛΑΣΙΚΟ",
                     "Νομική Προστασία 3.000€", "ERMIS55", "ΠΑΚΕΤΟ 1", "345,60"):
        assert expected in text, expected
    pdf.close()

    # the title stays on one line for every insurance type (even the longest one)
    for insurance_type in ("ΑΥΤΟΚΙΝΗΤΟΥ", "ΠΕΡΙΟΥΣΙΑΣ", "ΣΚΑΦΩΝ", "ΑΣΤΙΚΗΣ ΕΥΘΥΝΗΣ", "ΟΔΙΚΗΣ ΒΟΗΘΕΙΑΣ",
                           "ΝΟΜΙΚΗΣ ΠΡΟΣΤΑΣΙΑΣ", "ΤΑΞΙΔΙΩΤΙΚΗΣ ΑΣΦΑΛΙΣΗΣ", "ΥΓΕΙΑΣ & ΠΡΟΣ. ΑΤΥΧΗΜΑΤΩΝ"):
        title_path = os.path.join(d, "title.pdf")
        application_pdf.write_pdf(dict(data, type=insurance_type, asset={}), title_path)
        with fitz.open(title_path) as title_pdf:
            title_lines = [line.replace(" ", " ").strip() for line in title_pdf[0].get_text().splitlines()]
            assert len(title_pdf) == 1
        assert "ΑΙΤΗΣΗ ΑΣΦΑΛΙΣΗΣ " + insurance_type in title_lines, insurance_type

    prop = dict(data, type="ΠΕΡΙΟΥΣΙΑΣ", asset={"description": "ΚΑΤΟΙΚΙΑ", "insured_value": "60.000"})
    application_pdf.write_pdf(prop, os.path.join(d, "prop.pdf"))
    pdf = fitz.open(os.path.join(d, "prop.pdf"))
    text = pdf[0].get_text().replace(chr(160), " ")  # the title uses non-breaking spaces
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
