"""Dump the app's own extracted text for a PDF (or every PDF under a folder) to <pdf>.txt."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
from helpers import extract_text_from_pdf  # noqa: E402


def dump(pdf_path):
    text, _status, error = extract_text_from_pdf(pdf_path)
    if error:
        print(f"{pdf_path}: {error}")
        return
    with open(pdf_path + ".txt", "w", encoding="utf-8") as f:
        f.write(text)


if __name__ == "__main__":
    for target in sys.argv[1:]:
        if os.path.isdir(target):
            for root, _dirs, files in os.walk(target):
                for name in files:
                    if name.lower().endswith(".pdf"):
                        dump(os.path.join(root, name))
        else:
            dump(target)
