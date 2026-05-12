# Plan: KYC Studio — Full-Stack KYC Agent

## TL;DR
Build `KYC/kyc_studio/` with a FastAPI backend and a React (Vite + Tailwind) frontend. The app is a single fixed-viewport page (no page scroll) where the user uploads Passport / Aadhaar / PAN images (front required, back optional), a ground-truth JSON, and optionally a rubric YAML, then runs rule-based and/or LLM rubric-based KYC evaluation. Extraction reuses the existing `image_processing/` pipeline unchanged.

---

## Phase 1 — Backend

### 1. Directory scaffold
Create `KYC/kyc_studio/backend/` and `KYC/kyc_studio/frontend/`.

### 2. Extend document schemas (`document_schemas_ext.py`)
Add `aadhaar` and `pan` to `DOCUMENT_KEYWORDS` and `schemas` dict in a new file that subclasses/extends `DocumentSchemaHandler` (do NOT touch existing `image_processing/` files).
- Aadhaar fields: `aadhaar_number`, `name`, `dob`, `gender`, `address`, `pincode`
- PAN fields: `pan_number`, `name`, `father_name`, `dob`

### 3. Pydantic models (`models.py`)
- `DocumentUpload`: doc_type, side (front/back), image bytes
- `GroundTruth`: name, dob, gender, address, nationality, id_numbers (dict)
- `KYCRequest`: list of extracted docs, ground_truth, method (rules | llm | both), scope (individual | all), rubric (optional YAML str)
- `KYCResult`: per-document scores, field-level match details, overall score, pass/fail

### 4. OCR extraction endpoint (`main.py`)
`POST /api/extract` — accepts multipart form with image files. For each image, calls existing `OCRExtractionPipeline.process_single_image()` (import from `../../image_processing/`). Returns structured JSON.

### 5. Rule-based KYC engine (`kyc_rules.py`)
Bank-style checks — each returns a `CheckResult(name, passed, score, detail)`:
1. **Name Match** — fuzzy match (difflib SequenceMatcher ≥ 0.85) ground truth name vs each doc
2. **DOB Match** — exact match ground truth DOB vs Aadhaar / Passport DOB
3. **Aadhaar Format** — regex `^\d{12}$`
4. **PAN Format** — regex `^[A-Z]{5}[0-9]{4}[A-Z]$`
5. **Passport Expiry** — `date_of_expiration` > today
6. **Cross-Document Name Consistency** — all docs agree (fuzzy ≥ 0.85)
7. **Age Eligibility** — derived age ≥ 18
8. **Gender Consistency** — Aadhaar vs Passport match if both present
9. **Required Fields Completeness** — no null on critical fields per doc type
10. **Address Present** — Aadhaar address field non-null

Weighted scoring: each check has a weight; final score = Σ(passed_weight) / Σ(all_weights) × 100.

### 6. LLM rubric agent (`kyc_llm_agent.py`)
- Accepts rubric YAML (uploaded by user) + extracted doc data + ground truth
- Builds a structured prompt: rubric checks → LLM evaluates each → returns JSON scores per check
- Uses `get_llm()` from `common.py`
- Returns same `KYCResult` shape as rule engine

### 7. Rubric template download (`rubric_template.yaml`)
Static YAML file with annotated template:
```yaml
rubric_version: "1.0"
name: "KYC Rubric"
checks:
  - id: name_match
    description: "Full name matches ground truth"
    weight: 0.30
    criteria: "Use fuzzy match. Accept if similarity >= 0.85"
  - id: dob_match
    description: "Date of birth matches"
    weight: 0.25
    criteria: "Exact date match required (YYYY-MM-DD)"
  - id: document_validity
    description: "Documents are not expired"
    weight: 0.20
    criteria: "Check expiration dates where applicable"
  - id: format_validation
    description: "Document numbers conform to known formats"
    weight: 0.15
    criteria: "PAN: 5 letters + 4 digits + 1 letter. Aadhaar: 12 digits"
  - id: cross_doc_consistency
    description: "Name and DOB consistent across all submitted documents"
    weight: 0.10
    criteria: "All docs must agree within fuzzy threshold"
```

### 8. Evaluation endpoints (`main.py`)
- `POST /api/evaluate` — runs rule, llm, or both based on `method` param; handles `scope` (individual per doc or combined)
- `GET /api/rubric/template` — streams `rubric_template.yaml` as file download

### 9. Backend `requirements.txt`
fastapi, uvicorn, python-multipart, pydantic, python-dotenv, pytesseract, opencv-python-headless, pillow, numpy, openai, rapidfuzz, pyyaml

---

## Phase 2 — Frontend

### 10. Vite + React + Tailwind scaffold (`frontend/`)
`package.json` with: react 18, react-dom, typescript, vite, tailwindcss, postcss, autoprefixer, lucide-react.
Tailwind configured with `darkMode: 'class'`.

### 11. Theme system
- Copy token approach from `ui-themes-template.md` sections 3 and 7 (CSS vars in `index.css`, `ThemeContext.tsx`, blocking script in `index.html`, `ThemeToggle` button). **No sidebar nav.**
- Only need: dark/light toggle in top-right of header.

