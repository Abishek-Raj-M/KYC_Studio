from __future__ import annotations

from typing import Iterable, List

from manifest_field_matches import mandatory_field_failures, required_fields_completeness_score
from models import CheckResult, FieldMatch


# Rule names that apply only at the combined evaluation level (not on per-doc cards).
RULE_CHECKS_COMBINED_ONLY = frozenset({"Name Match", "DOB Match"})

# Rule name -> document types; None means all uploaded types / global.
RULE_CHECK_DOC_TYPES: dict[str, frozenset[str] | None] = {
    "Name Match": frozenset(),  # combined-only via RULE_CHECKS_COMBINED_ONLY
    "DOB Match": frozenset(),  # combined-only via RULE_CHECKS_COMBINED_ONLY
    "Aadhaar Format": frozenset({"aadhaar"}),
    "PAN Format": frozenset({"pan"}),
    "Passport Expiry": frozenset({"passport"}),
    "Gender Consistency": None,
    "Mandatory Fields": None,  # recomputed per document
    "Address Present": frozenset({"aadhaar"}),
}


def normalize_doc_type(doc_type: str) -> str:
    aliases = {"pan_card": "pan", "pancard": "pan", "aadhar": "aadhaar"}
    key = str(doc_type or "unknown").lower().strip()
    return aliases.get(key, key)


def rule_check_applies_to_doc(check_name: str, doc_type: str, *, multi_document: bool) -> bool:
    """Whether a rule check should appear on a per-document result card."""
    name = str(check_name or "").strip()
    dtype = normalize_doc_type(doc_type)

    if name in RULE_CHECKS_COMBINED_ONLY:
        return False

    scope = RULE_CHECK_DOC_TYPES.get(name)
    if scope is None:
        return True
    if not scope:
        return False
    return dtype in scope


def filter_checks_for_doc(
    checks: Iterable[CheckResult],
    doc_type: str,
    *,
    multi_document: bool = True,
) -> List[CheckResult]:
    out: List[CheckResult] = []
    for check in checks:
        if rule_check_applies_to_doc(check.name, doc_type, multi_document=multi_document):
            out.append(check)
    return out


def mandatory_fields_check_rules(field_matches: List[FieldMatch], doc_type: str) -> CheckResult:
    failures = mandatory_field_failures(field_matches, normalize_doc_type(doc_type))
    passed = not failures
    return CheckResult(
        name="Mandatory Fields",
        passed=passed,
        score=100.0 if passed else 0.0,
        detail="All mandatory fields matched" if passed else "Missing or mismatched mandatory fields: " + ", ".join(failures),
        weight=1.0,
    )


def score_from_checks(checks: List[CheckResult]) -> float:
    if not checks:
        return 0.0
    total_weight = sum(c.weight for c in checks) or 1.0
    passed_weight = sum(c.weight for c in checks if c.passed)
    return round((passed_weight / total_weight) * 100, 2)


def _patch_gender_consistency(check: CheckResult, field_matches: List[FieldMatch], doc_type: str) -> CheckResult:
    dtype = normalize_doc_type(doc_type)

    if dtype == "pan":
        gender_row = next((fm for fm in field_matches if fm.field == "gender"), None)
        if gender_row is None:
            return CheckResult(
                name=check.name,
                passed=True,
                score=100.0,
                detail="Gender not printed on PAN; check not applicable",
                weight=check.weight,
            )

    if dtype == "aadhaar":
        gender_row = next((fm for fm in field_matches if fm.field == "gender"), None)
        if gender_row:
            if gender_row.status in {"match", "partial"}:
                return CheckResult(
                    name=check.name,
                    passed=True,
                    score=100.0,
                    detail="Aadhaar gender matches manifest",
                    weight=check.weight,
                )
            if gender_row.status == "missing":
                return CheckResult(
                    name=check.name,
                    passed=False,
                    score=0.0,
                    detail="Gender missing on this Aadhaar document",
                    weight=check.weight,
                )

    if dtype == "passport":
        sex_row = next((fm for fm in field_matches if fm.field == "sex"), None)
        if sex_row and sex_row.status in {"match", "partial"}:
            return CheckResult(
                name=check.name,
                passed=True,
                score=100.0,
                detail="Passport sex matches manifest",
                weight=check.weight,
            )

    return check


def checks_for_document_card(
    checks: List[CheckResult],
    doc_type: str,
    field_matches: List[FieldMatch],
    *,
    multi_document: bool,
) -> List[CheckResult]:
    """Filter checks for one document card and replace mandatory_fields with doc-local version."""
    filtered = filter_checks_for_doc(checks, doc_type, multi_document=multi_document)
    result: List[CheckResult] = []
    for check in filtered:
        if check.name == "Mandatory Fields":
            continue
        patched = check
        if check.name == "Gender Consistency":
            patched = _patch_gender_consistency(check, field_matches, doc_type)
        result.append(patched)
    result.append(mandatory_fields_check_rules(field_matches, doc_type))
    return result
