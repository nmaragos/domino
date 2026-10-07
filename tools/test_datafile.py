"""Self-checks for src/datafile.py (temp dir only). Run: uv run python tools\test_datafile.py"""
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import datafile  # noqa: E402

DATA = {"id": 5, "customer": [{"name": "ΠΑΠΑΔΟΠΟΥΛΟΣ ΓΙΩΡΓΟΣ"}], "insurance_type": [{"name": "ΑΥΤΟΚΙΝΗΤΟ"}]}

with tempfile.TemporaryDirectory() as d:
    p = os.path.join(d, "record.json")

    # cp1253 round trip
    datafile.write_data(p, DATA, "cp1253")
    assert open(p, "rb").read().decode("cp1253").count("ΠΑΠΑΔΟΠΟΥΛΟΣ") == 1
    data, enc = datafile.read_data(p)
    assert data == DATA and enc == "cp1253", enc

    # utf-8 detected and preserved
    datafile.write_data(p, DATA, "utf-8")
    data, enc = datafile.read_data(p)
    assert data == DATA and enc == "utf-8", enc

    # unencodable char leaves original untouched, no tmp left
    datafile.write_data(p, DATA, "cp1253")
    before = open(p, "rb").read()
    bad = dict(DATA, customer=[{"name": "Zoë 😀"}])
    try:
        datafile.write_data(p, bad, "cp1253")
        raise SystemExit("expected UnicodeEncodeError")
    except UnicodeEncodeError:
        pass
    assert open(p, "rb").read() == before
    assert not [f for f in os.listdir(d) if f.endswith(".tmp")]

    # .bak created
    datafile.write_data(p, dict(DATA, id=6), "cp1253")
    assert os.path.exists(p + ".bak")

    # stale lock is broken, fresh lock times out, lock released
    lock = p + ".lock"
    open(lock, "w").close()
    os.utime(lock, (time.time() - 3600,) * 2)
    with datafile.locked(p):
        pass
    assert not os.path.exists(lock)
    open(lock, "w").close()
    try:
        with datafile.locked(p, timeout=0.3):
            raise SystemExit("expected LockTimeout")
    except datafile.LockTimeout:
        pass
    os.remove(lock)

    # two-writer merge keeps both customers and the higher id
    datafile.write_data(p, DATA, "cp1253")
    a = dict(DATA, id=6, customer=DATA["customer"] + [{"name": "A"}])
    b = dict(DATA, id=5, customer=DATA["customer"] + [{"name": "B"}])
    datafile.save_merged(p, a, "cp1253")
    merged = datafile.save_merged(p, b, "cp1253")
    names = {c["name"] for c in merged["customer"]}
    assert names == {"ΠΑΠΑΔΟΠΟΥΛΟΣ ΓΙΩΡΓΟΣ", "A", "B"} and merged["id"] == 6, merged
    assert datafile.read_data(p)[0] == merged

print("ok")
