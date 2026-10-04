# Template report

Checked with `tools/test.py <insurer>` (all fields extracted, company/type names present in the `record.json` the app loads, i.e. `DATA_FILE` in `receipt.py`; the repo copy `src/record.json` is stale)
and by reading the extracted values against the PDF text.

| insurer | templates | unresolved fields |
|---|---|---|
| aig | 1 (car) | none (amount anchored on the line before `Οδηγός`; fragile) |
| allianz | 1 (car) | none (`name_order: last_first_father`) |
| arag | 1 (legal, zone extra) | none (amount deliberately omitted) |
| atlantiki | 2 (car, boat) | none (boat has no plate) |
| caravela | 1 (auto) | none |
| dynamis | 3 (car, boat, property) | none (boat/property have no plate) |
| elpa | 1 (extra_covers, zone extra) | none |
| ergo | 1 (auto) | none (patronymic stripped from customer) |
| ethniki | 1 (car) | none (customer = surname + first name, 2 capture groups) |
| euroins | 1 (car) | none (dates printed with 2-digit years) |
| eurolife | 1 (property) | none |
| europa | 2 (car, property) | none |
| extra | 1 (road assistance, zone extra, ra) | none |
| generali | 1 (car) | none (`name_order: first_father_last`) |
| gmi | 1 (car) | none (amount = 6th value under `Δίπλωμα <2 ετών`; equals net total + taxes in both samples) |
| groupama | 1 (property) | none |
| hd | 1 (motorcycle, company HELLAS DIRECT) | none (`name_order: first_last`) |
| interamerican | 2 (car, road assistance zone extra) | none |
| interasco | 2 (car, health) | none (contract number only; health customer = policyholder `ΛΗΠΤΗΣ`, which is DOMINO GROUP IKE in sample 1; health dates are printed value-before-label) |
| interfast | 1 (road assistance, zone extra, ra) | none |
| interlife | 1 (car) | none (amount anchored on the line after the price column; fragile) |
| intersalonika | 1 (car) | none |
| mediterrania | 1 (legal, zone extra) | none (amount = first value after `Ολικά Ασφάλιστρα`; values print in reverse label order) |
| mineta | 1 (car) | none (amount = 5 lines after `ΣΥΝΟΛΟ`; breaks if the premium columns change) |
| syndea | 1 (car) | none (only one sample; amount = 6th figure after `ΣΥΝΟΛΟ`) |
| triglav | 1 (car) | none |
| ydrogios | 3 (car, boat, property) | none (boat/property customers are companies, printed as-is; dates in boat/property are printed value-before-label) |

Extractor behaviours that templates rely on (`src/policy_extractor.py`): dates accept dd/mm/yy and are
output as dd/mm/yyyy; plate Latin look-alike letters become Greek; spaces around `/` in policy numbers are
removed; several capture groups in a field are joined with a space; optional template key `name_order`
(`first_last`, `first_father_last`, `last_first_father`) rewrites person names to SURNAME FIRST (companies and initials untouched).

No samples yet: orizon.
