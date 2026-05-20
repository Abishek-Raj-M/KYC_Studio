from __future__ import annotations

import os
import logging
import json
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
from kyc_rules import RuleBasedKYCEngine  # noqa: E402
from models import GroundTruth, KYCRequest, KYCResult  # noqa: E402


ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=ENV_PATH)

RULES_REFERENCE_MD = Path(__file__).resolve().parent / "reference" / "kyc-rules-reference.md"

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
logger = logging.getLogger("uvicorn.error")

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

        declared = doc_types[idx] if doc_types and idx < len(doc_types) else None
        try:
            extracted = pipeline.process_single_image(temp_path, declared_doc_type=declared)
        finally:
            try:
                os.unlink(temp_path)
            except OSError:
                pass

        if not isinstance(extracted.get("_metadata"), dict):
            extracted["_metadata"] = {}
        extracted["_metadata"]["source_file"] = upload.filename or f"file_{idx}"
        extracted["_metadata"]["uploaded_filename"] = upload.filename or f"file_{idx}"

        extracted_docs.append(
            {
                "doc_type": (doc_types[idx] if doc_types and idx < len(doc_types) else extracted.get("document_type", "unknown")),
                "side": (sides[idx] if sides and idx < len(sides) else "front"),
                "filename": upload.filename or f"file_{idx}",
                "extracted": extracted,
            }
        )

        logger.info(
            "Extracted document filename=%s doc_type=%s detected_type=%s keys=%s pan_number=%s name=%s dob=%s",
            upload.filename or f"file_{idx}",
            doc_types[idx] if doc_types and idx < len(doc_types) else "unknown",
            extracted.get("document_type", "unknown"),
            sorted(k for k in extracted.keys() if k != "_metadata"),
            extracted.get("pan_number"),
            extracted.get("name"),
            extracted.get("dob"),
        )

    return {"documents": extracted_docs}


@app.post("/api/evaluate")
def evaluate_kyc(req: KYCRequest) -> Dict[str, Any]:
    if req.method != "rules":
        raise HTTPException(
            status_code=400,
            detail="Only rule-based evaluation is supported. Remove method='llm' or method='both'.",
        )

    docs = [normalize_document(item.extracted, item.doc_type) for item in req.extracted_docs]
    raw_ground_truth = req.ground_truth_manifest or req.ground_truth.model_dump()
    normalized_gt = normalize_ground_truth(raw_ground_truth)

    logger.info(
        "Evaluate request scope=%s doc_types=%s raw_ground_truth_keys=%s",
        req.scope,
        sorted({str(d.get("document_type") or "unknown") for d in docs}),
        sorted(raw_ground_truth.keys()) if isinstance(raw_ground_truth, dict) else type(raw_ground_truth).__name__,
    )
    logger.info("Normalized ground truth=%s", normalized_gt)
    for doc in docs:
        logger.info(
            "Normalized doc document_type=%s source_file=%s name=%s dob=%s gender=%s passport_number=%s pan_number=%s aadhaar_number=%s address=%s",
            doc.get("document_type"),
            (doc.get("_metadata") or {}).get("source_file"),
            doc.get("name"),
            doc.get("dob") or doc.get("date_of_birth"),
            doc.get("gender") or doc.get("sex"),
            doc.get("passport_number"),
            doc.get("pan_number"),
            doc.get("aadhaar_number"),
            doc.get("address"),
        )

    gt_has_core = any(
        str(normalized_gt.get(key) or "").strip()
        for key in ["name", "dob", "gender", "address", "nationality"]
    ) or bool(normalized_gt.get("id_numbers"))
    if not gt_has_core:
        raise HTTPException(status_code=400, detail="Ground truth JSON is required and cannot be empty")

    ground_truth = GroundTruth(**normalized_gt)

    if not docs:
        raise HTTPException(status_code=400, detail="No extracted documents provided")

    engine = RuleBasedKYCEngine()
    result = engine.evaluate(
        docs=docs,
        ground_truth=ground_truth,
        scope=req.scope,
        ground_truth_manifest=raw_ground_truth,
    )
    logger.info("Rules result overall_score=%s passed=%s summary=%s", result.overall_score, result.passed, result.summary)
    for check in result.checks:
        logger.info("Rules check name=%s passed=%s score=%s detail=%s", check.name, check.passed, check.score, check.detail)
    return {"result": result.model_dump()}


@app.post("/api/run-upload")
async def run_upload_flow(
    files: List[UploadFile] = File(...),
    doc_types: List[str] = Form(...),
    sides: Optional[List[str]] = Form(default=None),
    ground_truth_file: UploadFile = File(...),
    scope: str = Form("individual"),
) -> Dict[str, Any]:
    extracted = await extract_documents(files=files, doc_types=doc_types, sides=sides)

    gt_text = (await ground_truth_file.read()).decode("utf-8")
    gt_payload = json.loads(gt_text)
    normalized_gt = normalize_ground_truth(gt_payload)

    req = KYCRequest(
        extracted_docs=extracted["documents"],
        ground_truth=GroundTruth(**normalized_gt),
        ground_truth_manifest=gt_payload,
        scope=scope,  # type: ignore[arg-type]
    )
    return evaluate_kyc(req)


@app.get("/api/reference/rules")
def rules_reference_download() -> FileResponse:
    return FileResponse(
        path=RULES_REFERENCE_MD,
        filename="kyc-rules-reference.md",
        media_type="text/markdown",
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
            "POST /api/run-upload",
            "GET /api/reference/rules",
            "GET /api/ground-truth/template",
        ],
    }
