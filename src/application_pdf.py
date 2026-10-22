"""Insurance application (Αίτηση) layout and PDF output. No UI code here."""
from html import escape

from PyQt6.QtCore import QMarginsF, QRectF, QSizeF, QUrl
from PyQt6.QtGui import QFont, QImage, QPageLayout, QPageSize, QPainter, QPdfWriter, QTextDocument

from helpers import resource_path

OFFICE_NAME = "DOMINO GROUP I.K.E."
OFFICE_LINES = (
    "ΕΔΡΑ: ΤΑΣΗ ΚΑΖΑΖΗ 4, ΠΥΡΓΟΣ, 271 31 &nbsp; ΑΦΜ: 801070260 &nbsp; ΔΟΥ: ΠΥΡΓΟΥ",
    "ΤΗΛ: 26210 26503 &nbsp; www.dominogroup.gr &nbsp; e-mail: info@dominogroup.gr",
)
PLACE = "ΠΥΡΓΟΣ ΗΛΕΙΑΣ"
VEHICLE_TYPE = "ΑΥΤΟΚΙΝΗΤΟΥ"
TITLE_PT = 15  # size of the title ...
TITLE_FIT_CHARS = 34  # ... up to this many characters, smaller beyond
MIN_SCALE = 0.6  # smallest shrink to fit one page

# Exactly one of BASE_COVERS, any number of OPTIONAL_COVERS (vehicle applications only).
BASE_COVERS = ("ΑΣΤΙΚΗ ΕΥΘΥΝΗ", "ΠΥΡΟΣ - ΚΛΟΠΗ", "ΙΔΙΕΣ ΖΗΜΙΕΣ")
OPTIONAL_COVERS = ("ΘΡΑΥΣΗ ΚΡΥΣΤΑΛΛΩΝ", "ΝΟΜΙΚΗ ΠΡΟΣΤΑΣΙΑ", "ΟΔΙΚΗ ΒΟΗΘΕΙΑ")

# (key stored on the customer in record.json, label)
CUSTOMER_FIELDS = (
    ("father", "Πατρώνυμο"),
    ("profession", "Επάγγελμα"),
    ("birth", "Ημερ. γέννησης"),
    ("license_date", "Ημ. έκδοσης διπλ."),
    ("tin", "Α.Φ.Μ."),
    ("tax_office", "Δ.Ο.Υ."),
    ("address", "Διεύθυνση"),
    ("zip", "Τ.Κ."),
    ("city", "Πόλη"),
    ("phone", "Τηλέφωνο"),
    ("mobile", "Κινητό"),
    ("email", "e-mail"),
    ("other_driver", "Άλλος οδηγός"),
    ("other_driver_birth", "Ημ. γέν. άλλου οδηγού"),
    ("other_driver_license_date", "Ημ. διπλ. άλλου οδηγού"),
)
# fields that sit alone on a row
WIDE_FIELDS = ("other_driver",)
# stored per plate under customer["vehicles"]
VEHICLE_FIELDS = (
    ("plate", "Αριθμός κυκλοφορίας"),
    ("usage", "Χρήση"),
    ("make", "Εργ. κατασκευής"),
    ("model", "Μοντέλο"),
    ("hp", "Φορολογ. ίπποι"),
    ("seats", "Θέσεις"),
    ("color", "Χρώμα"),
)

_DARK = "#3a3a3a"
_LIGHT = "#ededed"
_MUTED = "#666666"
_LINE = "#9a9a9a"

