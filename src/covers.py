"""Extra-cover catalogues: covers/<company>.json, keyed by the record.json company name.

The live copy is the `covers` folder next to record.json (edited by hand, read every
time the form opens); the copy bundled with the app is only the fallback.
"""
import os
import sys

import datafile

FOLDER = "covers"
PACKAGES_FILE = "packages.json"  # lives in the same folder but is not a catalogue
COVERS_DIR = os.path.join(
    getattr(sys, "_MEIPASS", None)
    or os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    FOLDER,
)


def load_catalogs(covers_dir=COVERS_DIR):
    """Return ({company: [cover dict]}, [problem]).

    A cover needs a name; code, net and total are optional. A file or a cover that
    cannot be used is left out and reported, the rest still loads.
    """
    catalogs, problems = {}, []
    if not os.path.isdir(covers_dir):
        return catalogs, problems
    for file_name in sorted(os.listdir(covers_dir)):
        if not file_name.lower().endswith(".json") or file_name.lower() == PACKAGES_FILE:
            continue
        try:
            data, _encoding = datafile.read_data(os.path.join(covers_dir, file_name))
            company, items = data["company"], data["covers"]
        except (OSError, ValueError, KeyError, TypeError) as e:
            problems.append(f"{FOLDER}/{file_name}: {e!r}")
            continue
        covers = [c for c in items if isinstance(c, dict) and c.get("name")]
        if len(covers) != len(items):
            problems.append(f"{FOLDER}/{file_name}: {len(items) - len(covers)} cover(s) without a name")
        catalogs[company] = covers
    return catalogs, problems


def load(data_file):
    """The catalogues next to `data_file` (record.json), else the bundled ones."""
    live = os.path.join(os.path.dirname(data_file), FOLDER)
    return load_catalogs(live if os.path.isdir(live) else COVERS_DIR)
