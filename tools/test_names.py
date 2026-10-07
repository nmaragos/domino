"""Self-checks for src/names.py. Run: uv run python tools\test_names.py"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import names  # noqa: E402

k = names.name_key
assert k("Γιώργος  Παπαδόπουλος") == k("ΓΙΩΡΓΟΣ ΠΑΠΑΔΟΠΟΥΛΟΣ") == "ΓΙΩΡΓΟΣ ΠΑΠΑΔΟΠΟΥΛΟΣ"
assert k("άέήίόύώϊΐ") == "ΑΕΗΙΟΥΩΙΙ"
assert k("Ιωάννης Σ.") == k("ΙΩΑΝΝΗΣ Σ.")

idx = names.build_index(["ΠΑΠΑΔΟΠΟΥΛΟΣ ΓΙΩΡΓΟΣ", "ΧΧ", "Αβγ"])
assert names.find_name(idx, "παπαδόπουλος γιώργος") == "ΠΑΠΑΔΟΠΟΥΛΟΣ ΓΙΩΡΓΟΣ"
assert names.find_name(idx, "άβγ") == "Αβγ"
assert names.find_name(idx, "nobody") is None

# accent/case-only twins are ambiguous unless typed exactly
twins = names.build_index(["ΑΒΓ", "Άβγ"])
assert names.find_name(twins, "αβγ") is None
assert names.find_name(twins, "ΑΒΓ") == "ΑΒΓ"
print("ok")
