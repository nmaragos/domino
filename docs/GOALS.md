# Application form (Αίτηση) – goals and decisions

## Goal
Create an insurance application PDF from the receipt window. Generic form used by the office for all insurers.
Signed by the customer in signoSign, archived, optionally printed. Design is free (the old form is only a reference for the info needed: `docs/old_application_car.pdf`).

## Decisions
- Entry point: the existing disabled button in `receipt.ui` (`btn_print`, "Εκτύπωση Απόδ. Είσπραξης", never enabled in code) is now "Αίτηση".
- No premiums per cover on the form, only the total amount of the receipt window.
- Output: designed PDF generated directly (no Word). No customer signature field (signoSign adds it). The office signature is part of the document (image supplied by the user).
- File name: `ΑΙΤΗΣΗ_<plate or branch>_<yyyy.mm.dd>.pdf`, no "- signed" suffix. Same folder as receipts (`<archive_root>/<customer>/receipts`).
- Receipts are named the same way: `ΑΠΟΔΕΙΞΗ_...` prefix, no "- signed" suffix.
- Customer extra data (TIN, address, phone, dob, ...) is stored as optional keys on the customer entry in `record.json`, for the later database import.
- Covers (car/moto only):
  - Main row: company + company package name + exactly one of ΑΣΤΙΚΗ ΕΥΘΥΝΗ / ΠΥΡΟΣ - ΚΛΟΠΗ / ΙΔΙΕΣ ΖΗΜΙΕΣ, plus any of ΘΡΑΥΣΗ ΚΡΥΣΤΑΛΛΩΝ / ΝΟΜΙΚΗ ΠΡΟΣΤΑΣΙΑ / ΟΔΙΚΗ ΒΟΗΘΕΙΑ.
  - Extra rows: one or more, each picked from the company's catalogue in `covers/` (from `docs/INTERFAST ΟΔΙΚΗ.txt`, `docs/ΕΛΠΑ EXTRA COVERS.txt`) or typed.
  - Only the total amount of the receipt window is shown, no per-cover premiums.
- Property, boat etc.: main part only, no extra covers.

## Out of scope
Database, bulk import of existing PDFs, multi-machine sharing.

## Done / open
- Field list taken from `docs/old_application_car.pdf`; office signature is `src/resource/domino_SIGNATURE.png`.

## Autofill of the application from the policy PDF (decided 2026-10-22)
- Fields: core set only - tin, tax_office, address, zip, city, phone, mobile, email + vehicle make, model, hp, seats, usage. Not extracted: birth date, licence date, profession, colour, other driver, package.
- Templates get an optional `details` key (flat regex map); `fields` is untouched so receipts are not affected.
- Saved or typed values win: the PDF only fills blank fields (highlighted, tooltip "Από το PDF"). If the PDF differs from a saved value, a message lists the differences and nothing is overwritten.
- PDF details are used only for the customer that was in the receipt window when the PDF was dropped.
- Rollout: pilot with hd, atlantiki, dynamis (checked by hand against the text), then batches of 5 insurers, waiting for the user after each batch.
- Status: done for all 32 main-zone templates of 22 insurers (pilot hd, atlantiki, dynamis, then 19 more by Haiku subagents on 2026-10-28, audited). arag, elpa, extra, interfast, mediterrania only have extras templates (no application data). Check a new insurer with `tools/test_details.py` and `tools/audit_details.py`.

## Company cover packages (decided 2026-10-26)
- The "Πακέτο εταιρίας" field is an editable dropdown of the packages of the selected company and insurance type (property and others: names only). Other names can still be typed.
- Storage: `packages.json` in the `covers` folder next to `record.json` (moved there on 2026-10-27; shared by all PCs, read every time the form opens). Format: `docs/packages.example.json`. Each package lists its covers explicitly: one `base_cover` and the `optional_covers`; standard covers only, no extra-cover rows.
- Picking a package ticks its covers; they can still be changed for that application.
- No editor for now: the file is edited by hand. **Revisit later: a separate package manager (add / edit / delete packages), as its own feature.**
- Extra-cover catalogues (ΕΛΠΑ, INTERFAST...) follow the same rule: the live copy is a `covers` folder next to `record.json`, read every time the form opens, so updating a cover needs no rebuild. The bundled `covers/` folder is the fallback and the template to copy. Usage is unchanged (multi-select rows, not packages).