### 12. Single-page fixed-viewport layout (`App.tsx`)
```
html, body, #root → height: 100vh; overflow: hidden
  ┌─────────────────────────────────────────────────────┐
  │  Header (h-12): "KYC Studio" title + ThemeToggle    │
  ├───────────────────────┬─────────────────────────────┤
  │  LEFT PANEL (38%)     │  RIGHT PANEL (62%)          │
  │  overflow-y: auto     │  overflow-y: auto           │
  │  flex-1 min-h-0       │  flex-1 min-h-0             │
  │                       │                             │
  │  ① Document Uploads   │  Results                    │
  │  ② Ground Truth       │  (empty state until run)    │
  │  ③ Evaluation Config  │                             │
  │  ④ Rubric Upload      │                             │
  │  [Run KYC] button     │                             │
  └───────────────────────┴─────────────────────────────┘
```
Key CSS: root `display: flex; flex-direction: column; height: 100vh; overflow: hidden`. Body = header + `flex-1 flex min-h-0`. Both panels = `flex-1 min-h-0 overflow-y-auto`.

### 13. `DocumentUploadCard.tsx`
One card per document type (Passport | Aadhaar | PAN).
- Compact drag-and-drop zone for **Front** (required, labelled)
- `+ Add back side` toggle link → expands a second drag-and-drop zone for **Back** (optional, always optional for all doc types)
- Shows thumbnail preview on drop
- Uses `react-dropzone` or native HTML5 drag-drop
- Displays document type icon + extracted status indicator after extraction

### 14. `GroundTruthUpload.tsx`
- JSON file upload drop zone
- Shows parsed key fields (name, dob) as a mini preview after upload
- Download schema template button

### 15. `EvaluationConfig.tsx`
- **Method** toggle: `Rule-Based` | `LLM Rubric` | `Both` (segmented control)
- **Scope** toggle: `Individual` | `All Together` (toggle pill)
- Rubric upload section (visible only when method = LLM or Both)

### 16. `RubricUpload.tsx`
- YAML file drop zone
- Download template button → calls `GET /api/rubric/template`

### 17. `ResultsPanel/` components
- `OverallScoreCard.tsx` — large pass/fail badge + percentage score
- `DocumentResultCard.tsx` — per-document card with collapsible check details
- `FieldMatchTable.tsx` — table: Field | Extracted | Ground Truth | Status (✓/✗)
- `EvaluationModeBadge.tsx` — shows which method produced the result
- Individual vs All Toggle reflected in results display

### 18. `KYCContext.tsx`
Shared state: uploaded files, extraction results, ground truth, rubric, config, KYC results. Drives both panels.

### 19. API client (`api.ts`)
Typed fetch wrappers for `/api/extract` and `/api/evaluate`.

---

## Phase 3 — Integration & Polish

### 20. Wire extraction flow
On file drop → auto-call `/api/extract` per image → show extracted data badge on card.

### 21. Wire evaluation flow
"Run KYC" button → POST to `/api/evaluate` with extracted docs + ground truth + method + scope + rubric → populate results panel.

### 22. Per-document vs all-together display
- Individual: one `DocumentResultCard` per doc
- All Together: single combined `OverallScoreCard` + merged `FieldMatchTable`

### 23. Loading and error states
Spinner overlay during extraction/evaluation, toast on API error.

---

## Relevant Files

**Reuse (read-only):**
- `image_processing/ocr_extraction_pipeline.py` — `OCRExtractionPipeline.process_single_image()` — main extraction entry point
- `image_processing/hybrid_ocr_extractor.py` — Tesseract + GPT-4o Vision
- `image_processing/document_schemas.py` — `DocumentSchemaHandler` — extend for Aadhaar/PAN
- `image_processing/document_type_detector.py` — keyword-based type detection
- `image_processing/enhanced_image_preprocessor.py` — image preprocessing
- `common.py` — `get_llm()`, `get_embedder()` — LLM init

**Create:**
- `kyc_studio/backend/main.py`
- `kyc_studio/backend/kyc_rules.py`
- `kyc_studio/backend/kyc_llm_agent.py`
- `kyc_studio/backend/document_schemas_ext.py`
- `kyc_studio/backend/models.py`
- `kyc_studio/backend/rubric_template.yaml`
- `kyc_studio/backend/requirements.txt`
- `kyc_studio/frontend/` (full Vite+React app)

---

## Verification
1. Drop a Passport image → card shows extracted name/number
2. Drop an Aadhaar image → Aadhaar number extracted + formatted
3. Drop a PAN image → PAN number extracted with format check
4. Run Rule-Based → results panel shows 10 checks with scores
5. Run LLM Rubric (with template downloaded + re-uploaded) → per-rubric-check scores
6. Run Both → two result columns side by side
7. Toggle Individual ↔ All Together → score display changes
8. Dark/light toggle → full theme swap, no FOUC
9. Back-side upload: click "+ Add back side" → second drop zone appears; it's skippable
10. All content visible on 1920×1080 without page scroll

---

## Decisions
- Back side is **optional for ALL document types** (not pre-assumed required for any)
- Aadhaar and PAN schemas added in a NEW `document_schemas_ext.py` — existing `image_processing/` files untouched
- No sidebar nav (deferred to when merging with parent project)
- Theme: dark/light only — matching token approach from `ui-themes-template.md` sections 3 & 7
- Backend imports `image_processing` via `sys.path` insertion (no package restructuring)
- Rule-based KYC modelled on Indian RBI/UIDAI KYC norms (name + DOB + format + expiry + cross-doc consistency)
