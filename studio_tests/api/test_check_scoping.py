from __future__ import annotations

from typing import Any, Dict

from conftest import STUDIO_TESTS, build_extracted_docs

FIXTURES = STUDIO_TESTS / "fixtures" / "rubrics"


def _rubric(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_pan_per_doc_rules_exclude_aadhaar_and_passport_checks(
    client,
    manifest: Dict[str, Any],
    doc_uploads: Dict[str, Dict[str, Any]],
) -> None:
    extracted_docs = build_extracted_docs(["pan"], doc_uploads)
    payload = {
        "extracted_docs": extracted_docs,
        "ground_truth": {"name": "RAJESH SHARMA"},
        "ground_truth_manifest": manifest,
        "method": "rules",
        "scope": "individual",
        "rubric_mode": "single",
        "rubrics_by_doc_type": {},
    }
    res = client.post("/api/evaluate", json=payload)
    assert res.status_code == 200
    pan = res.json()["result"]["per_document_results"][0]
    names = {c["name"] for c in pan["checks"]}
    assert "Aadhaar Format" not in names
    assert "Passport Expiry" not in names
    assert "PAN Format" in names
    assert pan["score"] >= 75.0


def test_all_three_docs_each_card_has_only_relevant_rule_checks(
    client,
    manifest: Dict[str, Any],
    doc_uploads: Dict[str, Dict[str, Any]],
) -> None:
    extracted_docs = build_extracted_docs(["passport", "aadhaar", "pan"], doc_uploads)
    payload = {
        "extracted_docs": extracted_docs,
        "ground_truth": {"name": "RAJESH SHARMA"},
        "ground_truth_manifest": manifest,
        "method": "rules",
        "scope": "individual",
        "rubric_mode": "single",
        "rubrics_by_doc_type": {},
    }
    res = client.post("/api/evaluate", json=payload)
    assert res.status_code == 200
    by_type = {d["doc_type"]: {c["name"] for c in d["checks"]} for d in res.json()["result"]["per_document_results"]}

    assert "PAN Format" not in by_type["passport"]
    assert "Aadhaar Format" not in by_type["passport"]
    assert "Passport Expiry" in by_type["passport"]

    assert "PAN Format" not in by_type["aadhaar"]
    assert "Passport Expiry" not in by_type["aadhaar"]
    assert "Aadhaar Format" in by_type["aadhaar"]

    assert "Aadhaar Format" not in by_type["pan"]
    assert "Passport Expiry" not in by_type["pan"]
    assert "PAN Format" in by_type["pan"]

    assert "Cross-Document Name Consistency" not in by_type["pan"]


def test_combined_rubric_llm_scoping_uses_mocked_checks(client, manifest: Dict[str, Any], doc_uploads: Dict[str, Dict[str, Any]], monkeypatch) -> None:
    """Per-doc LLM cards must not list passport/aadhaar rubric checks on a PAN-only evaluation."""
    from kyc_llm_agent import KycLLMAgent

    def fake_evaluate(self, docs, ground_truth, ground_truth_manifest, rubric_yaml, scope, doc_types_in_scope=None):
        from models import CheckResult, DocumentKYCResult, KYCResult
        import yaml

        rubric = yaml.safe_load(rubric_yaml) or {}
        check_ids = [c["id"] for c in rubric.get("checks", [])]
        check_results = [
            CheckResult(name=cid, passed=True, score=100.0, detail="ok", weight=0.1) for cid in check_ids
        ]
        multi_document = len(docs) > 1
        per_doc = []
        for d in docs:
            from check_scoping import checks_for_document_card

            doc_type = str(d.get("document_type") or "unknown")
            fms = self._field_matches_for_doc(d, ground_truth_manifest or ground_truth)
            doc_checks = checks_for_document_card(
                check_results, doc_type, fms, is_rubric=True, multi_document=multi_document
            )
            from check_scoping import score_from_checks

            score = score_from_checks(doc_checks)
            per_doc.append(
                DocumentKYCResult(
                    document_id="x",
                    doc_type=doc_type,
                    score=score,
                    passed=score >= 75,
                    checks=doc_checks,
                    field_matches=fms,
                )
            )
        check_results.append(
            CheckResult(name="mandatory_fields", passed=True, score=100.0, detail="ok", weight=1.0)
        )
        from check_scoping import score_from_checks

        return KYCResult(
            method="llm",
            scope=scope,
            overall_score=score_from_checks(check_results),
            passed=True,
            summary="mock",
            per_document_results=per_doc,
            checks=check_results,
        )

    monkeypatch.setattr(KycLLMAgent, "evaluate", fake_evaluate)

    extracted_docs = build_extracted_docs(["pan"], doc_uploads)
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
    assert res.status_code == 200
    names = {c["name"] for c in res.json()["result"]["per_document_results"][0]["checks"]}
    assert "passport_validity" not in names
    assert "aadhaar_validity" not in names
    assert "pan_validity" in names
