# Domino Receipt

PyQt6 desktop app (Windows, Greek UI) that prints insurance receipts. Dropping policy PDFs onto the form autofills it from per-insurer regex templates.

## Run / test
- Always use uv from the repo root (`src/pyvenv.cfg` is stale, system Python has no PyQt6): `uv run .\src\receipt.py`, `uv run python tools\test.py <insurer>`.
- Headless UI checks: `QT_QPA_PLATFORM=offscreen`, build `Receipt()`, call `_autofill_from_pdfs(paths, "main"|"extra")`.

## PDF autofill
- Flow: `helpers.extract_text_from_pdf` (PyMuPDF, OCR fallback) -> `policy_extractor.detect/extract` -> `Receipt._autofill_from_text` / `_autofill_from_pdfs` in `src/receipt.py`.
- Two drop boxes: main (one policy; last PDF wins) and extra (RA / legal / extra covers; any number of PDFs). `Receipt.amounts` holds one amount per kind; the amount field shows their sum.
- Templates: `templates/<insurer>_<layout>.json`. Format and build procedure: `claude_code_instructions.txt` (read it before creating or editing templates).
- `company` / `insurance_type` must equal names in the `record.json` that the app loads (`DATA_FILE` in `receipt.py`; `src/record.json` is stale; both are cp1253-encoded). `tools/test.py` checks this.
- Passing `tools/test.py` only proves fields were captured, not that they are right. Print `policy_extractor.extract(...)` values and compare with the text: customer is a real SURNAME FIRST name (no labels, no patronymic), amount is the total premium payable, plate is Greek letters.
- Fix shared problems (dates, plates, names, amounts) in `policy_extractor.py`, not per template.

## Data and git
- `samples/` holds real customer PDFs: gitignored, never commit, never paste their contents into commits or docs.
- Never commit the local `DATA_FILE` path edit in `src/receipt.py` (unstage that hunk).
- Don't open a PR unless asked.

## Token rules
- Never open PDFs; run `tools/dump.py`, then grep the `.txt` for the label you need. Never print a full dump.
- Don't re-read files already read this session; don't restate code in replies.
- Template batches: reply one line per insurer, `<insurer>: N templates, unresolved: <fields or none>`; stop after 5 insurers and wait, unless told otherwise.
