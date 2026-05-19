# Compressed context — KYC extraction & evaluation alignment

**Repo:** `C:\AIIA\KYC`  
**App:** `kyc_studio/` (FastAPI backend `:8000`, Vite frontend `:6969`)  
**Full plan:** `docs/plans/2026-05-18-kyc-extraction-evaluation-alignment.md`  
**User approved:** implement alignment plan in a new agent session (May 2026).

---

## What KYC Studio does

1. **Upload** image → `POST /api/extract` → Tesseract + GPT-4o Vision → structured JSON per doc.  
2. **Run KYC** → `POST /api/evaluate` → rules and/or LLM rubric vs ground-truth manifest → scores + field table.  
3. Vision/rubric need `DIAL_API_KEY`; Tesseract must be on PATH.

**Extract pipeline (upload only):** preprocess → Tesseract (doc-type guess + OCR text hint) → GPT-4o Vision (image + hint + JSON schema) → `extracted` object.  
**Evaluate does not re-read images** — uses stored JSON + manifest.

---

## Root problems (why UI looked “wrong”)

| ID | Problem |
|----|---------|
| **X-0** | UI sends `doc_types=aadhaar` but pipeline ignores it; Tesseract detector picked **pan** for Aadhaar image → PAN schema → missing `aadhaar_number`, `gender`, `address`. Evaluate still used slot `aadhaar` → empty fields → ~25% score. |
| **X-1** | `DocumentUploadCard.tsx` `.slice(0, 8)` hides extracted keys. |
| **X-2** | Vision schemas omit manifest fields (passport father/mother/signature; aadhaar city/state; pan signature). |
| **X-3** | Rules `_field_matches` use flat `GroundTruth`, not `documents.*.fields`. |
| **X-4** | Results table shows subset of fields (passport 5 cols; no expiry row). |
| **X-5** | Top checks ≠ table (e.g. Name Match PASS + `given_names` mismatch; `gender_consistency` PASS + gender missing; PAN all rows match + `required_fields_completeness` FAIL 67). |

---

## Confirmed bugs (examples)

**Passport:** `given_names` compared to full `person.name` not `passport.fields.given_name`; `surname` compared to itself; expiry check has no table row; UI hides fields 9–11.  
**Aadhaar:** Mis-extract as PAN on `aadhaar_clean.png`; pincode rules GT is `None` despite manifest `400058`.  
**PAN:** Extract OK for front; manifest `gender`/`issue_date` not on card front; rubric completeness fails while table green.

---

## Manifest shape (Rajesh)

```json
{
  "person": { "name", "dob", "gender", "nationality" },
  "documents": {
    "passport": { "fields": { "surname", "given_name", "passport_number", "date_of_expiry", ... } },
    "aadhaar": { "fields": { "name", "dob", "gender", "aadhaar", "address", "city", "state", "pincode", "issue_date" } },
    "pan_card": { "fields": { "name", "father_name", "dob", "pan", "gender", "signature_name", "issue_date" } }
  }
}
```

Aliases: `canonical_mapper.py` — `given_name`→`given_names`, `aadhaar`→`aadhaar_number`, `pan`→`pan_number`, `date_of_expiry`→`date_of_expiration`.

---

## Already shipped (do not re-implement)

- `studio_tests/` matrix (pytest + Playwright) — **maintain after alignment**, don’t rescaffold.  
- UI: clear results on method/scope/rubric change; `resultDisplay` from stored result.  
- `check_scoping.py` per-doc card checks/scores.  
- Clear-upload buttons.

---

## Build order (phases)

0. **X-0** — `doc_types` from upload drives vision schema (`main.py`, `ocr_extraction_pipeline.py`, detector tune).  
1. **X-1** — Remove 8-field UI cap.  
2. **Schemas** — P-2, A-2, N-2 in `document_schemas_ext.py` (+ `document_schemas.py`).  
3. **Evaluate** — manifest → rules; `field_matches_from_manifest`; P-3–P-5, A-3–A-4, N-3–N-4 in `kyc_rules.py`, `kyc_llm_agent.py`, `check_scoping.py`.  
4. **Tests** — update `studio_tests/api/`, regenerate `fixtures/extracted/` if needed, README snippet.  
5. **Manual QA** — checklists in full plan.

---

## Default decisions (unless user says otherwise)

- **D-6:** Declared doc type **overrides** detector at extract — **Yes**.  
- **D-3:** Expired passport stays **FAIL**.  
- **D-2:** Align Name Match with per-field `given_names` (prefer manifest `given_name`).  
- **D-4:** Tie `required_fields_completeness` to field rows or surface LLM `detail` on FAIL.  
- **D-7/D-8:** `issue_date` / PAN `gender` — optional in scoring if not on uploaded image; document in template.

---

## Key files

| Area | Path |
|------|------|
| Extract API | `kyc_studio/backend/main.py` |
| Pipeline | `kyc_studio/backend/image_processing/ocr_extraction_pipeline.py` |
| Hybrid OCR | `hybrid_ocr_extractor.py` |
| Detector | `document_type_detector.py` |
| Schemas | `document_schemas_ext.py`, `document_schemas.py` |
| Rules | `kyc_rules.py` |
| LLM rubric | `kyc_llm_agent.py` |
| Scoping | `check_scoping.py` |
| Mapper | `canonical_mapper.py` |
| UI extract | `kyc_studio/frontend/src/components/DocumentUploadCard.tsx` |
| GT template | `kyc_studio/backend/ground_truth_template.json` |
| Tests | `studio_tests/api/`, `studio_tests/fixtures/extracted/` |
| Good Aadhaar fixture | `studio_tests/fixtures/extracted/aadhaar_front.json` |

---

## Verify commands

```powershell
cd C:\AIIA\KYC\studio_tests\api
pytest -q

cd C:\AIIA\KYC\studio_tests\e2e
npm test
```

Backend: `uvicorn main:app --reload --host 127.0.0.1 --port 8000` from `kyc_studio/backend`.  
Frontend: `npm run dev` from `kyc_studio/frontend` → `http://127.0.0.1:6969`.
