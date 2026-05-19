# KYC Extraction & Evaluation Alignment — Implementation Plan

> **Status:** APPROVED for implementation — handoff in `docs/context/AGENT-INSTRUCTIONS.md` + compressed context in `docs/context/kyc-extraction-evaluation-alignment-context.md`.

**Goal:** Align OCR extraction, UI display, ground-truth manifest fields, and rules/rubric field tables so per-document results are complete, visible, and internally consistent (no false PASS vs table mismatch).

**Architecture:** Four layers fixed in order — (0) use upload slot / declared doc type for vision schema, (1) vision schema asks for manifest fields, (2) UI shows full extraction payload, (3) rules/LLM field tables compare extracted values to **per-document manifest fields** (not wrong GT targets). Shared plumbing (manifest → rules engine, tests) once per doc type deltas are known.

**Tech Stack:** FastAPI (`kyc_studio/backend`), React/Vite (`kyc_studio/frontend`), GPT-4o Vision + Tesseract (`image_processing/`), pytest (`studio_tests/api/`).

---

## Process (how we will use this plan)

1. **Passport** — reviewed (below).
2. **Aadhaar** — reviewed (below).
3. **PAN** — reviewed (below).
4. **Consolidate** — merge overlapping fixes (X-0, X-1, schemas, rules, LLM, tests).
5. **Build** — implement only after user approves consolidated plan.

---

## Cross-cutting issues (all document types)

| ID | Issue | Affects | Proposed fix (high level) |
|----|--------|---------|---------------------------|
| **X-0** | **`/api/extract` ignores UI `doc_types`**; pipeline uses Tesseract `DocumentTypeDetector` only → wrong schema (e.g. Aadhaar image extracted as PAN) | **Aadhaar** (confirmed); risk for all | Pass declared `doc_types[idx]` into `OCRExtractionPipeline.process_single_image` / `extract_hybrid`; use it for vision prompt schema. Improve detector: avoid PAN winning on generic `"government of india"` alone; boost `aadhaar` / `uidai` keywords. |
| X-1 | UI shows max **8** extracted fields (`.slice(0, 8)`) | Passport, Aadhaar, PAN | Remove cap or show all keys in `DocumentUploadCard.tsx` |
| X-2 | Vision schema ≠ manifest `documents.*.fields` | Per doc type | Extend `document_schemas_ext.py` schemas per doc |
| X-3 | Rules `_field_matches` uses flat `GroundTruth` only; wrong or empty GT on some rows | Passport, Aadhaar, PAN | Pass `ground_truth_manifest` into `RuleBasedKYCEngine.evaluate`; compare per `documents.<type>.fields` |
| X-4 | Results field table shows subset of manifest fields | Per doc type | Expand `_field_matches` in `kyc_rules.py` + `_field_matches_for_doc` in `kyc_llm_agent.py` |
| X-5 | Top checks (Name Match, rubric IDs) ≠ table row logic | All | Document per check; align or scope checks to cards |
| X-6 | `rules:` + `rubric:` duplicate rows in Both mode | All | Keep for now; ensure both use same manifest field sources |
| X-7 | Field aliases | All | `canonical_mapper.py`: `given_name`→`given_names`, `aadhaar`→`aadhaar_number`, `pan`→`pan_number`, `date_of_expiry`→`date_of_expiration`; verify after schema changes |

### X-0 implementation notes (priority for Aadhaar)

- **Today:** `main.py` `extract_documents` accepts `doc_types` but only stores them on the response wrapper; `pipeline.process_single_image` uses detector output only (`ocr_extraction_pipeline.py` → `document_type_detector.py`).
- **Evaluate path:** `normalize_document(extracted, item.doc_type)` forces **slot type** (e.g. `aadhaar`) even when `extracted.document_type` is `pan` — KYC runs wrong field shape.
- **Files:** `main.py`, `ocr_extraction_pipeline.py`, optionally `document_type_detector.py`.

---

