# Agent instructions — Build KYC extraction & evaluation alignment

Use this file as your **primary briefing** for a new Cursor chat. The user will paste or reference this path and ask you to implement the plan.

---

## Your mission

Implement **`docs/plans/2026-05-18-kyc-extraction-evaluation-alignment.md`** end-to-end so that:

- Upload slot (Passport / Aadhaar / PAN) controls **which fields** vision extracts.
- **All** extracted fields are visible in the UI.
- Vision schemas and results tables align with **`documents.*.fields`** in the ground-truth manifest.
- Top checks and bottom field rows **agree** where they measure the same thing (fewer false contradictions).

**Read first (in order):**

1. `docs/context/kyc-extraction-evaluation-alignment-context.md` — compressed facts.  
2. `docs/plans/2026-05-18-kyc-extraction-evaluation-alignment.md` — full spec, checklists, task IDs.

---

## Copy-paste prompt for the user

```text
Implement the KYC extraction & evaluation alignment plan.

Read:
- docs/context/AGENT-INSTRUCTIONS.md
- docs/context/kyc-extraction-evaluation-alignment-context.md
- docs/plans/2026-05-18-kyc-extraction-evaluation-alignment.md

Follow phases 0→4 in the plan. Use default decisions in the context file unless I object.

Do NOT re-scaffold studio_tests/ or redo unrelated UI (stale results, clear uploads, check scoping) unless broken by your changes.

After implementation: run pytest in studio_tests/api, update extracted fixtures if extract shape changed, run Playwright e2e if feasible. Do not git push unless I ask.

Report: what changed per phase, test results, and any open decisions left for me.
```

---

## Scope boundaries

### In scope

- Phase 0–5 from the plan (code + tests + README notes).  
- Minimal shared helper for manifest field matches (recommended in plan).  
- Regenerate or hand-update `studio_tests/fixtures/extracted/*.json` when extract output changes.  
- Fix/update `studio_tests/api` tests affected by new field rows or X-0.

### Out of scope (unless user asks)

- Rewriting the matrix-test plan or large refactors outside listed files.  
- Changing rules so `scope: individual` vs `all` changes **scoring** (plan notes: presentation-only today).  
- Removing duplicate `rules:` / `rubric:` rows in Both mode (D-5 deferred).  
- Committing or pushing to remote without explicit request.

---

## Implementation order (mandatory)

### Phase 0 — X-0 / A-0 (do first)

**Problem:** `POST /api/extract` receives `doc_types` from the frontend but `OCRExtractionPipeline.process_single_image` only uses `DocumentTypeDetector` on Tesseract text. Aadhaar images were extracted with the **PAN** schema.

**Do:**

1. Add optional `declared_doc_type: str | None` to `process_single_image` (and wire from `main.py` using `doc_types[idx]`).  
2. When `declared_doc_type` is set, use it for `extract_hybrid(..., doc_type=...)` and vision prompt; still run Tesseract for OCR hint. Optionally compare detector vs declared and log warning.  
3. Tune `document_type_detector.py`: reduce false PAN match on `"government of india"` alone; strengthen Aadhaar signals.  
4. (Optional A-6) In `DocumentUploadCard.tsx`, warn if `extracted.document_type` ≠ selected slot.

**Verify:** Upload Aadhaar only → `extracted.document_type` is `aadhaar` and includes `aadhaar_number`, `gender`, `address` when visible on card.

---

### Phase 1 — X-1 / P-1

**File:** `kyc_studio/frontend/src/components/DocumentUploadCard.tsx`  
Remove `.slice(0, 8)`; show all non-`_metadata` keys; stable sort optional.

---

### Phase 2 — Schemas (P-2, A-2, N-2)

**Files:** `kyc_studio/backend/document_schemas_ext.py`, `kyc_studio/backend/image_processing/document_schemas.py`

| Doc | Add to vision JSON schema |
|-----|---------------------------|
| Passport | `father_name`, `mother_name`, `place_of_issue`, `signature_name` |
| Aadhaar | `city`, `state`, `issue_date` (nullable if not visible) |
| PAN | `signature_name`; `issue_date` / `gender` only if you document as optional when absent on front |

Keep `canonical_mapper.py` aliases in sync (X-7).

---

### Phase 3 — Evaluation (X-3, X-4, P-3–P-5, A-3–A-4, N-3–N-4)

1. **`main.py`:** Pass `ground_truth_manifest` (raw) into `RuleBasedKYCEngine.evaluate` (LLM path already has it).  
2. **`kyc_rules.py`:** Implement manifest-aware field matches per doc type (shared helper encouraged).  
   - Passport: fix `given_names` → `documents.passport.fields.given_name`; `surname` → manifest surname (not self-compare); add rows for sex, expiry, issue, father, mother, place_of_issue, signature, etc.  
   - Aadhaar: all manifest fields including `pincode` from `documents.aadhaar.fields.pincode`.  
   - PAN: `pan_number` ↔ `pan`; add signature/issue/gender rows with optional scoring per D-8.  
3. **`kyc_llm_agent.py`:** Mirror rules field lists in `_field_matches_for_doc`.  
4. **`check_scoping.py` / rules:** P-5, A-4 — reduce Name Match vs `given_names` contradiction; scope or fail `gender_consistency` on Aadhaar card when this doc’s gender is missing (pick one approach, note in commit).  
5. **N-4:** For `required_fields_completeness`, either derive score from present extracted fields vs manifest required set, or always attach LLM `detail` to the check in the API response/UI.

**Defaults:** D-3 keep passport expiry FAIL if date in past. D-2 align name checks with field rows.

---

### Phase 4 — Tests & docs

- Add/update tests in `studio_tests/api/` for X-0 regression and manifest field GT targets.  
- Update `studio_tests/fixtures/extracted/` if extract JSON shape changes (especially aadhaar).  
- Short update to `kyc_studio/README.md` (declared doc type at extract, full preview).  
- Run: `pytest -q` from `studio_tests/api`; Playwright from `studio_tests/e2e` if deps available.

---

### Phase 5 — Manual QA

Walk checklists in the plan for passport, aadhaar, pan (user’s clean images + Rajesh manifest).

---

## Coding standards

- Match existing style; minimal diff; no drive-by refactors.  
- Do not commit secrets.  
- Run tests before claiming done (verification-before-completion).  
- Update plan doc checkboxes or add a short `## Implementation notes` section at bottom of the plan with date + what was done, if helpful.

---

## Success criteria (acceptance)

- [ ] Aadhaar upload → extract JSON is Aadhaar-shaped, not PAN-shaped.  
- [ ] UI shows full extract payload.  
- [ ] Results field tables include manifest fields documented in the plan.  
- [ ] Passport `given_names` row compares to manifest given name, not full person name only.  
- [ ] `pytest` in `studio_tests/api` passes (or document skips with reason).  
- [ ] No new contradictions: PAN table all-match should not FAIL completeness without visible `detail`.

---

## If stuck

| Symptom | Likely cause | Where to look |
|---------|--------------|---------------|
| Aadhaar still PAN fields | X-0 not wired | `main.py`, `ocr_extraction_pipeline.py` |
| Table still 5 passport cols | P-3 not done | `kyc_rules.py` `_field_matches` |
| pincode always missing | GT None in rules | `kyc_rules.py` aadhaar branch |
| Tests fail on passport expiry | Rajesh passport expired 2018 | Expected FAIL; encode in tests |

---

*Created for handoff to a new agent session — May 2026.*
