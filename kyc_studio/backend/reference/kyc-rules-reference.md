# KYC Studio — Built-in Rules Reference

Rule-based evaluation (`method: rules` or the rules half of `method: both`) uses the engine in `kyc_rules.py`. Rules are **built in**; no upload is required.

Weights below are defaults used in the overall rules score (except **Mandatory Fields**, which is recomputed per document card).

---

## Shared rules (every document card)

### Name Match (weight 0.16)
- **Passport:** Fuzzy match of extracted `given_names` / `surname` vs manifest `documents.passport.fields.given_name` / `surname` (≥ 85% similarity).
- **Aadhaar / PAN:** Fuzzy match of extracted `name` vs manifest / `person.name`.

### DOB Match (weight 0.14)
- At least one uploaded passport, Aadhaar, or PAN DOB must match ground-truth DOB after date normalization.

### Age Eligibility (weight 0.10)
- Customer must be **18+** from manifest DOB (or Aadhaar DOB fallback).

### Gender Consistency (weight 0.08)
- Shown when relevant sources exist. Compares passport `sex`, Aadhaar `gender`, PAN `gender`, and manifest (`M` = `MALE`).
- **Per card:** Passport uses `sex` row; Aadhaar uses `gender` row; PAN skipped if gender is not on the card.

### Mandatory Fields (weight 1.00, per card)
- Required manifest field rows for **this document only** must be `match` or `partial` (address coverage).
- Optional fields (e.g. passport expiry row, Aadhaar city/state, PAN signature) do not fail mandatory.

---

## Passport only

### Passport Expiry (weight 0.10)
- Extracted `date_of_expiration` must be **after today** (travel validity).
- **Note:** The field table can still show **match** vs manifest when both record an expired date; this rule enforces calendar validity.

---

## Aadhaar only

### Aadhaar Format (weight 0.08)
- `aadhaar_number` must be **12 digits** after stripping spaces/dashes.

### Address Present (weight 0.06)
- Extracted `address` must be non-empty.

---

## PAN only

### PAN Format (weight 0.08)
- `pan_number` must match pattern **AAAAA9999A**.

---

## Combined evaluation only (not on single-doc cards)

### Cross-Document Name Consistency (weight 0.12)
- When **2+ documents** are uploaded, names extracted from each doc must be mutually consistent (≥ 85% similarity).

---

## Field table (rules rows)

Per-document field rows compare **extracted vs manifest** (`documents.*.fields`), including:
- Address **coverage** (ground truth contained in extract → match; partial overlap → coverage %).
- ID normalization (spaces ignored for Aadhaar/PAN/passport numbers).

---

*Built-in rules — KYC Studio. Rubrics are separate (LLM / both mode) and documented in per-document rubric `.md` downloads.*
