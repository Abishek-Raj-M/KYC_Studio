from __future__ import annotations

from typing import Any, Dict

from conftest import build_extracted_docs


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
        "scope": "individual",
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
        "scope": "individual",
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
