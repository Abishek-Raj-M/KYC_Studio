from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Tuple

from models import FieldMatch

DOC_MANIFEST_KEYS = {
    "passport": "passport",
    "aadhaar": "aadhaar",
    "pan": "pan_card",
}

# Fields not scored for mandatory / completeness when absent or non-matching.
OPTIONAL_MANIFEST_FIELDS: Dict[str, frozenset[str]] = {
    "passport": frozenset(
        {
            "father_name",
            "mother_name",
            "place_of_issue",
            "signature_name",
            "place_of_birth",
            "date_of_issue",
            "date_of_expiration",
        }
    ),
    "aadhaar": frozenset({"city", "state"}),
    "pan": frozenset({"signature_name"}),
}

PASSPORT_FIELD_ROWS: List[Tuple[str, str]] = [
    ("passport_number", "passport_number"),
    ("given_names", "given_name"),
    ("surname", "surname"),
    ("date_of_birth", "date_of_birth"),
    ("nationality", "nationality"),
    ("sex", "sex"),
    ("place_of_birth", "place_of_birth"),
    ("father_name", "father_name"),
    ("mother_name", "mother_name"),
    ("date_of_issue", "date_of_issue"),
    ("date_of_expiration", "date_of_expiry"),
    ("place_of_issue", "place_of_issue"),
    ("signature_name", "signature_name"),
]

AADHAAR_FIELD_ROWS: List[Tuple[str, str]] = [
    ("aadhaar_number", "aadhaar"),
    ("name", "name"),
    ("dob", "dob"),
    ("gender", "gender"),
    ("address", "address"),
    ("pincode", "pincode"),
    ("city", "city"),
    ("state", "state"),
]

PAN_FIELD_ROWS: List[Tuple[str, str]] = [
    ("pan_number", "pan"),
    ("name", "name"),
    ("father_name", "father_name"),
    ("dob", "dob"),
    ("signature_name", "signature_name"),
]

FIELD_ROWS_BY_DOC: Dict[str, List[Tuple[str, str]]] = {
    "passport": PASSPORT_FIELD_ROWS,
    "aadhaar": AADHAAR_FIELD_ROWS,
    "pan": PAN_FIELD_ROWS,
}

ADDRESS_COVERAGE_MATCH_THRESHOLD = 85.0


def _norm(value: Any) -> str:
    return str(value or "").strip()


def _normalize_address(text: str) -> str:
    lowered = text.lower()
    lowered = re.sub(r"[^\w\s,]", " ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def _address_tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", _normalize_address(text)) if len(t) > 1}


def address_coverage_status(extracted: Any, expected: Any) -> Tuple[str, float | None]:
    extracted_text = _norm(extracted)
    expected_text = _norm(expected)
    if not expected_text:
        return "missing", None
    if not extracted_text:
        return "missing", None

    norm_ext = _normalize_address(extracted_text)
    norm_exp = _normalize_address(expected_text)
    if norm_exp in norm_ext:
        return "match", 100.0

    exp_tokens = _address_tokens(expected_text)
    if not exp_tokens:
        return "missing", None
    ext_tokens = _address_tokens(extracted_text)
    overlap = len(exp_tokens & ext_tokens) / len(exp_tokens)
    pct = round(overlap * 100, 1)
    if pct >= ADDRESS_COVERAGE_MATCH_THRESHOLD:
        return "match", pct
    if pct >= 50.0:
        return "partial", pct
    return "mismatch", pct


def normalize_gender(value: Any) -> str:
    token = _norm(value).upper()
    if token in {"M", "MALE", "MAN"}:
        return "M"
    if token in {"F", "FEMALE", "WOMAN"}:
        return "F"
    return token


def genders_compatible(left: Any, right: Any) -> bool:
    left_n = normalize_gender(left)
    right_n = normalize_gender(right)
    if not left_n or not right_n:
        return False
    return left_n == right_n


def _parse_date(date_str: str) -> datetime | None:
    if not date_str:
        return None
    for fmt in ["%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"]:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None


def dates_equal(left: str, right: str) -> bool:
    left_dt = _parse_date(left)
    right_dt = _parse_date(right)
    if left_dt and right_dt:
        return left_dt.date() == right_dt.date()
    return _norm(left).lower() == _norm(right).lower()


