from __future__ import annotations

from manifest_field_matches import address_coverage_status, field_matches_from_manifest


def test_address_superset_of_ground_truth_is_match(manifest) -> None:
    doc = {
        "document_type": "aadhaar",
        "address": "42 Mahatma Gandhi Road, Andheri West, Mumbai, Maharashtra",
    }
    gt_address = manifest["documents"]["aadhaar"]["fields"]["address"]
    status, coverage = address_coverage_status(doc["address"], gt_address)
    assert status == "match"
    assert coverage is not None
    assert coverage >= 85.0

    matches = {m.field: m for m in field_matches_from_manifest({**doc, "aadhaar_number": "1", "name": "x", "dob": "1", "gender": "M", "pincode": "1"}, manifest)}
    assert matches["address"].status == "match"


def test_aadhaar_format_accepts_spaced_number() -> None:
    from kyc_rules import _normalize_aadhaar_number, AADHAAR_REGEX

    normalized = _normalize_aadhaar_number("2767 4582 4811")
    assert normalized == "276745824811"
    assert AADHAAR_REGEX.match(normalized)


def test_gender_m_vs_male_is_match(manifest) -> None:
    doc = {"document_type": "passport", "sex": "M"}
    passport_fields = manifest["documents"]["passport"]["fields"]
    from manifest_field_matches import compare_field

    status, _ = compare_field("sex", "M", passport_fields["sex"])
    assert status == "match"