## Vision schemas today (`document_schemas_ext.py`)

### Aadhaar (prompted fields)

`aadhaar_number`, `name`, `dob`, `gender`, `address`, `pincode` — **not** `city`, `state`, `issue_date`.

### PAN (prompted fields)

`pan_number`, `name`, `father_name`, `dob` — **not** `gender`, `signature_name`, `issue_date`.

### Passport (prompted fields)

See Document 1 — missing `father_name`, `mother_name`, `place_of_issue`, `signature_name` vs manifest.

---

## Document 1: Passport — REVIEWED

### Manifest expectation

`documents.passport.fields`: `surname`, `given_name`, `nationality`, `sex`, `date_of_birth`, `place_of_birth`, `father_name`, `mother_name`, `passport_number`, `date_of_issue`, `date_of_expiry`, `place_of_issue`, `signature_name`.

### Current behavior (findings)

| Area | Finding |
|------|---------|
| **UI** | Shows exactly **8** keys — schema order 1–8; hides `date_of_issue`, `date_of_expiration`, `issuing_country` if in API response. |
| **Extraction schema** | 11 fields; **missing** `father_name`, `mother_name`, `place_of_issue`, `signature_name`. |
| **Evaluation table** | Only 5 fields: `passport_number`, `given_names`, `surname`, `date_of_birth`, `nationality`. |
| **given_names** | vs full `person.name` → **mismatch**; `rules:Name Match` **PASS** (fuzzy `given_names + surname`). |
| **surname** | Compared to **itself** → always **match** (bug). |
| **Passport Expiry** | No table row; FAIL if expiry missing or past (e.g. 2018). |

### Passport-specific tasks

| ID | Task | Files |
|----|------|-------|
| P-1 | UI: show full extraction (remove `.slice(0, 8)`) | `DocumentUploadCard.tsx` |
| P-2 | Schema: add `father_name`, `mother_name`, `place_of_issue`, `signature_name` | `document_schemas_ext.py`, `document_schemas.py` |
| P-3 | Rules: manifest-aware passport field matches; fix `given_names` / `surname` GT | `kyc_rules.py`, `main.py` |
| P-4 | LLM field table parity with P-3 | `kyc_llm_agent.py` |
| P-5 | Name Match consistency (decision: A/C in decisions log) | `kyc_rules.py`, `check_scoping.py` |
| P-6 | Tests: field GT targets, expiry row | `studio_tests/api/` |

### Passport verification checklist (post-build)

- [ ] UI shows all passport schema fields after re-extract.
- [ ] `/api/extract` keys match UI.
- [ ] Results table includes issue/expiry/father/mother/place_of_issue/signature.
- [ ] `given_names` vs manifest `given_name`, not full `person.name`.
- [ ] `date_of_expiration` row visible; Passport Expiry FAIL if past (acceptable).

---

## Document 2: Aadhaar — REVIEWED

### Manifest expectation (user manifest)

`documents.aadhaar.fields`:

| Field | Example |
|-------|---------|
| name | RAJESH SHARMA |
| dob | 21/07/1987 |
| gender | MALE |
| aadhaar | 2767 4582 4811 |
| address | 42 Mahatma Gandhi Road, Andheri West, Mumbai |
| city | MUMBAI |
| state | Maharashtra |
| pincode | 400058 |
| issue_date | 01/01/2018 |

### Critical finding: mis-detection (X-0)

**Observed on `aadhaar_clean.png` run:**

| UI slot | `extracted.document_type` | Fields shown |
|---------|---------------------------|--------------|
| Aadhaar | **pan** (wrong) | `pan_number` N/A, `name`, `father_name` N/A, `dob` |

Physical card has name, DOB, **MALE**, address, **Aadhaar number** — visible but not extracted because **PAN schema** was used.

**Evaluate** still uses slot `doc_type: aadhaar` → rules/rubric expect `aadhaar_number`, `gender`, `address` → empty → low score. **Not primarily bad photo**; **wrong schema first**.

