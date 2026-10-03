# Template report

Checked with `tools/test.py <insurer>` (all fields extracted, company/type names present in `record.json`)
and by reading the extracted values against the PDF text.

| insurer | templates | unresolved fields |
|---|---|---|
| aig | 1 (car) | none (amount anchored on the line before `Οδηγός`; fragile) |
| allianz | 1 (car) | none |
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
| hd | 1 (motorcycle, company HELLAS DIRECT) | company: `HELLAS DIRECT` is not in `record.json` yet (add it; `test.py hd` reports it until then); `name_order: first_last` |
| interamerican | 2 (car, road assistance zone extra) | none |

Extractor behaviours that templates rely on (`src/policy_extractor.py`): dates accept dd/mm/yy and are
output as dd/mm/yyyy; plate Latin look-alike letters become Greek; spaces around `/` in policy numbers are
removed; several capture groups in a field are joined with a space; optional template key `name_order`
(`first_last`, `first_father_last`) rewrites person names to SURNAME FIRST (companies and initials untouched).

No samples yet: interasco, interfast, interlife, intersalonika, mediterrania, mineta, orizon, syndea, triglav, ydrogios.