_DECLARATION_INTRO = "Δηλώνω υπεύθυνα ότι:"
_DECLARATION_1 = (
    "1. Σαν κύριος ή κάτοχος {subject}, τα αναγραφόμενα στοιχεία είναι απολύτως "
    "αληθή και δεν παρέλειψα περιστατικό ή στοιχείο που θα μπορούσε να επηρεάσει "
    "τον υπό εκτίμηση κίνδυνο από την Ασφαλιστική Εταιρία. Επίσης ενημερώθηκα "
    "σχετικά με τους Γενικούς και ειδικούς όρους καθώς και για τις εξαιρέσεις του "
    "Ασφαλιστηρίου Συμβολαίου."
)
_DECLARATION_2_CIVIL = (
    " Εφ΄ όσον η Εταιρία αποδεχθεί τον κίνδυνο, η ισχύς της κάλυψης Αστικής Ευθύνης "
    "τρίτων (Ν 489/76, κωδικ. Π.Δ. 237/86 και τροπ. εν ισχύ Ν3557/2007) και η "
    "ημερομηνία έναρξής της θα αποδεικνύεται ΜΟΝΟ από το ΑΣΦΑΛΙΣΤΗΡΙΟ ΣΥΜΒΟΛΑΙΟ "
    "που εκδίδει η Εταιρία από τα κεντρικά γραφεία της. Σε ότι αφορά στις υπόλοιπες "
    "καλύψεις και τα κεφάλαιά τους, η ισχύς τους και η ημερομηνία έναρξης τους "
    "αποδεικνύονται ΜΟΝΟ από το ΑΣΦΑΛΙΣΤΗΡΙΟ ΣΥΜΒΟΛΑΙΟ ή την ΠΡΟΣΘΕΤΗ ΠΡΑΞΗ που έχει "
    "εκδώσει η Εταιρία."
)
_DECLARATION_2_OTHER = (
    " Εφ΄ όσον η Εταιρία αποδεχθεί τον κίνδυνο, η ισχύς των καλύψεων και τα κεφάλαιά "
    "τους, καθώς και η ημερομηνία έναρξής τους, αποδεικνύονται ΜΟΝΟ από το "
    "ΑΣΦΑΛΙΣΤΗΡΙΟ ΣΥΜΒΟΛΑΙΟ ή την ΠΡΟΣΘΕΤΗ ΠΡΑΞΗ που έχει εκδώσει η Εταιρία."
)
_DECLARATION_2 = (
    "2. Αποδέχομαι ότι η παρούσα ΑΙΤΗΣΗ δεν αποτελεί ασφαλιστική σύμβαση και δεν "
    "δεσμεύει την Εταιρία καθ΄ οποιονδήποτε τρόπο."
)


def is_vehicle(data):
    return data.get("type") == VEHICLE_TYPE


def _e(value):
    return escape(str(value or ""))


def _cell(label, value, span=1):
    """One label + underlined value pair as two table cells."""
    return (
        f'<td width="21%" style="color:{_MUTED};" valign="bottom">{_e(label)}</td>'
        f'<td colspan="{span}" style="border-bottom:1px solid {_LINE};font-weight:600;" '
        f'valign="bottom">{_e(value) or "&nbsp;"}</td>'
    )


def _grid(pairs):
    """Rows of two label/value pairs; a pair with a third item True spans the row."""
    rows, pending = [], []
    for pair in pairs:
        label, value, *wide = pair
        if wide and wide[0]:
            if pending:
                rows.append(pending)
                pending = []
            rows.append([(label, value, True)])
            continue
        pending.append((label, value, False))
        if len(pending) == 2:
            rows.append(pending)
            pending = []
    if pending:
        rows.append(pending)

    html = ['<table width="100%" cellspacing="0" cellpadding="2">']
    for row in rows:
        html.append("<tr>")
        for index, (label, value, wide) in enumerate(row):
            if wide:
                html.append(_cell(label, value, span=4))
            else:
                html.append(_cell(label, value))
                if index == 0 and len(row) == 2:
                    html.append('<td width="3%">&nbsp;</td>')
        if len(row) == 1 and not row[0][2]:
            html.append('<td colspan="3">&nbsp;</td>')
        html.append("</tr>")
    html.append("</table>")
    return "".join(html)


def _section(title, body):
    return (
        '<table width="100%" cellspacing="0" cellpadding="3"><tr>'
        f'<td bgcolor="{_DARK}" style="color:#ffffff;font-weight:700;">&nbsp;{_e(title)}</td>'
        "</tr></table>"
        f'<table width="100%" cellspacing="0" cellpadding="0"><tr><td height="3"></td></tr></table>'
        f"{body}"
        '<table width="100%" cellspacing="0" cellpadding="0"><tr><td height="6"></td></tr></table>'
    )


def _check(checked, text):
    box = "&#9745;" if checked else "&#9744;"
    weight = "700" if checked else "400"
    color = "#000000" if checked else _MUTED
    return (
        f'<span style="font-family:\'Segoe UI Symbol\';font-size:11pt;color:{color};">{box}</span> '
        f'<span style="font-weight:{weight};color:{color};">{_e(text)}</span>'
    )


