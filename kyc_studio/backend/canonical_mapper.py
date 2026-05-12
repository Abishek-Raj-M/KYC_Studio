from __future__ import annotations

from typing import Any, Dict, Iterable, List


DOC_TYPE_ALIASES = {
    "passport": "passport",
    "indian_passport": "passport",
    "pan": "pan",
    "pan_card": "pan",
    "pancard": "pan",
    "aadhaar": "aadhaar",
    "aadhar": "aadhaar",
    "adhar": "aadhaar",
}


FIELD_ALIASES = {
    "name": ["name", "full_name", "applicant_name", "holder_name"],
    "dob": ["dob", "date_of_birth", "birth_date", "date of birth"],
    "gender": ["gender", "sex"],
    "address": ["address", "current_address", "residential_address"],
    "nationality": ["nationality", "citizenship"],
    "passport_number": ["passport_number", "passport_no", "passport"],
    "pan_number": ["pan_number", "pan", "pan_no", "pan_card_number"],
    "aadhaar_number": ["aadhaar_number", "aadhaar", "aadhar", "uid", "uidai_number"],
    "given_names": ["given_names", "given_name", "first_name"],
    "surname": ["surname", "last_name", "family_name"],
    "father_name": ["father_name", "fathers_name"],
    "mother_name": ["mother_name", "mothers_name"],
    "date_of_issue": ["date_of_issue", "issue_date", "issued_on"],
    "date_of_expiration": ["date_of_expiration", "date_of_expiry", "expiry_date", "expiration_date"],
    "place_of_birth": ["place_of_birth", "birth_place", "place_birth"],
    "place_of_issue": ["place_of_issue", "issued_at", "issue_place"],
    "pincode": ["pincode", "pin", "postal_code", "zip_code"],
}


def _normalize_key(value: str) -> str:
    return value.lower().strip().replace(" ", "_")


def _pick(data: Dict[str, Any], candidates: Iterable[str]) -> Any:
    if not data:
        return None
    normalized = {_normalize_key(k): v for k, v in data.items()}
    for candidate in candidates:
        key = _normalize_key(candidate)
        if key in normalized and normalized[key] not in [None, ""]:
            return normalized[key]
    return None


def normalize_document(raw_doc: Dict[str, Any], declared_doc_type: str | None = None) -> Dict[str, Any]:
    fields = raw_doc.get("fields") if isinstance(raw_doc.get("fields"), dict) else {}
    merged: Dict[str, Any] = {**fields, **raw_doc}

    raw_type = str(declared_doc_type or raw_doc.get("document_type") or raw_doc.get("doc_type") or "").lower().strip()
    canonical_doc_type = DOC_TYPE_ALIASES.get(raw_type, raw_type or "unknown")

    normalized: Dict[str, Any] = {
        "document_type": canonical_doc_type,
    }

    for target, aliases in FIELD_ALIASES.items():
        picked = _pick(merged, aliases)
        if picked is not None:
            normalized[target] = picked

    metadata = raw_doc.get("_metadata")
    if isinstance(metadata, dict):
        normalized["_metadata"] = metadata

    return normalized


def normalize_documents(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [normalize_document(item) for item in items]


def normalize_ground_truth(raw_gt: Dict[str, Any]) -> Dict[str, Any]:
    normalized: Dict[str, Any] = {}

    for target in ["name", "dob", "gender", "address", "nationality"]:
        value = _pick(raw_gt, FIELD_ALIASES.get(target, [target]))
        if value is not None:
            normalized[target] = value

    ids = raw_gt.get("id_numbers") if isinstance(raw_gt.get("id_numbers"), dict) else {}
    id_numbers = {
        "passport": _pick(ids, ["passport", "passport_number"]),
        "pan": _pick(ids, ["pan", "pan_number"]),
        "aadhaar": _pick(ids, ["aadhaar", "aadhar", "aadhaar_number"]),
    }
    normalized["id_numbers"] = {k: v for k, v in id_numbers.items() if v not in [None, ""]}

    return normalized
