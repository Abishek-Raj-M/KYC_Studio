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
| Name Match | 0.16 | Always (per document card) |
| DOB Match | 0.14 | Always |
| Age Eligibility | 0.10 | Always |
| Gender Consistency | 0.08 | When comparable gender/sex values exist |
| Mandatory Fields | 1.00 | Per document card (recomputed per doc) |
| Passport Expiry | 0.10 | Passport uploaded |
| Aadhaar Format | 0.08 | Aadhaar uploaded |
| Address Present | 0.06 | Aadhaar uploaded |
| PAN Format | 0.08 | PAN uploaded |
| Cross-Document Name Consistency | 0.12 | Combined scope, 2+ documents |

---

## Checks — shared (shown on relevant document cards)

### Name Match (weight 0.16)

Compares the name on each document to the name in ground truth.

- **Passport:** Given name and surname are compared to ground truth using fuzzy matching (85% similarity or higher).
- **Aadhaar / PAN:** Full name on the card is compared to the person name in ground truth the same way.

### DOB Match (weight 0.14)

At least one date of birth taken from an uploaded passport, Aadhaar, or PAN must match the date of birth in ground truth (dates are normalized before comparison).

### Age Eligibility (weight 0.10)

The person must be **18 years or older** based on ground truth date of birth (or Aadhaar date of birth if needed as a fallback).

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

The passport expiration date must be **after today** for travel validity.

A field row can still show as matching ground truth when both record the same expired date; this check enforces that the document is not expired for use.

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

## Checks — combined evaluation only

These appear in the **Combined checks** section when scope is **Combined**. They do not appear on individual document cards.

### Cross-Document Name Consistency (weight 0.12)

When **two or more** documents are evaluated together, the names extracted from each document must be consistent with each other (85% similarity or higher between consecutive name pairs).

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
