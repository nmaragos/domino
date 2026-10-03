"""Run templates over samples/<insurer>/*.pdf (via cached .txt dumps). Prints only failures + a summary."""
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import policy_extractor as pe  # noqa: E402
from dump import dump  # noqa: E402


def check_names(template, record):
    """Return problems where company/insurance_type aren't in record.json."""
    lists = {
        "main": "insurance_company",
        "ra": "insurance_ra",
        "legal": "insurance_legal",
        "extra_covers": "insurance_extra_covers",
    }
    key = lists.get(template.get("extra_kind") if template.get("zone") == "extra" else "main")
    problems = []
    company = template.get("company")
    if not company or company not in [x["name"] for x in record.get(key, [])]:
        problems.append(f"company {company!r} not in {key}")
    if template.get("zone", "main") == "main":
        itype = template.get("insurance_type")
        if itype not in [x["name"] for x in record["insurance_type"]]:
            problems.append(f"insurance_type {itype!r} not in insurance_type")
    return problems


def main(insurer):
    templates = pe.load_templates()
    with open(os.path.join(ROOT, "src", "record.json"), encoding="cp1253") as f:
        record = json.load(f)
    name_problems = 0
    for t in templates:
        if t.get("insurer", "").casefold() == insurer.casefold():
            for problem in check_names(t, record):
                print(f"{t['_file']}: {problem}")
                name_problems += 1
    pdfs = sorted(glob.glob(os.path.join(ROOT, "samples", insurer, "*.pdf")))
    if not pdfs:
        print(f"no samples for {insurer}")
        return 1
    failures, checked = name_problems, 0
    for pdf in pdfs:
        if not os.path.exists(pdf + ".txt"):
            dump(pdf)
        if not os.path.exists(pdf + ".txt"):
            print(f"{os.path.basename(pdf)}: text extraction failed")
            failures += 1
            continue
        with open(pdf + ".txt", encoding="utf-8") as f:
            text = f.read()
        checked += 1
        template = pe.detect(text, templates)
        if not template:
            print(f"{os.path.basename(pdf)}: no template detected")
            failures += 1
            continue
        for field, value in pe.extract(text, template).items():
            if value is None:
                print(f"{os.path.basename(pdf)}: {field} = None ({template['_file']})")
                failures += 1
    print(f"{insurer}: {checked} files, {failures} failures")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