**Reference good extract:** `studio_tests/fixtures/extracted/aadhaar_front.json` (all core fields present when type + schema correct).

### Manifest vs schema vs image vs run

| Manifest field | On card (front) | Vision schema | Observed extract UI | Results table |
|----------------|-----------------|---------------|---------------------|-----------------|
| name | Yes | Yes | Yes | match |
| dob | Yes | Yes | Yes (ISO) | match |
| gender | Yes | Yes | **No** (PAN schema) | missing |
| aadhaar | Yes | Yes (`aadhaar_number`) | **No** | missing |
| address | Yes | Yes | **No** | missing |
| pincode | Yes (in address line) | Yes | **No** | missing (rules GT `None` for pincode — bug) |
| city | In address | **No** | **No** | no row |
| state | In address | **No** | **No** | no row |
| issue_date | Not on front | **No** | **No** | no row |

### Top checks vs table (`aadhaar_clean.png`, Both + Individual)

| Check | PASS/FAIL | Aligns with table? | Notes |
|-------|-----------|-------------------|--------|
| rules:Name Match | PASS | Yes | `name` match |
| rules:DOB Match | PASS | Yes | `dob` match (normalized) |
| rules:Aadhaar Format | FAIL | Yes | no `aadhaar_number` |
| rules:Age Eligibility | PASS | — | DOB OK |
| rules:Address Present | FAIL | Yes | empty `address` |
| rules:Mandatory Fields | FAIL | Yes | weight 1.0 |
| rubric:identity_name_consistency | PASS | Mostly | LLM / cross-doc |
| rubric:identity_dob_consistency | PASS | Yes | |
| rubric:gender_consistency | PASS | **No** | table `gender` missing |
| rubric:aadhaar_validity | FAIL | Yes | |
| rubric:address_presence | FAIL | Yes | |
| rubric:required_fields_completeness | FAIL (67) | Partial | LLM partial |
| rubric:mandatory_fields | FAIL | Yes | |

### Aadhaar-specific tasks

| ID | Task | Files |
|----|------|-------|
| **A-0** | **Use UI `doc_types` for vision schema** (same as X-0); fix detector PAN/Aadhaar confusion | `main.py`, `ocr_extraction_pipeline.py`, `document_type_detector.py` |
| A-1 | Review complete (this doc) | — |
| A-2 | Extend schema: `city`, `state`, `issue_date` if required by manifest | `document_schemas_ext.py` |
| A-3 | Rules/LLM field rows: all manifest fields; `pincode` ↔ `documents.aadhaar.fields.pincode`; `aadhaar` ↔ `aadhaar_number` | `kyc_rules.py`, `kyc_llm_agent.py`, `main.py` |
| A-4 | `gender_consistency` vs `gender` row: fail when this doc’s gender missing, or hide check on card | `check_scoping.py`, rubric prompt |
| A-5 | Tests: extract with declared `aadhaar` type; field matches; mis-detect regression | `studio_tests/api/`, fixtures |
| A-6 | Show `document_type` from extract in UI with warning if ≠ upload slot | `DocumentUploadCard.tsx` (optional) |

### Aadhaar verification checklist (post-build)

- [ ] Upload Aadhaar only → extract panel shows `document_type: aadhaar` (not `pan`).
- [ ] Extract includes `aadhaar_number`, `gender`, `address`, `pincode` when on image.
- [ ] Results table: pincode vs manifest `400058`; gender vs manifest `MALE`.
- [ ] Re-run fails Aadhaar Format / mandatory if number still missing (true OCR gap).

---

## Document 3: PAN — REVIEWED

### Manifest expectation (user manifest)

`documents.pan_card.fields`:

| Field | Example |
|-------|---------|
| name | RAJESH SHARMA |
| father_name | SURESH SHARMA |
| dob | 21/07/1987 |
| pan | DVXRS2424S |
| gender | Male |
| signature_name | Rajesh Sharma |
| issue_date | 24/03/2012 |

