from __future__ import annotations

import itertools
from typing import Any, Dict, List

import pytest

from conftest import build_extracted_docs

DOC_KEYS = ("passport", "aadhaar", "pan")
SCOPES = ("individual", "all")
REMOVED_METHODS = ("llm", "both")


def subsets(keys: tuple[str, ...]) -> List[tuple[str, ...]]:
    out: List[tuple[str, ...]] = []
    for r in range(1, len(keys) + 1):
        for combo in itertools.combinations(keys, r):
            out.append(combo)
    return out


@pytest.mark.parametrize("selected", subsets(DOC_KEYS))
@pytest.mark.parametrize("scope", SCOPES)
def test_rules_evaluate_matrix(
    client,
    manifest: Dict[str, Any],
    doc_uploads: Dict[str, Dict[str, Any]],
    selected: tuple[str, ...],
    scope: str,
) -> None:
    extracted_docs = build_extracted_docs(list(selected), doc_uploads)
    flat_gt = manifest.get("person") or {}
    payload = {
        "extracted_docs": extracted_docs,
        "ground_truth": {
            "name": flat_gt.get("name"),
            "dob": flat_gt.get("dob"),
            "gender": flat_gt.get("gender"),
            "nationality": flat_gt.get("nationality"),
            "address": (manifest.get("documents") or {}).get("aadhaar", {}).get("fields", {}).get("address"),
            "id_numbers": {},
        },
        "ground_truth_manifest": manifest,
        "scope": scope,
    }
    res = client.post("/api/evaluate", json=payload)
    assert res.status_code == 200, res.text
    body = res.json()
    result = body["result"]
    assert result["method"] == "rules"
    assert result["scope"] == scope
    assert result["passed"] is True
    assert result["overall_score"] >= 75.0
    mandatory = next((c for c in result["checks"] if c["name"] == "Mandatory Fields"), None)
    assert mandatory is not None
    assert mandatory["passed"] is True
    assert len(result["per_document_results"]) == len(selected)


@pytest.mark.parametrize("method", REMOVED_METHODS)
def test_removed_evaluation_methods_return_400(
    client,
    manifest: Dict[str, Any],
    doc_uploads: Dict[str, Dict[str, Any]],
    method: str,
) -> None:
    extracted_docs = build_extracted_docs(["pan"], doc_uploads)
    payload = {
        "extracted_docs": extracted_docs,
        "ground_truth": {"name": "RAJESH SHARMA"},
        "ground_truth_manifest": manifest,
        "method": method,
        "scope": "individual",
    }
    res = client.post("/api/evaluate", json=payload)
    assert res.status_code in (400, 422)


def test_rules_manifest_id_numbers_alignment(
    client,
    manifest: Dict[str, Any],
    doc_uploads: Dict[str, Dict[str, Any]],
) -> None:
    """Field matches for PAN/Aadhaar/Passport IDs align with manifest-derived id_numbers."""
    extracted_docs = build_extracted_docs(["pan", "aadhaar", "passport"], doc_uploads)
    payload = {
        "extracted_docs": extracted_docs,
        "ground_truth": {"name": "RAJESH SHARMA"},
        "ground_truth_manifest": manifest,
        "scope": "individual",
    }
    res = client.post("/api/evaluate", json=payload)
    assert res.status_code == 200
    per = res.json()["result"]["per_document_results"]
    by_type = {d["doc_type"]: d for d in per}
    pan_fm = {fm["field"]: fm["status"] for fm in by_type["pan"]["field_matches"]}
    assert pan_fm.get("pan_number") == "match"
    aad_fm = {fm["field"]: fm["status"] for fm in by_type["aadhaar"]["field_matches"]}
    assert aad_fm.get("aadhaar_number") == "match"
    pass_fm = {fm["field"]: fm["status"] for fm in by_type["passport"]["field_matches"]}
    assert pass_fm.get("passport_number") == "match"


def test_reference_rules_endpoint(client) -> None:
    res = client.get("/api/reference/rules")
    assert res.status_code == 200
    assert "Name Match" in res.text
