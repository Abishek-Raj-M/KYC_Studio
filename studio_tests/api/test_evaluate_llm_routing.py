from __future__ import annotations

from typing import Any, Dict

import pytest

from conftest import STUDIO_TESTS, build_extracted_docs

FIXTURES = STUDIO_TESTS / "fixtures" / "rubrics"


def _rubric(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_llm_per_doc_missing_rubric_returns_400_no_dial_key_needed(
    client,
    manifest: Dict[str, Any],
    doc_uploads: Dict[str, Dict[str, Any]],
) -> None:
    """Validation runs before KycLLMAgent is constructed (no DIAL_API_KEY required)."""
    extracted_docs = build_extracted_docs(["pan", "aadhaar"], doc_uploads)
    payload = {
        "extracted_docs": extracted_docs,
        "ground_truth": {"name": "x"},
        "ground_truth_manifest": manifest,
        "method": "llm",
        "scope": "individual",
        "rubric_mode": "per_doc",
        "rubrics_by_doc_type": {"pan": _rubric("pan_rubric.yaml")},
    }
    res = client.post("/api/evaluate", json=payload)
    assert res.status_code == 400
    assert "Missing rubric" in res.json()["detail"]


@pytest.mark.integration
@pytest.mark.skipif(
    not __import__("os").environ.get("DIAL_API_KEY"),
    reason="DIAL_API_KEY not set — skip live LLM integration",
)
def test_llm_per_doc_happy_path(client, manifest: Dict[str, Any], doc_uploads: Dict[str, Dict[str, Any]]) -> None:
    extracted_docs = build_extracted_docs(["pan", "aadhaar"], doc_uploads)
    payload = {
        "extracted_docs": extracted_docs,
        "ground_truth": {"name": "RAJESH SHARMA"},
        "ground_truth_manifest": manifest,
        "method": "llm",
        "scope": "all",
        "rubric_mode": "per_doc",
        "rubrics_by_doc_type": {
            "pan": _rubric("pan_rubric.yaml"),
            "aadhaar": _rubric("aadhaar_rubric.yaml"),
        },
    }
    res = client.post("/api/evaluate", json=payload)
    assert res.status_code == 200, res.text
    result = res.json()["result"]
    assert result["method"] == "llm"
    assert result["scope"] == "all"
    assert len(result["per_document_results"]) == 2
    assert result["checks"]


@pytest.mark.integration
@pytest.mark.skipif(
    not __import__("os").environ.get("DIAL_API_KEY"),
    reason="DIAL_API_KEY not set — skip live LLM integration",
)
def test_llm_single_combined_rubric_multi_doc(client, manifest: Dict[str, Any], doc_uploads: Dict[str, Dict[str, Any]]) -> None:
    extracted_docs = build_extracted_docs(["pan", "aadhaar"], doc_uploads)
    payload = {
        "extracted_docs": extracted_docs,
        "ground_truth": {"name": "RAJESH SHARMA"},
        "ground_truth_manifest": manifest,
        "method": "llm",
        "scope": "individual",
        "rubric_mode": "single",
        "rubric": _rubric("indian_kyc_combined_rubric.yaml"),
    }
    res = client.post("/api/evaluate", json=payload)
    assert res.status_code == 200, res.text
    result = res.json()["result"]
    assert result["method"] == "llm"
    assert len(result["per_document_results"]) == 2
