"""Company cover packages: packages.json next to record.json (edited by hand for now)."""
import os

import covers
import datafile
import names
from application_pdf import BASE_COVERS, OPTIONAL_COVERS

FILE_NAME = covers.PACKAGES_FILE


def path(data_file):
    """packages.json sits in the covers folder next to the data file (record.json)."""
    return os.path.join(os.path.dirname(data_file), covers.FOLDER, FILE_NAME)


def load(path):
    """Return ([package], [problem]); a missing file just means no packages.

    A package is {"company", "type" ("" = any), "name", "base_cover" ("" = none),
    "optional_covers"}. Entries that are unusable are left out and reported.
    """
    try:
        data, _encoding = datafile.read_data(path)
    except FileNotFoundError:
        return [], []
    except (OSError, ValueError) as e:
        return [], [f"{FILE_NAME}: {e}"]
    if not isinstance(data, dict) or not isinstance(data.get("packages"), list):
        return [], [f'{FILE_NAME}: expected {{"packages": [...]}}']

    packages, problems = [], []
    for number, item in enumerate(data["packages"], 1):
        label = f"#{number} {item.get('name') or '?'}"
        if not item.get("company") or not item.get("name"):
            problems.append(f"{label}: company and name are required")
            continue
        base = item.get("base_cover") or ""
        optional = list(item.get("optional_covers") or [])
        unknown = ([base] if base and base not in BASE_COVERS else []) + [
            cover for cover in optional if cover not in OPTIONAL_COVERS
        ]
        if unknown:
            problems.append(f"{label}: unknown cover {', '.join(unknown)}")
            continue
        packages.append({
            "company": item["company"],
            "type": item.get("type") or "",
            "name": item["name"],
            "base_cover": base,
            "optional_covers": optional,
        })
    return packages, problems


def for_company(packages, company, insurance_type):
    """The packages of one company that apply to the insurance type, in file order."""
    key = names.name_key
    return [
        p for p in packages
        if key(p["company"]) == key(company)
        and (not p["type"] or key(p["type"]) == key(insurance_type))
    ]
