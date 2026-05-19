from __future__ import annotations

import os
import logging
import json
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse

# Use vendored OCR modules inside kyc_studio/backend/image_processing.
LOCAL_IMAGE_PROCESSING = Path(__file__).resolve().parent / "image_processing"
if str(LOCAL_IMAGE_PROCESSING) not in sys.path:
    sys.path.insert(0, str(LOCAL_IMAGE_PROCESSING))

import document_schemas  # noqa: E402
from ocr_extraction_pipeline import OCRExtractionPipeline  # noqa: E402

from canonical_mapper import normalize_document, normalize_ground_truth
from document_schemas_ext import ExtendedDocumentSchemaHandler  # noqa: E402
from kyc_llm_agent import KycLLMAgent  # noqa: E402
from builtin_eval import (  # noqa: E402
    BUILTIN_RUBRICS_DIR,
    RUBRIC_FILES,
    RULES_REFERENCE_MD,
    builtin_rubric_map_for_doc_types,
    load_builtin_rubric_yaml,
    normalize_doc_type,
    rubric_markdown_for_doc_type,
)
from kyc_rules import RuleBasedKYCEngine  # noqa: E402
from models import CheckResult, GroundTruth, KYCRequest, KYCResult  # noqa: E402


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
    docs = [normalize_document(item.extracted, item.doc_type) for item in req.extracted_docs]
    doc_types_in_scope = sorted({str(d.get("document_type") or "unknown") for d in docs})
    raw_ground_truth = req.ground_truth_manifest or req.ground_truth.model_dump()
    normalized_gt = normalize_ground_truth(raw_ground_truth)

    logger.info(
        "Evaluate request method=%s scope=%s doc_types=%s raw_ground_truth_keys=%s",
        req.method,
        req.scope,
        doc_types_in_scope,
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

    # Enforce ground truth as mandatory verification context for all evaluation modes.
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

    def _resolve_rubric_map() -> Dict[str, str]:
        if req.rubrics_by_doc_type:
            return {
                normalize_doc_type(k): v
                for k, v in req.rubrics_by_doc_type.items()
                if v and str(v).strip()
            }
        return builtin_rubric_map_for_doc_types(doc_types_in_scope)

    def run_llm_with_rubrics() -> KYCResult:
        if req.rubric_mode == "single" and req.rubric and str(req.rubric).strip():
            llm_agent = KycLLMAgent()
            return llm_agent.evaluate(
                docs=docs,
                ground_truth=ground_truth.model_dump(),
                ground_truth_manifest=raw_ground_truth,
                rubric_yaml=req.rubric,
                scope=req.scope,
                doc_types_in_scope=doc_types_in_scope,
            )

        rubric_map = _resolve_rubric_map()
        per_doc_pairs: List[tuple[Dict[str, Any], str, str]] = []
        for doc in docs:
            doc_type = str(doc.get("document_type") or "unknown").lower().strip()
            canonical = normalize_doc_type(doc_type)
            rubric_yaml = rubric_map.get(canonical)
            if not rubric_yaml:
                raise HTTPException(status_code=400, detail=f"No built-in rubric for document type: {doc_type}")
            per_doc_pairs.append((doc, rubric_yaml, doc_type))

        llm_agent = KycLLMAgent()
        doc_results = []
        all_checks: List[CheckResult] = []

        for doc, rubric_yaml, doc_type in per_doc_pairs:
            single_result = llm_agent.evaluate(
                docs=[doc],
                ground_truth=ground_truth.model_dump(),
                ground_truth_manifest=raw_ground_truth,
                rubric_yaml=rubric_yaml,
                scope="individual",
                doc_types_in_scope=[doc_type],
            )

            doc_results.extend(single_result.per_document_results)
            all_checks.extend(
                [
                    CheckResult(
                        name=f"{doc_type}:{check.name}",
                        passed=check.passed,
                        score=check.score,
                        detail=check.detail,
                        weight=check.weight,
                    )
                    for check in single_result.checks
                ]
            )

        overall = round(sum(r.score for r in doc_results) / max(len(doc_results), 1), 2)
        return KYCResult(
            method="llm",
            scope=req.scope,
            overall_score=overall,
            passed=overall >= 75,
            summary="LLM rubric evaluation completed with per-document rubrics",
            per_document_results=doc_results,
            checks=all_checks,
        )

    if req.method == "rules":
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

    if req.method == "llm":
        result = run_llm_with_rubrics()
        logger.info("LLM result overall_score=%s passed=%s summary=%s", result.overall_score, result.passed, result.summary)
        for check in result.checks:
            logger.info("LLM check name=%s passed=%s score=%s detail=%s", check.name, check.passed, check.score, check.detail)
        return {"result": result.model_dump()}

    if req.method == "both":
        rules_result = engine.evaluate(
            docs=docs,
            ground_truth=ground_truth,
            scope=req.scope,
            ground_truth_manifest=raw_ground_truth,
        )
        llm_result = run_llm_with_rubrics()

        rules_weight = 0.5
        llm_weight = 0.5
        combined_score = round((rules_result.overall_score * rules_weight) + (llm_result.overall_score * llm_weight), 2)

        combined_per_doc_results = []
        llm_by_doc = {doc.document_id: doc for doc in llm_result.per_document_results}
        for rules_doc in rules_result.per_document_results:
            llm_doc = llm_by_doc.get(rules_doc.document_id)
            llm_doc_score = llm_doc.score if llm_doc else 0.0
            merged_checks = [
                CheckResult(
                    name=f"rules:{check.name}",
                    passed=check.passed,
                    score=check.score,
                    detail=check.detail,
                    weight=check.weight,
                )
                for check in rules_doc.checks
            ]
            if llm_doc:
                merged_checks.extend(
                    [
                        CheckResult(
                            name=f"rubric:{check.name}",
                            passed=check.passed,
                            score=check.score,
                            detail=check.detail,
                            weight=check.weight,
                        )
                        for check in llm_doc.checks
                    ]
                )

            merged_field_matches = [
                {
                    "field": f"rules:{fm.field}",
                    "extracted": fm.extracted,
                    "ground_truth": fm.ground_truth,
                    "status": fm.status,
                }
                for fm in rules_doc.field_matches
            ]
            if llm_doc:
                merged_field_matches.extend(
                    [
                        {
                            "field": f"rubric:{fm.field}",
                            "extracted": fm.extracted,
                            "ground_truth": fm.ground_truth,
                            "status": fm.status,
                        }
                        for fm in llm_doc.field_matches
                    ]
                )

            combined_doc_score = round((rules_doc.score * rules_weight) + (llm_doc_score * llm_weight), 2)
            combined_per_doc_results.append(
                {
                    "document_id": rules_doc.document_id,
                    "doc_type": rules_doc.doc_type,
                    "score": combined_doc_score,
                    "passed": combined_doc_score >= 75,
                    "checks": [check.model_dump() for check in merged_checks],
                    "field_matches": merged_field_matches,
                }
            )

        return {
            "result": {
                "method": "both",
                "scope": req.scope,
                "overall_score": combined_score,
                "passed": combined_score >= 75,
                "summary": "Combined rule-based and rubric-based evaluation",
                "score_breakdown": {
                    "rules_weight": rules_weight,
                    "rubric_weight": llm_weight,
                    "rules_score": rules_result.overall_score,
                    "rubric_score": llm_result.overall_score,
                    "rules_contribution": round(rules_result.overall_score * rules_weight, 2),
                    "rubric_contribution": round(llm_result.overall_score * llm_weight, 2),
                },
                "combined_result": {
                    "overall_score": combined_score,
                    "passed": combined_score >= 75,
                    "summary": "Combined rule-based and rubric-based evaluation",
                    "per_document_results": combined_per_doc_results,
                    "checks": [
                        *[
                            {
                                "name": f"rules:{check.name}",
                                "passed": check.passed,
                                "score": check.score,
                                "detail": check.detail,
                                "weight": check.weight,
                            }
                            for check in rules_result.checks
                        ],
                        *[
                            {
                                "name": f"rubric:{check.name}",
                                "passed": check.passed,
                                "score": check.score,
                                "detail": check.detail,
                                "weight": check.weight,
                            }
                            for check in llm_result.checks
                        ],
                    ],
                },
                "rules_result": rules_result.model_dump(),
                "llm_result": llm_result.model_dump(),
            }
        }

    raise HTTPException(status_code=400, detail="Unsupported method")


@app.post("/api/run-upload")
async def run_upload_flow(
    files: List[UploadFile] = File(...),
    doc_types: List[str] = Form(...),
    sides: Optional[List[str]] = Form(default=None),
    ground_truth_file: UploadFile = File(...),
    method: str = Form("rules"),
    scope: str = Form("individual"),
    rubric_mode: str = Form("single"),
    rubric_file: Optional[UploadFile] = File(default=None),
    rubrics_by_doc_type_json: Optional[str] = Form(default=None),
) -> Dict[str, Any]:
    extracted = await extract_documents(files=files, doc_types=doc_types, sides=sides)

    gt_text = (await ground_truth_file.read()).decode("utf-8")
    gt_payload = json.loads(gt_text)
    normalized_gt = normalize_ground_truth(gt_payload)

    rubric_text: Optional[str] = None
    if rubric_file is not None:
        rubric_text = (await rubric_file.read()).decode("utf-8")

    rubrics_by_doc_type: Dict[str, str] = {}
    if rubrics_by_doc_type_json:
        rubrics_by_doc_type = json.loads(rubrics_by_doc_type_json)

    req = KYCRequest(
        extracted_docs=extracted["documents"],
        ground_truth=GroundTruth(**normalized_gt),
        ground_truth_manifest=gt_payload,
        method=method,  # type: ignore[arg-type]
        scope=scope,  # type: ignore[arg-type]
        rubric=rubric_text,
        rubric_mode=rubric_mode,  # type: ignore[arg-type]
        rubrics_by_doc_type=rubrics_by_doc_type,
    )
    return evaluate_kyc(req)


@app.get("/api/reference/rules")
def rules_reference_download() -> FileResponse:
    return FileResponse(
        path=RULES_REFERENCE_MD,
        filename="kyc-rules-reference.md",
        media_type="text/markdown",
    )


@app.get("/api/reference/rubric/{doc_type}", response_model=None)
def rubric_reference_download(doc_type: str, format: str = Query("md")):
    canonical = normalize_doc_type(doc_type)
    try:
        yaml_text = load_builtin_rubric_yaml(canonical)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if format.lower() == "yaml":
        return PlainTextResponse(
            content=yaml_text,
            media_type="application/x-yaml",
            headers={"Content-Disposition": f'attachment; filename="{canonical}-rubric.yaml"'},
        )

    md = rubric_markdown_for_doc_type(canonical)
    return PlainTextResponse(
        content=md,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{canonical}-rubric.md"'},
    )


@app.get("/api/reference/rubrics/active")
def active_rubrics_info(doc_types: str = Query(..., description="Comma-separated doc types, e.g. passport,aadhaar")) -> Dict[str, Any]:
    types = [normalize_doc_type(t) for t in doc_types.split(",") if t.strip()]
    rubric_map = builtin_rubric_map_for_doc_types(types)
    return {
        "doc_types": types,
        "rubrics": {
            dt: {
                "name": (yaml.safe_load(text) or {}).get("name"),
                "check_count": len((yaml.safe_load(text) or {}).get("checks", [])),
                "download_md": f"/api/reference/rubric/{dt}?format=md",
                "download_yaml": f"/api/reference/rubric/{dt}?format=yaml",
            }
            for dt, text in rubric_map.items()
        },
    }


@app.get("/api/rubric/template")
def rubric_template() -> FileResponse:
    """Legacy alias — combined built-in rubric YAML."""
    return FileResponse(
        path=BUILTIN_RUBRICS_DIR / RUBRIC_FILES["combined"],
        filename="indian_kyc_combined_rubric.yaml",
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
            "POST /api/run-upload",
            "GET /api/reference/rules",
            "GET /api/reference/rubric/{doc_type}",
            "GET /api/reference/rubrics/active",
            "GET /api/rubric/template",
            "GET /api/ground-truth/template",
        ],
    }
