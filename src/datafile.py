"""Robust reading/writing of the shared record.json data file."""
import contextlib
import json
import os
import shutil
import tempfile
import time

LEGACY_ENCODING = "cp1253"


class LockTimeout(OSError):
    """The data file lock could not be acquired in time."""


def read_data(path):
    """Return (data, encoding). UTF-8 (with/without BOM) is tried first."""
    with open(path, "rb") as f:
        raw = f.read()
    for encoding in ("utf-8-sig", LEGACY_ENCODING):
        try:
            text = raw.decode(encoding)
        except UnicodeDecodeError:
            continue
        return json.loads(text), ("utf-8" if encoding == "utf-8-sig" else encoding)
    raise UnicodeDecodeError(LEGACY_ENCODING, raw, 0, 1, "undecodable data file")


def write_data(path, data, encoding=LEGACY_ENCODING, retries=5):
    """Atomically replace `path`; the original survives any failure."""
    # Encode first: an unencodable character must fail before touching disk.
    payload = json.dumps(data, ensure_ascii=False, indent=4).encode(encoding)

    directory = os.path.dirname(os.path.abspath(path))
    fd, tmp_path = tempfile.mkstemp(dir=directory, suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(payload)
            f.flush()
            os.fsync(f.fileno())
        if os.path.exists(path):
            with contextlib.suppress(OSError):
                shutil.copyfile(path, path + ".bak")
        for attempt in range(retries):
            try:
                os.replace(tmp_path, path)
                break
            except PermissionError:
                if attempt == retries - 1:
                    raise
                time.sleep(0.2 * (attempt + 1))
    finally:
        with contextlib.suppress(OSError):
            os.remove(tmp_path)


@contextlib.contextmanager
def locked(path, timeout=10.0, stale=60.0):
    """Advisory exclusive lock via a `<path>.lock` file."""
    lock_path = path + ".lock"
    deadline = time.monotonic() + timeout
    while True:
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            break
        except FileExistsError:
            try:
                if time.time() - os.path.getmtime(lock_path) > stale:
                    os.remove(lock_path)
                    continue
            except OSError:
                pass
            if time.monotonic() >= deadline:
                raise LockTimeout(f"Data file is locked: {lock_path}")
            time.sleep(0.1)
    try:
        yield
    finally:
        with contextlib.suppress(OSError):
            os.remove(lock_path)


def merge(disk, memory):
    """Merge in-memory changes into the freshly read on-disk data."""
    merged = dict(disk)
    merged["id"] = max(int(disk.get("id", 0)), int(memory.get("id", 0)))
    known = {c["name"] for c in disk.get("customer", [])}
    merged["customer"] = list(disk.get("customer", [])) + [
        c for c in memory.get("customer", []) if c["name"] not in known
    ]
    return merged


def save_merged(path, memory, encoding=LEGACY_ENCODING):
    """Under lock: re-read disk, merge `memory` into it, write, return result."""
    with locked(path):
        try:
            disk, _ = read_data(path)
        except FileNotFoundError:
            disk = memory
        merged = merge(disk, memory)
        write_data(path, merged, encoding)
    return merged


def update_customer(path, name, fields, memory, encoding=LEGACY_ENCODING):
    """Under lock: set `fields` on the customer `name`, return the merged data.

    Empty values remove the key. The customer is added if it is not known yet.
    """
    with locked(path):
        try:
            disk, _ = read_data(path)
        except FileNotFoundError:
            disk = memory
        merged = merge(disk, memory)
        customers = merged["customer"]
        entry = next((c for c in customers if c["name"] == name), None)
        if entry is None:
            entry = {"name": name}
            customers.append(entry)
        for key, value in fields.items():
            if value in (None, "", [], {}):
                entry.pop(key, None)
            else:
                entry[key] = value
        write_data(path, merged, encoding)
    return merged


def next_number(data):
    """The receipt number the next print will use: lowest free one, else id + 1."""
    free = data.get("free_ids")
    return min(free) if free else int(data["id"]) + 1


def reserve_id(path, memory, encoding=LEGACY_ENCODING):
    """Under lock: claim a receipt number on disk before printing.

    Released numbers in `free_ids` are reused first, so no number is skipped.
    `id` is the highest number ever issued and never decreases, so a stale
    in-memory copy merged with `max` cannot hand a number out twice.
    Returns (merged, number). The write raises if it cannot be saved, in
    which case nothing should be printed.
    """
    with locked(path):
        try:
            disk, _ = read_data(path)
        except FileNotFoundError:
            disk = memory
        merged = merge(disk, memory)
        free = sorted(merged.get("free_ids", []))
        if free:
            number = free.pop(0)
            merged["free_ids"] = free
        else:
            number = int(merged["id"]) + 1
            merged["id"] = number
        write_data(path, merged, encoding)
    return merged, number


def release_id(path, number, memory, encoding=LEGACY_ENCODING):
    """Under lock: return an unprinted receipt number to the pool for reuse."""
    with locked(path):
        try:
            disk, _ = read_data(path)
        except FileNotFoundError:
            disk = memory
        merged = merge(disk, memory)
        merged["free_ids"] = sorted(set(merged.get("free_ids", [])) | {number})
        write_data(path, merged, encoding)
    return merged