def _customer_section(data):
    customer = data["customer"]
    pairs = [("Επωνυμία", customer.get("name"), True)]
    vehicle = is_vehicle(data)
    pairs += [
        (label, customer.get(key), key in WIDE_FIELDS) for key, label in CUSTOMER_FIELDS
        if vehicle or not (key.startswith("other_driver") or key == "license_date")
    ]
    return _section("ΣΤΟΙΧΕΙΑ ΛΗΠΤΗ ΑΣΦΑΛΙΣΗΣ - ΑΣΦΑΛΙΖΟΜΕΝΟΥ", _grid(pairs))


def _asset_section(data):
    asset = data["asset"]
    if is_vehicle(data):
        pairs = [(label, asset.get(key)) for key, label in VEHICLE_FIELDS]
        pairs.append(("Ασφαλιζόμενη αξία", asset.get("insured_value")))
        return _section("ΣΤΟΙΧΕΙΑ ΟΧΗΜΑΤΟΣ", _grid(pairs))
    pairs = [
        ("Ασφαλιζόμενο", asset.get("description"), True),
        ("Ασφαλιζόμενη αξία", asset.get("insured_value")),
    ]
    return _section("ΣΤΟΙΧΕΙΑ ΑΣΦΑΛΙΖΟΜΕΝΟΥ", _grid(pairs))


def _policy_section(data):
    pairs = [
        ("Ασφαλιστική εταιρία", data.get("company")),
        ("Πακέτο εταιρίας", data.get("package")),
        ("Διάρκεια από", data.get("start")),
        ("Έως", data.get("end")),
    ]
    return _section("ΑΣΦΑΛΙΣΗ", _grid(pairs))


def _covers_section(data):
    base = data.get("base_cover")
    optional = set(data.get("optional_covers", ()))
    html = ['<table width="100%" cellspacing="0" cellpadding="3"><tr>']
    html.append("<td width='50%' valign='top'>")
    html.append("<br>".join(_check(name == base, name) for name in BASE_COVERS))
    html.append("</td><td width='50%' valign='top'>")
    html.append("<br>".join(_check(name in optional, name) for name in OPTIONAL_COVERS))
    html.append("</td></tr></table>")

    extras = [x for x in data.get("extras", ()) if x.get("covers")]
    if extras:
        html.append(
            f'<table width="100%" cellspacing="0" cellpadding="3" style="margin-top:4px;">'
            f'<tr><td colspan="2" style="color:{_MUTED};">Επιπλέον καλύψεις</td></tr>'
        )
        for extra in extras:
            html.append(
                f'<tr><td width="30%" valign="top" style="border-bottom:1px solid {_LINE};font-weight:600;">'
                f'{_e(extra.get("company")) or "&nbsp;"}</td>'
                f'<td style="border-bottom:1px solid {_LINE};">'
                + "<br>".join(_e(cover) for cover in extra["covers"]) + "</td></tr>"
            )
        html.append("</table>")
    return _section("ΚΑΛΥΨΕΙΣ", "".join(html))


def _total_section(data):
    body = (
        '<table width="100%" cellspacing="0" cellpadding="4"><tr>'
        f'<td bgcolor="{_LIGHT}" style="font-size:11pt;font-weight:700;">&nbsp;Συνολικό ποσό</td>'
        f'<td bgcolor="{_LIGHT}" align="right" style="font-size:11pt;font-weight:700;">'
        f'{_e(data.get("amount"))} €&nbsp;</td></tr></table>'
    )
    return body + '<table width="100%" cellspacing="0" cellpadding="0"><tr><td height="9"></td></tr></table>'


def _declaration_section(data):
    vehicle = is_vehicle(data)
    subject = (
        "του αναφερόμενου στον ανωτέρω πίνακα οχήματος"
        if vehicle else "του αναφερόμενου στον ανωτέρω πίνακα ασφαλιζόμενου"
    )
    text_2 = _DECLARATION_2 + (_DECLARATION_2_CIVIL if vehicle else _DECLARATION_2_OTHER)
    body = (
        '<p style="font-size:7pt;margin:0;">'
        f"{_e(_DECLARATION_INTRO)}<br>{_e(_DECLARATION_1.format(subject=subject))}<br>"
        f"{_e(text_2)}</p>"
    )
    return _section("ΥΠΕΥΘΥΝΗ ΔΗΛΩΣΗ", body)


