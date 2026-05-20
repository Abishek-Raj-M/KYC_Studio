# KYC Evaluation — Rules Reference

This document describes how rule-based KYC evaluation works in the studio: what you run, how scores are built, and what each check means.

---

## Evaluation flow

1. **Select documents** — Choose one or more of Passport, Aadhaar, and PAN. Upload front images (back optional where supported).
2. **Extract** — Each image is read and key fields are pulled from the document.
3. **Ground truth** — Upload a JSON manifest with the expected person and per-document values. Evaluation always compares extracted data against this ground truth.
4. **Choose scope**
   - **Per document** — One result card per uploaded document. Each card shows only the checks that apply to that document type, plus a field-level table (extracted vs ground truth).
   - **Combined** — One overall score for the whole submission, a list of combined checks (expand any check to see the fields it used), and the same per-document breakdown below.
5. **Run KYC** — All checks below run automatically. No rubric or extra configuration is required.

**Pass threshold:** Overall and per-document scores use a **75%** pass line unless noted otherwise.

---

## How the score is calculated

- Each check is **pass** or **fail** and contributes to the score by its **weight**.
- The overall score is the weighted average of passed checks: sum of weights for passed checks ÷ sum of all check weights, expressed as a percentage.
- **Mandatory Fields** uses weight 1.0 on each document card and is evaluated separately per document (see below). It is included in the combined check list when scope is Combined.
- Checks that do not apply to your upload set are omitted (for example, Passport Expiry only runs when a passport is included).

---

## Check weights (summary)

| Check | Weight | Applies when |
|-------|--------|----------------|
| Name Match | 0.28 | Combined scope only |
| DOB Match | 0.14 | Combined scope only |
| Gender Consistency | 0.08 | When comparable gender/sex values exist |
| Mandatory Fields | 1.00 | Per document card (recomputed per doc) |
| Passport Expiry | 0.10 | Passport uploaded |
| Aadhaar Format | 0.08 | Aadhaar uploaded |
| Address Present | 0.06 | Aadhaar uploaded |
| PAN Format | 0.08 | PAN uploaded |

---

## Checks — combined evaluation only

These appear in the **Combined checks** section when scope is **Combined**. They do not appear on individual document cards.

### Name Match (weight 0.28)

Evaluates **all** uploaded identity documents (passport, Aadhaar, PAN) together:

- **Name must be extracted** on every uploaded identity document. If any document is missing a name, this check **fails**.
- **Names must be consistent** with each other (85% fuzzy similarity or higher between each pair).
- If ground truth includes a person name, every extracted name must also match ground truth at the same threshold.

**Passport:** Uses given name + surname combined into one name string.

### DOB Match (weight 0.14)

Same all-documents requirement for date of birth:

- **DOB must be extracted** on every uploaded identity document. If any document is missing a DOB, this check **fails**.
- **DOBs must be consistent** with each other (normalized date comparison).
- If ground truth includes a DOB, every extracted DOB must match ground truth.

---

## Checks — shared (shown on relevant document cards)

### Gender Consistency (weight 0.08)

Runs only when there is something to compare (for example passport sex vs Aadhaar gender, or PAN vs ground truth). Male/female codes are treated as equivalent across common variants (M, MALE, F, FEMALE).

- **Passport card:** Uses sex on the passport vs ground truth.
- **Aadhaar card:** Uses gender on the card vs ground truth.
- **PAN card:** Gender is not required on the PAN front; the check is skipped when gender is not present on the card.

### Mandatory Fields (weight 1.00, per document)

For **each document card**, every required field for that document type must be present and match ground truth, or qualify as a partial address match (see field table). Optional fields (such as passport issue place, Aadhaar city/state, PAN signature) do not fail this check.

---

## Checks — passport only

### Passport Expiry (weight 0.10)

The passport **expiration date must be extracted** from the upload and must be **after today**. If expiry was not read from the image, this check **fails**.

A field row can still show as matching ground truth when both record the same expired date; this rule enforces calendar validity from **extracted** expiry only.

---

## Checks — Aadhaar only

### Aadhaar Format (weight 0.08)

The Aadhaar number must be **12 digits** after spaces and dashes are removed.

### Address Present (weight 0.06)

A non-empty address must be present on the extracted Aadhaar.

---

## Checks — PAN only

### PAN Format (weight 0.08)

The PAN must match the standard pattern: five letters, four digits, one letter (e.g. ABCDE1234F).

---

## Field-level table (per document)

Alongside checks, each document card includes a **field table**:

| Column | Meaning |
|--------|---------|
| Field | Which value was compared |
| Extracted | What was read from the image |
| Ground Truth | Expected value from your uploaded JSON |
| Status | match, partial, mismatch, or missing |

**Address** uses coverage logic: if the ground truth address is contained in the extracted text, status is match; partial overlap shows a coverage percentage; otherwise mismatch.

**ID numbers** (Aadhaar, PAN, passport) ignore spaces when comparing.

**Dates** are normalized to a common format before match/mismatch is decided.

In **Combined** scope, expanding a combined check shows the same kind of field rows that were used for that check, labeled by document type.

---

## What you need to run evaluation

- At least one uploaded and extracted document.
- Ground truth JSON with person details and per-document expected fields.
- Scope: **Per document** or **Combined**, depending on whether you want a portfolio-level score and cross-document checks.
