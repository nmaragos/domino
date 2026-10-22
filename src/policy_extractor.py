import json
import os
import re
import sys
from datetime import datetime

import names

TEMPLATES_DIR = os.path.join(
    getattr(sys, "_MEIPASS", None)
    or os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "templates",
)
_LATIN_TO_GREEK = str.maketrans("ABEZHIKMNOPTYX", "ΑΒΕΖΗΙΚΜΝΟΡΤΥΧ")
_LEGAL_FORMS = {"ΕΕ", "ΟΕ", "ΙΚΕ", "ΑΕ", "ΕΠΕ", "ΑΒΕΕ", "ΜΟΝ"}
# name_order -> (word count of a person, rewrite to "SURNAME FIRST")
_NAME_ORDERS = {
    "first_last": (2, lambda w: f"{w[1]} {w[0]}"),
    "first_father_last": (3, lambda w: f"{w[2]} {w[0]}"),
    "last_first_father": (3, lambda w: f"{w[0]} {w[1]}"),
}
FIELDS = ("policy", "plate", "start", "end", "amount", "customer")
# optional template key "details": extra data for the application form, same regex rules as "fields"
DETAIL_FIELDS = (
    "tin", "tax_office", "address", "zip", "city", "phone", "mobile", "email",
    "make", "model", "hp", "seats", "usage",
)


def load_templates(templates_dir=TEMPLATES_DIR):
    templates = []
    if not os.path.isdir(templates_dir):
        return templates
    for name in sorted(os.listdir(templates_dir)):
        if name.lower().endswith(".json"):
            with open(os.path.join(templates_dir, name), encoding="utf-8") as f:
                template = json.load(f)
            template["_file"] = name
            templates.append(template)
    return templates


def detect(text, templates):
    """Return the template whose detect strings all appear in text.

    The template with the most detect strings wins (most specific).
    """
    folded = text.casefold()
    matches = [
        t for t in templates
        if t.get("detect") and all(d.casefold() in folded for d in t["detect"])
    ]
    return max(matches, key=lambda t: len(t["detect"]), default=None)


def _parse_date(value):
    for fmt in ("%d/%m/%Y", "%d/%m/%y"):  # some insurers print 2-digit years
        try:
            return datetime.strptime(value.strip(), fmt)
        except (ValueError, AttributeError):
            pass
    return None


def _normalise_amount(value):
    """'1.234,56' -> '1.234,56' (app/Greek format); returns None if invalid."""
    value = value.strip().replace(" ", "")
    if re.fullmatch(r"\d{1,3}(\.\d{3})*,\d{2}", value):
        return value
    if re.fullmatch(r"\d+,\d{2}", value):
        return value
    if re.fullmatch(r"\d{1,3}(,\d{3})*\.\d{2}|\d+\.\d{2}", value):  # English format
        whole, dec = value.rsplit(".", 1)
        whole = whole.replace(",", "")
        grouped = f"{int(whole):,}".replace(",", ".")
        return f"{grouped},{dec}"
    return None


def greek_lookalikes(value):
    """Capitals with Latin letters that look Greek turned into Greek: 'E.I.X.' -> 'Ε.Ι.Χ.'."""
    return (value or "").upper().translate(_LATIN_TO_GREEK)


# usage printed by insurers -> the abbreviation the office uses (compared without periods and spaces)
_USAGE_ALIASES = {
    "ΙΔΙΩΤΙΚΗ": "ΕΙΧ",
    "ΙΔΙΩΤΙΚΗΧΡΗΣΗ": "ΕΙΧ",
    "ΙΔΙΩΤΙΚΗΣΧΡΗΣΗΣ": "ΕΙΧ",
}


# the office's own addresses: policies carry them when the customer has no email of their own
_OFFICE_EMAILS = ("maragos.asfaleies@", "@dominogroup.gr")

# what insurers print when a value is unknown: never fill these in
_PLACEHOLDERS = {"OTHER MODEL", "OTHER", "N/A", "ΑΛΛΟ", "ΑΛΛΟ ΜΟΝΤΕΛΟ", "ΑΓΝΩΣΤΟ", "ΧΩΡΙΣ"}