def build_html(data):
    title_text = "ΑΙΤΗΣΗ ΑΣΦΑΛΙΣΗΣ " + str(data.get("type") or "")
    # one line, always: no break opportunities, and a smaller size for the longest types
    title_pt = min(TITLE_PT, TITLE_PT * TITLE_FIT_CHARS / len(title_text))
    title = _e(title_text).replace(" ", "&nbsp;")
    header = (
        '<table width="100%" cellspacing="0" cellpadding="0"><tr>'
        '<td valign="middle">'
        '<table cellspacing="0" cellpadding="0"><tr>'
        '<td valign="middle"><img src="logo" width="68" height="68"></td>'
        '<td width="10"></td>'
        '<td valign="middle">'
        f'<span style="font-size:13pt;font-weight:700;color:{_DARK};">DOMINO GROUP</span><br>'
        f'<span style="font-size:8pt;font-weight:600;color:{_MUTED};">ΑΣΦΑΛΙΣΤΙΚΟΙ ΠΡΑΚΤΟΡΕΣ</span>'
        '</td></tr></table>'
        '</td>'
        '<td valign="middle" align="right" style="white-space:nowrap;">'
        f'<span style="font-size:{title_pt:.1f}pt;font-weight:700;color:{_DARK};white-space:nowrap;">{title}</span>'
        "</td></tr></table>"
        f'<p style="font-size:6.5pt;color:{_MUTED};margin-top:3px;margin-bottom:0;">'
        f"{OFFICE_LINES[0]}<br>{OFFICE_LINES[1]}</p>"
        '<table width="100%" cellspacing="0" cellpadding="0"><tr><td height="8"></td></tr></table>'
    )

    sections = [_customer_section(data), _asset_section(data), _policy_section(data)]
    if is_vehicle(data):
        sections.append(_covers_section(data))
    sections.append(_total_section(data))
    sections.append(_declaration_section(data))

    footer = (
        '<table width="100%" cellspacing="0" cellpadding="2"><tr>'
        '<td width="34%" valign="top">'
        f'Τόπος: <b>{PLACE}</b><br>Ημερομηνία: <b>{_e(data.get("date"))}</b></td>'
        '<td width="33%" align="center" valign="top">Ο ΔΙΑΜΕΣΟΛΑΒΩΝ<br>'
        '<img src="signature" width="105" height="72"></td>'
        '<td width="33%" align="center" valign="top">Ο ΛΗΠΤΗΣ / ΑΣΦΑΛΙΖΟΜΕΝΟΣ</td>'
        "</tr></table>"
    )

    return (
        '<html><body style="font-family:\'Segoe UI\';font-size:8pt;color:#111111;">'
        + header + "".join(sections) + footer + "</body></html>"
    )


def build_document(data):
    doc = QTextDocument()
    doc.setDefaultFont(QFont("Segoe UI", 8))
    doc.addResource(
        QTextDocument.ResourceType.ImageResource,
        QUrl("logo"), QImage(resource_path("resource", "domino_logo.png")),
    )
    doc.addResource(
        QTextDocument.ResourceType.ImageResource,
        QUrl("signature"), QImage(resource_path("resource", "domino_SIGNATURE.png")),
    )
    doc.setHtml(build_html(data))
    return doc


def print_document(doc, device):
    """Draw `doc` on one page of `device` (a QPdfWriter or QPrinter).

    QTextDocument lays out at 96 dpi, so the page size is given in 96-dpi pixels
    whatever the device resolution is. A document taller than the page (many
    extra covers) is shrunk to fit instead of spilling onto a second page.
    """
    page = device.pageLayout().paintRect(QPageLayout.Unit.Point)
    width, height = page.width() * 96 / 72, page.height() * 96 / 72
    scale = 1.0
    for _ in range(4):  # laying out wider makes the text shorter, so re-measure
        doc.setPageSize(QSizeF(width / scale, height / scale))
        needed = doc.size().height() * scale
        if needed <= height:
            break
        scale = max(scale * height / needed, MIN_SCALE)

    painter = QPainter(device)
    try:
        factor = device.logicalDpiX() / 96 * scale
        painter.scale(factor, factor)
        doc.drawContents(painter, QRectF(0, 0, width / scale, height / scale))
    finally:
        painter.end()


def write_pdf(data, pdf_path):
    writer = QPdfWriter(pdf_path)
    writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    writer.setPageMargins(QMarginsF(12, 10, 12, 10), QPageLayout.Unit.Millimeter)
    writer.setTitle("ΑΙΤΗΣΗ ΑΣΦΑΛΙΣΗΣ")
    print_document(build_document(data), writer)