### Manifest vs schema vs image vs run (`pan_card_clean.png`)

| Manifest field | On PAN front image | Vision schema | Extract UI | Results table |
|----------------|-------------------|---------------|------------|-----------------|
| name | Yes | Yes | Yes | match |
| father_name | Yes | Yes | Yes | match |
| dob | Yes | Yes | Yes | match |
| pan | Yes | Yes (`pan_number`) | Yes | match |
| gender | **Not printed** | **No** | **No** | no row |
| signature_name | Yes (signature) | **No** | **No** | no row |
| issue_date | **Not on front** | **No** | **No** | no row |

**Verdict:** Core extract **correct** for front-visible data. ~**97%** card score. Failures are manifest/schema/LLM completeness, not wrong doc type.

### Top checks vs table

| Check | PASS/FAIL | vs table |
|-------|-----------|----------|
| rules:Name / DOB / PAN Format / Age / Mandatory | PASS | all rows match |
| rubric:identity_* / pan_validity / mandatory_fields | PASS | |
| rubric:gender_consistency | PASS | no PAN gender row — cross-doc |
| **rubric:required_fields_completeness** | **FAIL (67)** | **all table rows match** — LLM expects manifest fields not extracted |

### PAN-specific tasks

| ID | Task | Files |
|----|------|-------|
| N-1 | Review complete (this doc) | — |
| N-2 | Schema: add `signature_name`; optional `issue_date`, `gender` only if product requires (not on front) | `document_schemas_ext.py` |
| N-3 | Field table: `signature_name`, optional `issue_date`, `gender` vs manifest; use `documents.pan_card.fields` | `kyc_rules.py`, `kyc_llm_agent.py` |
| N-4 | `required_fields_completeness`: score from extracted+manifest fields, or show LLM `detail` when FAIL | `kyc_llm_agent.py`, UI check detail |
| N-5 | Manifest: mark `gender` / `issue_date` optional if not on card front | `ground_truth_template.json` / docs |
| N-6 | Tests: PAN extract keys; completeness vs table consistency | `studio_tests/api/` |

### PAN verification checklist (post-build)

- [ ] Extract: `pan_number`, `name`, `father_name`, `dob` match image.
- [ ] If signature in schema: `signature_name` extracted or null with clear status.
- [ ] `required_fields_completeness` FAIL only when table rows fail OR documented optional manifest fields excluded.
- [ ] No FAIL on `gender` / `issue_date` when not on uploaded image side.

---

## Consolidated implementation phases (execute after approval)

### Phase 0 — Extraction correctness (blocks Aadhaar)

- [ ] **X-0 / A-0:** Declared `doc_types` drives vision schema; detector tuning; optional UI mismatch warning.

### Phase 1 — Visibility (all docs)

- [ ] **X-1:** `DocumentUploadCard` show all extracted fields.

### Phase 2 — Extraction schemas

- [ ] **P-2, A-2, N-2:** `document_schemas_ext.py` (+ `document_schemas.py` parity).

### Phase 3 — Evaluation alignment

- [ ] **X-3:** Pass manifest to rules engine.
- [ ] **P-3/P-4, A-3, N-3:** Shared `field_matches_from_manifest(doc, manifest)` (recommended).
- [ ] **P-5, A-4, N-4:** Check-level consistency.

### Phase 4 — Tests & docs

- [ ] Per-doc API tests + X-0 regression (Aadhaar slot + PAN-shaped extract).
- [ ] `kyc_studio/README.md`: declared doc type, full extract preview, manifest vs schema.

### Phase 5 — Manual QA

- [ ] Re-upload passport, aadhaar, pan clean images + manifest; run checklists above.

---

## Decisions log