def canonical_usage(value):
    """Usage in a form where equal meanings compare equal: 'E.I.X.', 'ΕΙΧ', 'Ιδιωτική' -> 'ΕΙΧ'."""
    key = greek_lookalikes(names.name_key(value or "")).replace(".", "").replace(" ", "")
    return _USAGE_ALIASES.get(key, key)


def normalise_plate(value):
    """'ham 1234' -> 'ΗΑΜ1234': no spaces or dashes, capitals, Greek lookalike letters."""
    return greek_lookalikes(re.sub(r"[\s-]", "", value or ""))


def _match(pattern, text):
    """First match of `pattern`; several capture groups are joined with a space."""
    match = re.search(pattern, text, re.MULTILINE)
    if not match or not match.groups():
        return None
    return " ".join(g.strip() for g in match.groups() if g) or None


def extract(text, template):
    """Apply template regexes to text. Invalid values become None."""
    out = {}
    for field, pattern in template.get("fields", {}).items():
        out[field] = _match(pattern, text)

    order = _NAME_ORDERS.get(template.get("name_order"))
    if order and out.get("customer"):
        n_words, reorder = order
        words = out["customer"].split()
        is_person = len(words) == n_words and all(len(w) > 2 for w in words)             and not _LEGAL_FORMS.intersection(words)
        if is_person:  # companies/other shapes stay untouched
            out["customer"] = reorder(words)
    if out.get("plate"):
        out["plate"] = normalise_plate(out["plate"])
    if out.get("policy"):
        out["policy"] = re.sub(r"\s*/\s*", "/", out["policy"])
    if out.get("amount"):
        out["amount"] = _normalise_amount(out["amount"])

    start, end = _parse_date(out.get("start")), _parse_date(out.get("end"))
    # zero-pad (7/08/2026 -> 07/08/2026) so QDate "dd/MM/yyyy" accepts it
    if "start" in out:
        out["start"] = start.strftime("%d/%m/%Y") if start else None
    if "end" in out:
        out["end"] = end.strftime("%d/%m/%Y") if end else None
    if start and end and end <= start:
        out["end"] = None
    return out


def validate(values):
    """Return list of (field, value) problems; empty means all good."""
    return [(f, v) for f, v in values.items() if v is None]


def _digits(value):
    return re.sub(r"\D", "", value)


def _phone_kind(value):
    """('phone'|'mobile', 10 digits) for a Greek number, else None."""
    digits = _digits(value)
    if digits.startswith("0030"):
        digits = digits[4:]
    elif len(digits) == 12 and digits.startswith("30"):
        digits = digits[2:]
    if len(digits) != 10:
        return None
    if digits.startswith("69"):
        return "mobile", digits
    if digits.startswith("2"):
        return "phone", digits
    return None


def normalise_details(raw):
    """Clean raw detail strings; fields that don't look right are left out."""
    out = {}
    tin = _digits(raw.get("tin") or "")
    if len(tin) == 9:
        out["tin"] = tin
    zip_code = _digits(raw.get("zip") or "")
    if len(zip_code) == 5:
        out["zip"] = zip_code
    for key in ("phone", "mobile"):  # a number goes where it belongs, whatever label it had
        kind = _phone_kind(raw.get(key) or "")
        if kind:
            out.setdefault(*kind)
    email = (raw.get("email") or "").strip().lower()
    if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email) and not any(o in email for o in _OFFICE_EMAILS):
        out["email"] = email
    for key, low, high in (("hp", 1, 9999), ("seats", 1, 99)):
        number = re.sub(r"[.,\s]", "", raw.get(key) or "")
        if number.isdigit() and low <= int(number) <= high:
            out[key] = str(int(number))
    for key in ("address", "city", "tax_office", "make", "model", "usage"):
        text = names.name_key((raw.get(key) or "").strip(" ,.-"))
        if key == "usage":  # 'E.I.X.', 'Ιδιωτική' = 'ΕΙΧ'; others stay as printed, in Greek letters
            text = "ΕΙΧ" if canonical_usage(text) == "ΕΙΧ" else greek_lookalikes(text)
        if len(text) > 1 and text not in _PLACEHOLDERS:
            out[key] = text
    return out


def extract_details(text, template):
    """Application-form data of a policy: only the fields that were found and look valid."""
    raw = {
        field: _match(pattern, text)
        for field, pattern in template.get("details", {}).items()
    }
    return normalise_details({k: v for k, v in raw.items() if v})
