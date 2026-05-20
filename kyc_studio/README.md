# KYC Studio

KYC Studio is a full-stack KYC evaluation app with:
- FastAPI backend for OCR extraction + KYC scoring
- React (Vite + Tailwind) frontend for uploads and results

## Prerequisites

- Python 3.10+
- Node.js 18+
- npm 9+
- Tesseract OCR installed

### Tesseract (Windows)
Install Tesseract and ensure `tesseract.exe` is available in PATH.
Default install path is usually:
`C:\Program Files\Tesseract-OCR\tesseract.exe`

## Environment Setup

Create or update `.env` in this folder (`C:\AIIA\KYC\kyc_studio\.env`):

```env
DIAL_API_KEY=your_dial_api_key_here
KYC_LLM_MODEL=gpt-4o
```

Notes:
- `DIAL_API_KEY` is required for OCR Vision extraction.
- `KYC_LLM_MODEL` is optional (defaults to `gpt-4o`).

## Project Structure

```text
kyc_studio/
  backend/
    main.py
    kyc_rules.py
    models.py
    document_schemas_ext.py
    image_processing/
    requirements.txt
  frontend/
    src/
    package.json
```

## Backend Startup (FastAPI)

From `kyc_studio/backend` folder:

```powershell
cd C:\AIIA\KYC\kyc_studio\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Backend base URL:
- `http://127.0.0.1:8000`

Health check:
- `GET http://127.0.0.1:8000/api/health`

## Frontend Startup (Vite)

Open a new terminal from `kyc_studio` folder:

```powershell
cd C:\AIIA\KYC\kyc_studio\frontend
npm install
npm run dev
```

Frontend URL (default):
- `http://127.0.0.1:6969`

The Vite dev server proxies `/api/*` to `http://127.0.0.1:8000`.

## Quick Usage Flow

1. Open frontend in browser.
2. Upload document images (Passport/Aadhaar/PAN front; back optional). The upload slot sets the vision schema at extract time (`doc_types` overrides Tesseract detection). The extract preview shows all returned fields (no 8-field cap).
3. Upload ground-truth JSON.
4. Choose evaluation scope:
   - **Per document** — one score card per uploaded document
   - **Combined** — single overall score with cross-document checks
5. Click **Run KYC**.
6. Review overall score, per-document checks, and field match details.

## Available Backend APIs

- `POST /api/extract` - OCR extraction for uploaded files (pass `doc_types` per file so Aadhaar/PAN schemas match the slot)
- `POST /api/evaluate` - rule-based KYC evaluation (`scope`: `individual` | `all`)
- `GET /api/reference/rules` - built-in rules reference (Markdown text for in-app viewer)
- `GET /api/ground-truth/template` - download ground truth JSON template

## Troubleshooting

### 1. `DIAL_API_KEY is not set`
Set `DIAL_API_KEY` in `.env` and restart backend.

### 2. OCR errors about Tesseract
Install Tesseract and make sure it is in PATH.

### 3. Frontend cannot call backend
Ensure backend is running on `127.0.0.1:8000` and frontend on `6969`.

### 4. Dependency install issues
Upgrade pip/npm:

```powershell
python -m pip install --upgrade pip
npm install -g npm
```