| ID | Decision | Status |
|----|----------|--------|
| D-1 | Implement only after user approves consolidated plan | **Locked** |
| D-2 | Passport Name Match behavior (P-5) | **Open** — recommend A or C |
| D-3 | Expired passport: keep FAIL vs warn | **Open** — default: keep FAIL |
| D-4 | LLM `required_fields_completeness`: field-derived vs LLM-only | **Open** — PAN + passport |
| D-5 | Hide duplicate `rubric:` field rows in Both mode | **Deferred** |
| D-6 | **Declared doc type overrides detector at extract** | **Recommend: Yes** (X-0) |
| D-7 | Aadhaar `issue_date` / PAN `issue_date`: extract, optional in KYC, or back-of-card only | **Open** |
| D-8 | PAN `gender` in manifest when not on card | **Open** — optional field |

---

## Files likely touched (consolidated)

| File | Changes |
|------|---------|
| `kyc_studio/backend/main.py` | X-0: pass `doc_types` to pipeline; X-3: manifest → rules |
| `kyc_studio/backend/image_processing/ocr_extraction_pipeline.py` | X-0: optional `declared_doc_type` param |
| `kyc_studio/backend/image_processing/document_type_detector.py` | X-0: keyword scoring |
| `kyc_studio/frontend/src/components/DocumentUploadCard.tsx` | X-1, optional A-6 mismatch warning |
| `kyc_studio/backend/document_schemas_ext.py` | P-2, A-2, N-2 |
| `kyc_studio/backend/image_processing/document_schemas.py` | Schema parity |
| `kyc_studio/backend/kyc_rules.py` | P-3, A-3, N-3 |
| `kyc_studio/backend/kyc_llm_agent.py` | P-4, A-3, N-3, N-4 |
| `kyc_studio/backend/check_scoping.py` | P-5, A-4 |
| `kyc_studio/backend/canonical_mapper.py` | X-7 verify |
| `kyc_studio/backend/ground_truth_template.json` | N-5 optional field notes |
| `studio_tests/api/*.py` | P-6, A-5, N-6, X-0 |
| `kyc_studio/README.md` | Phase 4 docs |

---

## References

- Template: `kyc_studio/backend/ground_truth_template.json`
- Scoping: `kyc_studio/backend/check_scoping.py`
- Detector: `kyc_studio/backend/image_processing/document_type_detector.py` (PAN keyword `"government of india"`)
- Extract API: `kyc_studio/backend/main.py` — `doc_types` not passed to pipeline
- Normalize: `kyc_studio/backend/canonical_mapper.py` — `normalize_document(..., declared_doc_type)`
- UI cap: `DocumentUploadCard.tsx` lines 79–81
- Good Aadhaar fixture: `studio_tests/fixtures/extracted/aadhaar_front.json`
- User review images: `aadhaar_clean.png`, `pan_card_clean.png` (2026-05-18 session)

---

*Last updated: 2026-05-18 — Passport, Aadhaar, and PAN reviewed; ready for consolidate/approve before build.*

---

## Implementation notes (2026-05-18)

- **Phase 0:** `declared_doc_type` wired from `main.py` → `OCRExtractionPipeline.process_single_image`; detector tuned (Aadhaar/UIDAI boost, generic “government of india” no longer alone selects PAN); optional slot mismatch warning in `DocumentUploadCard`.
- **Phase 1:** Removed `.slice(0, 8)`; all non-`_metadata` keys shown (sorted).
- **Phase 2:** Vision schemas extended in `document_schemas_ext.py` and `document_schemas.py` (passport father/mother/place/signature; aadhaar city/state/issue_date; PAN signature/gender/issue_date).
- **Phase 3:** Shared `manifest_field_matches.py`; rules engine receives `ground_truth_manifest`; passport Name Match uses manifest `given_name`; optional fields excluded from mandatory failures; `gender_consistency` fails on Aadhaar card when gender row missing; `required_fields_completeness` derived from field rows on per-doc cards.
- **Phase 4:** `studio_tests/api/test_extract_declared_type.py`; passport fixture aligned; README + template notes. **Tests:** `pytest -q` → 24 passed, 2 skipped; Playwright e2e → 3 passed.
