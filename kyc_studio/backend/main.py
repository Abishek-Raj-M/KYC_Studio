from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

# Use vendored OCR modules inside kyc_studio/backend/image_processing.
LOCAL_IMAGE_PROCESSING = Path(__file__).resolve().parent / "image_processing"
if str(LOCAL_IMAGE_PROCESSING) not in sys.path:
    sys.path.insert(0, str(LOCAL_IMAGE_PROCESSING))

import document_schemas  # noqa: E402
from ocr_extraction_pipeline import OCRExtractionPipeline  # noqa: E402

from canonical_mapper import normalize_document, normalize_ground_truth
from document_schemas_ext import ExtendedDocumentSchemaHandler  # noqa: E402
from kyc_llm_agent import KycLLMAgent  # noqa: E402
from kyc_rules import RuleBasedKYCEngine  # noqa: E402
from models import GroundTruth, KYCRequest  # noqa: E402


ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=ENV_PATH)

# Runtime extension to keep image_processing code unchanged while supporting Aadhaar/PAN.
document_schemas.DocumentSchemaHandler.DOCUMENT_KEYWORDS.update(
    {
        "aadhaar": ["aadhaar", "uidai", "unique identification", "aadhaar number"],
        "pan": ["pan", "permanent account number", "income tax department"],
    }
)
document_schemas.DocumentSchemaHandler.get_gpt4_vision_prompt = staticmethod(
    ExtendedDocumentSchemaHandler.get_gpt4_vision_prompt
)

app = FastAPI(title="KYC Studio API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/api/extract")
async def extract_documents(
    files: List[UploadFile] = File(...),
    doc_types: Optional[List[str]] = Form(default=None),
    sides: Optional[List[str]] = Form(default=None),
) -> Dict[str, Any]:
    api_key = os.getenv("DIAL_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="DIAL_API_KEY is not set")

    pipeline = OCRExtractionPipeline(api_key=api_key)
    extracted_docs: List[Dict[str, Any]] = []

    for idx, upload in enumerate(files):
        suffix = Path(upload.filename or "upload.png").suffix or ".png"
        payload = await upload.read()

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(payload)
            temp_path = tmp.name

        try:
            extracted = pipeline.process_single_image(temp_path)
        finally:
            try:
                os.unlink(temp_path)
            except OSError:
                pass

        extracted_docs.append(
            {
                "doc_type": (doc_types[idx] if doc_types and idx < len(doc_types) else extracted.get("document_type", "unknown")),
                "side": (sides[idx] if sides and idx < len(sides) else "front"),
                "filename": upload.filename or f"file_{idx}",
                "extracted": extracted,
            }
        )

    return {"documents": extracted_docs}


@app.post("/api/evaluate")
def evaluate_kyc(req: KYCRequest) -> Dict[str, Any]:
    docs = [normalize_document(item.extracted, item.doc_type) for item in req.extracted_docs]
    normalized_gt = normalize_ground_truth(req.ground_truth.model_dump())
    ground_truth = GroundTruth(**normalized_gt)

    if not docs:
        raise HTTPException(status_code=400, detail="No extracted documents provided")

    engine = RuleBasedKYCEngine()
    llm_agent = KycLLMAgent()

    if req.method == "rules":
        return {"result": engine.evaluate(docs=docs, ground_truth=ground_truth, scope=req.scope).model_dump()}

    if req.method == "llm":
        if not req.rubric:
            raise HTTPException(status_code=400, detail="rubric YAML is required for llm mode")
        return {
            "result": llm_agent.evaluate(
                docs=docs,
                ground_truth=ground_truth.model_dump(),
                rubric_yaml=req.rubric,
                scope=req.scope,
            ).model_dump()
        }

    if req.method == "both":
        if not req.rubric:
            raise HTTPException(status_code=400, detail="rubric YAML is required for both mode")

        rules_result = engine.evaluate(docs=docs, ground_truth=ground_truth, scope=req.scope)
        llm_result = llm_agent.evaluate(
            docs=docs,
            ground_truth=ground_truth.model_dump(),
            rubric_yaml=req.rubric,
            scope=req.scope,
        )

        combined_score = round((rules_result.overall_score + llm_result.overall_score) / 2.0, 2)
        return {
            "result": {
                "method": "both",
                "scope": req.scope,
                "overall_score": combined_score,
                "passed": combined_score >= 75,
                "summary": "Combined rule-based and rubric-based evaluation",
                "rules_result": rules_result.model_dump(),
                "llm_result": llm_result.model_dump(),
            }
        }

    raise HTTPException(status_code=400, detail="Unsupported method")


@app.get("/api/rubric/template")
def rubric_template() -> FileResponse:
    return FileResponse(
        path=Path(__file__).with_name("rubric_template.yaml"),
        filename="rubric_template.yaml",
        media_type="application/x-yaml",
    )


@app.get("/api/ground-truth/template")
def ground_truth_template() -> FileResponse:
    return FileResponse(
        path=Path(__file__).with_name("ground_truth_template.json"),
        filename="ground_truth_template.json",
        media_type="application/json",
    )


@app.get("/")
def root() -> Dict[str, Any]:
    return {
        "name": "KYC Studio API",
        "routes": [
            "GET /api/health",
            "POST /api/extract",
            "POST /api/evaluate",
            "GET /api/rubric/template",
            "GET /api/ground-truth/template",
        ],
    }
