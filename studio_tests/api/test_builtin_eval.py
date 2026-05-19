from __future__ import annotations

import pytest

from builtin_eval import builtin_rubric_map_for_doc_types, load_builtin_rubric_yaml, rubric_markdown_for_doc_type


def test_builtin_rubric_map_single_doc() -> None:
    rubrics = builtin_rubric_map_for_doc_types(["passport"])
    assert "passport" in rubrics
    assert "passport_name_match" in rubrics["passport"]


def test_builtin_rubric_map_multi_doc() -> None:
    rubrics = builtin_rubric_map_for_doc_types(["pan", "aadhaar", "passport"])
    assert set(rubrics.keys()) == {"pan", "aadhaar", "passport"}


def test_rubric_markdown_export() -> None:
    md = rubric_markdown_for_doc_type("aadhaar")
    assert "#" in md
    assert "aadhaar_number_format" in md


def test_evaluate_llm_uses_builtin_without_upload(client, manifest, doc_uploads, monkeypatch) -> None:
    from kyc_llm_agent import KycLLMAgent
    from models import CheckResult, DocumentKYCResult, KYCResult

    captured: list[str] = []

    def fake_evaluate(self, docs, ground_truth, ground_truth_manifest, rubric_yaml, scope, doc_types_in_scope=None):
        captured.append(rubric_yaml)
        return KYCResult(
            method="llm",
            scope=scope,
            overall_score=100.0,
            passed=True,
            summary="mock",
            per_document_results=[
                DocumentKYCResult(
                    document_id="x",
                    doc_type=str(docs[0].get("document_type")),
                    score=100.0,
                    passed=True,
                    checks=[CheckResult(name="pan_format", passed=True, score=100.0, detail="ok", weight=1.0)],
                    field_matches=[],
                )
            ],
            checks=[],
        )

    monkeypatch.setattr(KycLLMAgent, "evaluate", fake_evaluate)

    extracted_docs = [doc_uploads["pan"]]
    payload = {
        "extracted_docs": extracted_docs,
        "ground_truth": {"name": "RAJESH SHARMA"},
        "ground_truth_manifest": manifest,
        "method": "llm",
        "scope": "individual",
    }
    res = client.post("/api/evaluate", json=payload)
    assert res.status_code == 200, res.text
    assert captured
    assert "pan_format" in captured[0]


def test_reference_rules_endpoint(client) -> None:
    res = client.get("/api/reference/rules")
    assert res.status_code == 200
    assert "Name Match" in res.text


def test_reference_rubric_md_endpoint(client) -> None:
    res = client.get("/api/reference/rubric/pan?format=md")
    assert res.status_code == 200
    assert "pan_format" in res.text
