"""Case- and accent-insensitive matching of (Greek) names."""
import unicodedata


def name_key(text):
    """Comparison key: no accents/diaeresis, upper case, single spaces."""
    decomposed = unicodedata.normalize("NFD", text)
    stripped = "".join(c for c in decomposed if unicodedata.category(c) != "Mn")
    return " ".join(stripped.upper().split())


def build_index(names):
    """Map name_key -> [names] (more than one only for accent/case-only twins)."""
    index = {}
    for name in names:
        index.setdefault(name_key(name), []).append(name)
    return index


def find_name(index, text):
    """Canonical list entry for `text`, or None if absent or ambiguous."""
    candidates = index.get(name_key(text), [])
    if text in candidates:
        return text
    return candidates[0] if len(candidates) == 1 else None