def _normalize_id(field: str, value: str) -> str:
    if field in {"aadhaar_number", "pan_number", "passport_number"}:
        return re.sub(r"\s+", "", value).upper()
    return value


def compare_field(field: str, extracted: Any, expected: Any) -> Tuple[str, float | None]:
    extracted_text = _norm(extracted)
    expected_text = _norm(expected)
    if not extracted_text:
        return "missing", None
    if not expected_text:
        return "missing", None
    if field == "address":
        return address_coverage_status(extracted, expected)
    if field in {"dob", "date_of_birth", "date_of_issue", "date_of_expiration", "issue_date"}:
        return ("match" if dates_equal(extracted_text, expected_text) else "mismatch"), None
    if field in {"aadhaar_number", "pan_number", "passport_number"}:
        status = (
            "match"
            if _normalize_id(field, extracted_text) == _normalize_id(field, expected_text)
            else "mismatch"
        )
        return status, None
    if field in {"gender", "sex"}:
        return ("match" if genders_compatible(extracted_text, expected_text) else "mismatch"), None
    if extracted_text.lower() == expected_text.lower():
        return "match", None
    return "mismatch", None


def manifest_doc_fields(manifest: Dict[str, Any], doc_type: str) -> Dict[str, Any]:
    documents = manifest.get("documents") if isinstance(manifest.get("documents"), dict) else {}
    manifest_key = DOC_MANIFEST_KEYS.get(doc_type, doc_type)
    doc_entry = documents.get(manifest_key) if isinstance(documents, dict) else {}
    if isinstance(doc_entry, dict) and isinstance(doc_entry.get("fields"), dict):
        return doc_entry["fields"]
    return {}


def field_matches_from_manifest(doc: Dict[str, Any], manifest: Dict[str, Any]) -> List[FieldMatch]:
    doc_type = str(doc.get("document_type") or "unknown").lower().strip()
    rows = FIELD_ROWS_BY_DOC.get(doc_type, [])
    if not rows:
        return []

    doc_fields = manifest_doc_fields(manifest, doc_type)
    person = manifest.get("person") if isinstance(manifest.get("person"), dict) else {}
    matches: List[FieldMatch] = []

    for extract_key, manifest_key in rows:
        extracted = doc.get(extract_key)
        if extract_key == "date_of_birth" and extracted is None:
            extracted = doc.get("dob")
        if extract_key == "dob" and extracted is None:
            extracted = doc.get("date_of_birth")
        if extract_key == "sex" and extracted is None:
            extracted = doc.get("gender")

        expected = doc_fields.get(manifest_key)
        if expected is None and manifest_key in {"name", "dob", "gender", "nationality"}:
            expected = person.get(manifest_key if manifest_key != "nationality" else "nationality")
        if expected is None and manifest_key == "name":
            expected = person.get("name")

        status, coverage = compare_field(extract_key, extracted, expected)
        matches.append(
            FieldMatch(
                field=extract_key,
                extracted=extracted,
                ground_truth=expected,
                status=status,  # type: ignore[arg-type]
                coverage_percent=coverage,
            )
        )

    return matches


def _counts_for_mandatory(status: str) -> bool:
    return status in {"match", "partial"}


def mandatory_field_failures(field_matches: List[FieldMatch], doc_type: str) -> List[str]:
    optional = OPTIONAL_MANIFEST_FIELDS.get(doc_type, frozenset())
    return [
        f"{doc_type}.{fm.field} ({fm.status})"
        for fm in field_matches
        if fm.field not in optional and not _counts_for_mandatory(fm.status)
    ]


def required_fields_completeness_score(field_matches: List[FieldMatch], doc_type: str) -> Tuple[float, bool, str]:
    optional = OPTIONAL_MANIFEST_FIELDS.get(doc_type, frozenset())
    scored = [fm for fm in field_matches if fm.field not in optional]
    if not scored:
        return 100.0, True, "No required manifest fields for scoring"

    matched = sum(1 for fm in scored if _counts_for_mandatory(fm.status))
    score = round((matched / len(scored)) * 100, 2)
    passed = score >= 75.0
    failures = [f"{fm.field} ({fm.status})" for fm in scored if not _counts_for_mandatory(fm.status)]
    detail = (
        "All required manifest fields present and matching"
        if passed
        else "Incomplete or mismatched required fields: " + ", ".join(failures)
    )
    return score, passed, detail
