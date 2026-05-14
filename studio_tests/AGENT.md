# KYC Studio matrix tests — agent handoff

This folder contains **Tier A** (deterministic API tests), **Tier B** (optional live LLM), and **Tier C** (Playwright UI). Use it to verify rubric routing, ground-truth alignment, and UI behavior after config changes.

## Layout

- [`api/`](api/) — `pytest` against FastAPI `TestClient` (no running server required for Tier A).
- [`fixtures/ground_truth/rajesh_manifest.json`](fixtures/ground_truth/rajesh_manifest.json) — manifest-style ground truth (Aadhaar ID normalized to 12 digits for rule matching).
- [`fixtures/extracted/`](fixtures/extracted/) — frozen `DocumentUpload` JSON (front-only) aligned with that manifest. Passport uses a **non-expired** `date_of_expiration` and a placeholder `surname` so rule-based checks stay stable in CI; see [`fixtures/images/README.md`](fixtures/images/README.md).
- [`fixtures/rubrics/`](fixtures/rubrics/) — copies of YAML rubrics from `test_set/`.
- [`e2e/`](e2e/) — Playwright specs (`playwright.config.cjs`; mock `/api/extract` and `/api/evaluate` where noted).

## Prerequisites

**Tier A + LLM 400 routing (default CI slice)**

- Python 3.10+ with `kyc_studio/backend` dependencies installed (same as backend `requirements.txt`).
- No `DIAL_API_KEY` required for rules-only tests or for `per_doc` missing-rubric 400 test.

**Tier B (`pytest -m integration`)**

- `DIAL_API_KEY` in `kyc_studio/.env` (or environment).
- Network access to the configured LLM proxy.

**Tier C (Playwright)**

- From repo root, start the frontend: `cd kyc_studio/frontend && npm install && npm run dev` (default `http://127.0.0.1:6969`; override with `KYC_BASE_URL` if the port differs).
- If the app is not reachable, Playwright tests **skip** instead of failing.

## Commands

From `studio_tests/api` (after `pip install -r requirements.txt` and backend deps):

```powershell
cd C:\AIIA\KYC\studio_tests\api
python -m pip install -r requirements.txt
python -m pip install -r ..\..\kyc_studio\backend\requirements.txt
python -m pytest -m "not integration" -v
```

Optional live LLM checks:

```powershell
python -m pytest -m integration -v
```

Playwright (with frontend running):

```powershell
cd C:\AIIA\KYC\studio_tests\e2e
npm install
npx playwright install chromium
$env:KYC_BASE_URL = "http://127.0.0.1:6969"   # adjust if Vite picked another port
npm test
```

## What failures usually mean

| Symptom | Likely area |
|--------|-------------|
| Rules score / mandatory fields changed | [`kyc_studio/backend/kyc_rules.py`](../kyc_studio/backend/kyc_rules.py) or fixture JSON vs manifest drift |
| `Missing rubric` 400 unexpected | [`kyc_studio/backend/main.py`](../kyc_studio/backend/main.py) `run_llm_with_rubrics` |
| LLM integration 4xx/5xx | Keys, proxy, or rubric YAML shape |
| Playwright: results not clearing on scope change | [`kyc_studio/frontend/src/App.tsx`](../kyc_studio/frontend/src/App.tsx) `useEffect` that clears `result` when `method` / `scope` / `rubricMode` change |

## Matrix covered (Tier A)

- All **7** non-empty subsets of `{passport, aadhaar, pan}` × `scope` **`individual`** and **`all`**, `method: rules`, manifest ground truth.
- Extra case: all three docs with manifest `id_numbers` field-match alignment for PAN, Aadhaar, passport.

Tier B adds: `per_doc` missing rubric → **400** without `DIAL_API_KEY`; with key, smoke `llm` per-doc and single combined rubric on two docs.

## Clean images (Tier B only)

Place front scans under `test_set/rajesh_sharma/indian_doc/clean/` (or paths described in [`fixtures/images/README.md`](fixtures/images/README.md)) when running extraction integration tests — not required for Tier A.
