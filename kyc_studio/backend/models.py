from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


MethodType = Literal["rules", "llm", "both"]
ScopeType = Literal["individual", "all"]
DocType = Literal["passport", "aadhaar", "pan"]


class DocumentUpload(BaseModel):
    doc_type: DocType
    side: Literal["front", "back"]
    filename: str
    extracted: Dict[str, Any]


class GroundTruth(BaseModel):
    name: Optional[str] = None
    dob: Optional[str] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    nationality: Optional[str] = None
    id_numbers: Dict[str, str] = Field(default_factory=dict)


class KYCRequest(BaseModel):
    extracted_docs: List[DocumentUpload]
    ground_truth: GroundTruth
    ground_truth_manifest: Optional[Dict[str, Any]] = None
    method: MethodType = "rules"
    scope: ScopeType = "individual"
    rubric: Optional[str] = None
    rubric_mode: Literal["single", "per_doc"] = "single"
    rubrics_by_doc_type: Dict[str, str] = Field(default_factory=dict)


class CheckResult(BaseModel):
    name: str
    passed: bool
    score: float
    detail: str
    weight: float = 1.0


class FieldMatch(BaseModel):
    field: str
    extracted: Any
    ground_truth: Any
    status: Literal["match", "mismatch", "missing"]


class DocumentKYCResult(BaseModel):
    document_id: str
    doc_type: str
    score: float
    passed: bool
    checks: List[CheckResult]
    field_matches: List[FieldMatch] = Field(default_factory=list)


class KYCResult(BaseModel):
    method: MethodType
    scope: ScopeType
    overall_score: float
    passed: bool
    summary: str
    per_document_results: List[DocumentKYCResult] = Field(default_factory=list)
    checks: List[CheckResult] = Field(default_factory=list)
