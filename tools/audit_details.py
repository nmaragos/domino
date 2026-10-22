"""Sanity audit of the `details` templates: flags values that look like the insurer's or office's own
data, identical values across samples, or a captured label. Prints flags only (never customer values).
Run: uv run python tools\audit_details.py <insurer> [<insurer> ...]
"""
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
import names  # noqa: E402
import policy_extractor as pe  # noqa: E402

OFFICE = ("801070260", "ΚΑΖΑΖΗ", "26210026503", "2621026503", "DOMINOGROUP", "MARAGOS.ASFALEIES")
LABEL = re.compile(r"[:;]|^(EMAIL|E-MAIL|ΤΗΛ|ΑΦΜ|ΔΟΥ|ΔΙΕΥΘΥΝΣΗ|ΠΟΛΗ|ΚΙΝΗΤΟ)\b", re.I)


def audit(insurer, templates):
    flags, found, asked = [], {}, {}
    pdfs = sorted(glob.glob(os.path.join(ROOT, "samples", insurer, "*.pdf")))
    seen = {}
    for pdf in pdfs:
        with open(pdf + ".txt", encoding="utf-8") as f:
            text = f.read()
        template = pe.detect(text, templates)
        name = os.path.basename(pdf)
        if not template or template.get("zone", "main") != "main":
            continue
        if "details" not in template:
            flags.append(f"{name}: template {template['_file']} has no details")
            continue
        details = pe.extract_details(text, template)
        for key in template["details"]:
            asked[key] = asked.get(key, 0) + 1
            if key in details or (key in ("phone", "mobile") and {"phone", "mobile"} & details.keys()):
                found[key] = found.get(key, 0) + 1
        for key, value in details.items():
            upper = names.name_key(value).replace(" ", "")
            if any(o in upper or o in value.upper() for o in OFFICE):
                flags.append(f"{name}: {key} looks like the OFFICE's own data")
            if key in ("tax_office", "address", "city", "make", "model", "usage") and LABEL.search(value):
                flags.append(f"{name}: {key} looks like a label")
            seen.setdefault(key, set()).add(value)
    n = len(pdfs)
    if n > 1:
        for key in ("tin", "address", "email", "mobile", "phone", "zip", "city"):
            if key in found and found[key] == n and len(seen.get(key, ())) == 1:
                flags.append(f"{key}: identical in all {n} samples (insurer/boilerplate?)")
    summary = ", ".join(f"{k} {found.get(k, 0)}/{asked[k]}" for k in sorted(asked))
    return summary, flags


if __name__ == "__main__":
    templates = pe.load_templates()
    for insurer in sys.argv[1:]:
        summary, flags = audit(insurer, templates)
        print(f"{insurer}: {summary}")
        for flag in flags:
            print(f"   ! {flag}")
