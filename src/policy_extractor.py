import json
import os
import re
from datetime import datetime

TEMPLATES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
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


def extract(text, template):
    """Apply template regexes to text. Invalid values become None."""
    out = {}
    for field, pattern in template.get("fields", {}).items():
        match = re.search(pattern, text, re.MULTILINE)
        out[field] = " ".join(g.strip() for g in match.groups() if g) if match and match.groups() else None

    order = _NAME_ORDERS.get(template.get("name_order"))
    if order and out.get("customer"):
        n_words, reorder = order
        words = out["customer"].split()
        is_person = len(words) == n_words and all(len(w) > 2 for w in words)             and not _LEGAL_FORMS.intersection(words)
        if is_person:  # companies/other shapes stay untouched
            out["customer"] = reorder(words)
    if out.get("plate"):
        out["plate"] = re.sub(r"[\s-]", "", out["plate"]).upper().translate(_LATIN_TO_GREEK)
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
