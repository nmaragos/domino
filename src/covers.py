"""Extra-cover catalogues: covers/<company>.json, keyed by the record.json company name."""
import json
import os
import sys

COVERS_DIR = os.path.join(
    getattr(sys, "_MEIPASS", None)
    or os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "covers",
)


def load_catalogs(covers_dir=COVERS_DIR):
    """Return {company: [cover dict]}; a missing folder gives no catalogues."""
    catalogs = {}
    if not os.path.isdir(covers_dir):
        return catalogs
    for name in sorted(os.listdir(covers_dir)):
        if name.lower().endswith(".json"):
            with open(os.path.join(covers_dir, name), encoding="utf-8") as f:
                data = json.load(f)
            catalogs[data["company"]] = data["covers"]
    return catalogs
