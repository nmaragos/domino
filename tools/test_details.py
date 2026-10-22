"""Application-form details per sample. Run: uv run python tools\test_details.py <insurer> [--show]

Prints, per sample, which `details` fields were captured. With --show it also prints the
values (real customer data: for checking against the text only, never paste them anywhere).
"""
import glob
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import policy_extractor as pe  # noqa: E402
from dump import dump  # noqa: E402


def main(insurer, show):
    templates = pe.load_templates()
    pdfs = sorted(glob.glob(os.path.join(ROOT, "samples", insurer, "*.pdf")))
    if not pdfs:
        print(f"no samples for {insurer}")
        return 1
    totals = {}
    for pdf in pdfs:
        if not os.path.exists(pdf + ".txt"):
            dump(pdf)
        with open(pdf + ".txt", encoding="utf-8") as f:
            text = f.read()
        template = pe.detect(text, templates)
        if not template or "details" not in template:
            print(f"{os.path.basename(pdf)}: no template with details")
            continue
        found = pe.extract_details(text, template)
        asked = set(template["details"])
        for field in asked:
            totals.setdefault(field, [0, 0])
            totals[field][1] += 1
            # a number is filed under phone or mobile by its prefix, whatever label it had
            totals[field][0] += bool(
                field in found
                or (field in ("phone", "mobile") and {"phone", "mobile"} & found.keys())
            )
        missing = sorted(asked - found.keys())
        if {"phone", "mobile"} & found.keys():  # filed by prefix: one number is enough
            missing = [m for m in missing if m not in ("phone", "mobile")]
        print(f"{os.path.basename(pdf)} [{template['_file']}]: {len(found)} found"
              + (f", not found/invalid: {', '.join(missing)}" if missing else ""))
        if show:
            for field in pe.DETAIL_FIELDS:
                if field in found:
                    print(f"    {field}: {found[field]}")
    print(f"{insurer}: " + ", ".join(f"{k} {a}/{b}" for k, (a, b) in sorted(totals.items())))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], "--show" in sys.argv))
