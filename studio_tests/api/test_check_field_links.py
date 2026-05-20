from __future__ import annotations

from typing import Any, Dict

from check_field_links import field_matches_for_check
from conftest import build_extracted_docs
from models import CheckResult, DocumentKYCResult, FieldMatch


def test_combined_scope_checks_include_field_matches(
    client,
    manifest: Dict[str, Any],
    doc_uploads: Dict[str, Dict[str, Any]],
) -> None:
    extracted_docs = build_extracted_docs(["pan", "aadhaar"], doc_uploads)
    payload = {
        "extracted_docs": extracted_docs,
        "ground_truth": {"name": "RAJESH SHARMA"},
        "ground_truth_manifest": manifest,
        "scope": "all",
    }
    res = client.post("/api/evaluate", json=payload)
    assert res.status_code == 200
    checks = res.json()["result"]["checks"]
    pan_format = next(c for c in checks if c["name"] == "PAN Format")
    assert pan_format["field_matches"]
    assert any(fm["field"] == "pan_number" for fm in pan_format["field_matches"])
    assert pan_format["field_matches"][0].get("doc_type") == "pan"


def test_field_matches_for_check_name_match() -> None:
    per_doc = [
        DocumentKYCResult(
            document_id="pan.jpg",
            doc_type="pan",
            score=90.0,
            passed=True,
            checks=[],
            field_matches=[
                FieldMatch(field="name", extracted="RAJESH", ground_truth="RAJESH SHARMA", status="match"),
            ],
        )
    ]
    rows = field_matches_for_check("Name Match", per_doc)
    assert len(rows) == 1
    assert rows[0].field == "name"
    assert rows[0].doc_type == "pan"
