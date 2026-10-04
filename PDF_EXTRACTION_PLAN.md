# PDF Extraction Capabilities Plan

## Current State
- `src/helpers.py` has `extract_text_from_pdf(pdf_path)` using PyMuPDF.
- OCR fallback exists via `page.get_textpage_ocr(language="ell+eng", dpi=300)`.
- Results are shown in `show_pdf_text_preview(...)`.
- No batch processing, no export, limited reporting.
- We will NOT modify existing behavior unless explicitly planned.

---

## Phase 1: Baseline Verification
Goal: confirm current extraction behavior across representative PDFs.

- [ ] List the kinds of PDFs we need to support (native text, scanned/image-only, mixed, protected).
- [ ] Write a one-off verification script that calls the existing helper and prints:
  - extracted text length
  - status message
  - error message
  - pages processed / OCR pages
- [ ] Run it on a sample set and record expected vs actual.
- [ ] Define what "working as expected" means for each class (text extracted, acceptable error for protected, etc.).

Deliverable: baseline report and acceptance criteria for each PDF class.

---

## Phase 2: Text Normalization
Goal: postprocess raw extracted text without changing the extraction call itself.

- [ ] Add an internal helper `normalize_extracted_text(raw_text)` that:
  - strips excessive blank lines
  - fixes common hyphenation/line-break artifacts
  - collapses repeated spaces
  - preserves intentional structure (paragraphs, sections)
- [ ] Apply normalization only after `extract_text_from_pdf` returns text.
- [ ] Add to the baseline verification and compare before/after.
- [ ] Make normalization opt-in/configurable so old behavior stays available.

Deliverable: normalization module and before/after comparison.

---

## Phase 3: Structured Export
Goal: let users save extracted text in useful formats.

- [ ] Add `extract_text_to_file(pdf_path, output_path, format)` supporting:
  - txt
  - md (Markdown, simple heuristic headings based on font size or page breaks)
  - json (pages array with text + optional metadata)
  - csv (one row per page)
- [ ] Report output path on success; leave preview behavior unchanged.
- [ ] Add to Phase 1/2 verification by re-running on representative PDFs and checking outputs.

Deliverable: export helpers plus sample outputs for each supported format.

---

## Phase 4: Status & Reporting
Goal: give clearer, machine-friendlier extraction results.

- [ ] Refactor `extract_text_from_pdf` into a small extraction report object / dataclass:
  - extracted_text
  - total_pages
  - text_pages
  - ocr_pages
  - error
  - warnings
- [ ] Keep the current tuple return for backward compatibility, or add a wrapper that returns the structured report.
- [ ] Update `show_pdf_text_preview` to display stats (pages, OCR usage, warnings).
- [ ] Verify UI preview still shows text correctly for all sample PDFs.

Deliverable: structured report plus updated preview dialog behavior.

---

## Phase 5: Batch Extraction
Goal: extract from multiple PDFs at once.

- [ ] Add `extract_text_from_pdfs(paths, ...)` that processes a list of PDFs.
- [ ] Aggregate results into a report per file.
- [ ] Save combined output to a chosen export format.
- [ ] UI: add a small non-invasive dialog (or reuse the preview) to show per-file status.
- [ ] Verify with 5-10 PDFs, mixed types.

Deliverable: batch extraction helper and summary report.

---

## Phase 6: Advanced Extraction (Optional)
Goal: table/form-field extraction if needed.

- [ ] Add `extract_tables_from_pdf(pdf_path)` using PyMuPDF's table API.
- [ ] Add `extract_form_fields(pdf_path)` if the app needs structured form data.
- [ ] This phase is contingent on whether Phase 1-5 reveal a real gap.

Deliverable: table/form extraction helpers, only if required.

---

## Execution Rule
For each phase:
1. Implement ONLY what the phase requires.
2. Run verification against representative PDFs.
3. Confirm outputs match acceptance criteria.
4. Stop and ask for direction before starting the next phase.

No changes to previous phases without explicit approval.
