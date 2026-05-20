from __future__ import annotations

import copy
from typing import Any, Dict

from conftest import build_extracted_docs


def test_name_and_dob_match_only_in_combined_scope(
    client,
    manifest: Dict[str, Any],
    doc_uploads: Dict[str, Dict[str, Any]],
) -> None:
    extracted_docs = build_extracted_docs(["pan"], doc_uploads)
    payload = {
        "extracted_docs": extracted_docs,
        "ground_truth": {"name": "RAJESH SHARMA", "dob": "21/07/1987"},
        "ground_truth_manifest": manifest,
        "scope": "individual",
    }
    res = client.post("/api/evaluate", json=payload)
    assert res.status_code == 200
    pan_checks = {c["name"] for c in res.json()["result"]["per_document_results"][0]["checks"]}
    assert "Name Match" not in pan_checks
    assert "DOB Match" not in pan_checks

    payload["scope"] = "all"
    res = client.post("/api/evaluate", json=payload)
    assert res.status_code == 200
    top_names = {c["name"] for c in res.json()["result"]["checks"]}
    assert "Name Match" in top_names
    assert "DOB Match" in top_names
    assert "Age Eligibility" not in top_names


def test_name_match_fails_when_one_document_missing_name(
    client,
    manifest: Dict[str, Any],
    doc_uploads: Dict[str, Dict[str, Any]],
) -> None:
    extracted_docs = build_extracted_docs(["passport", "pan"], doc_uploads)
    pan_wrap = copy.deepcopy(next(d for d in extracted_docs if d["doc_type"] == "pan"))
    pan_wrap["extracted"]["name"] = ""
    pan_wrap["extracted"]["dob"] = ""
    passport_wrap = next(d for d in extracted_docs if d["doc_type"] == "passport")
    extracted_docs = [passport_wrap, pan_wrap]

    payload = {
        "extracted_docs": extracted_docs,
        "ground_truth": {"name": "RAJESH SHARMA", "dob": "21/07/1987"},
        "ground_truth_manifest": manifest,
        "scope": "all",
    }
    res = client.post("/api/evaluate", json=payload)
    assert res.status_code == 200
    checks = {c["name"]: c for c in res.json()["result"]["checks"]}
    assert checks["Name Match"]["passed"] is False
    assert "not extracted" in checks["Name Match"]["detail"].lower()
    assert checks["DOB Match"]["passed"] is False


def test_name_match_passes_when_all_docs_extract_and_align(
    client,
    manifest: Dict[str, Any],
    doc_uploads: Dict[str, Dict[str, Any]],
) -> None:
    extracted_docs = build_extracted_docs(["passport", "aadhaar", "pan"], doc_uploads)
    payload = {
        "extracted_docs": extracted_docs,
        "ground_truth": {"name": "RAJESH SHARMA", "dob": "21/07/1987"},
        "ground_truth_manifest": manifest,
        "scope": "all",
    }
    res = client.post("/api/evaluate", json=payload)
    assert res.status_code == 200
    checks = {c["name"]: c for c in res.json()["result"]["checks"]}
    assert checks["Name Match"]["passed"] is True
    assert checks["DOB Match"]["passed"] is True
