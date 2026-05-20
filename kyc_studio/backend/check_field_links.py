from __future__ import annotations

from typing import Dict, List, Set

from manifest_field_matches import OPTIONAL_MANIFEST_FIELDS
from models import CheckResult, DocumentKYCResult, FieldMatch

# Which extracted/manifest field rows support each top-level rule check.
CHECK_FIELD_KEYS: Dict[str, Dict[str, Set[str]]] = {
    "Name Match": {
        "passport": {"given_names", "surname"},
        "aadhaar": {"name"},
        "pan": {"name"},
    },
    "DOB Match": {
        "passport": {"date_of_birth"},
        "aadhaar": {"dob"},
        "pan": {"dob"},
    },
    "Aadhaar Format": {"aadhaar": {"aadhaar_number"}},
    "PAN Format": {"pan": {"pan_number"}},
    "Passport Expiry": {"passport": {"date_of_expiration"}},
    "Gender Consistency": {
        "passport": {"sex"},
        "aadhaar": {"gender"},
        "pan": {"gender"},
    },
    "Address Present": {"aadhaar": {"address"}},
}


def _labeled_field_match(doc: DocumentKYCResult, fm: FieldMatch) -> FieldMatch:
    return FieldMatch(
        field=fm.field,
        extracted=fm.extracted,
        ground_truth=fm.ground_truth,
        status=fm.status,
        coverage_percent=fm.coverage_percent,
        doc_type=doc.doc_type,
        document_id=doc.document_id,
    )


def field_matches_for_check(check_name: str, per_doc_results: List[DocumentKYCResult]) -> List[FieldMatch]:
    """Return manifest field rows that inform a combined-scope check."""
    name = str(check_name or "").strip()

    if name == "Mandatory Fields":
        out: List[FieldMatch] = []
        for doc in per_doc_results:
            optional = OPTIONAL_MANIFEST_FIELDS.get(doc.doc_type, frozenset())
            for fm in doc.field_matches:
                if fm.field in optional:
                    continue
                out.append(_labeled_field_match(doc, fm))
        return out

    keys_by_type = CHECK_FIELD_KEYS.get(name)
    if not keys_by_type:
        return []

    out = []
    for doc in per_doc_results:
        allowed = keys_by_type.get(doc.doc_type)
        if not allowed:
            continue
        for fm in doc.field_matches:
            if fm.field in allowed:
                out.append(_labeled_field_match(doc, fm))
    return out


def checks_with_field_matches(
    checks: List[CheckResult],
    per_doc_results: List[DocumentKYCResult],
) -> List[CheckResult]:
    enriched: List[CheckResult] = []
    for check in checks:
        linked = field_matches_for_check(check.name, per_doc_results)
        enriched.append(
            CheckResult(
                name=check.name,
                passed=check.passed,
                score=check.score,
                detail=check.detail,
                weight=check.weight,
                field_matches=linked,
            )
        )
    return enriched
