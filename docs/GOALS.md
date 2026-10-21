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
  - Main row: company + company package name + exactly one of ΑΠΛΗ ΑΣΤΙΚΗ ΕΥΘΥΝΗ / ΠΥΡΟΣ - ΚΛΟΠΗ / ΙΔΙΕΣ ΖΗΜΙΕΣ, plus any of ΘΡΑΥΣΗ ΚΡΥΣΤΑΛΛΩΝ / ΝΟΜΙΚΗ ΠΡΟΣΤΑΣΙΑ / ΟΔΙΚΗ ΒΟΗΘΕΙΑ.
  - Extra rows: one or more, each picked from the company's catalogue in `covers/` (from `docs/INTERFAST ΟΔΙΚΗ.txt`, `docs/ΕΛΠΑ EXTRA COVERS.txt`) or typed.
  - Only the total amount of the receipt window is shown, no per-cover premiums.
- Property, boat etc.: main part only, no extra covers.

## Out of scope
Database, bulk import of existing PDFs, multi-machine sharing.

## Done / open
- Field list taken from `docs/old_application_car.pdf`; office signature is `src/resource/domino_SIGNATURE.png`.
- Open: template autofill of customer / vehicle data from policy PDFs (not started; fields are typed or restored from the customer entry).
