from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.parametrize(
    ("declared", "detected", "expected_schema_type"),
    [
        ("aadhaar", "pan", "aadhaar"),
        ("pan", "aadhaar", "pan"),
        ("passport", "unknown", "passport"),
    ],
)
def test_process_single_image_uses_declared_doc_type(declared: str, detected: str, expected_schema_type: str) -> None:
    from image_processing.ocr_extraction_pipeline import OCRExtractionPipeline

    pipeline = OCRExtractionPipeline(api_key="test-key")
    pipeline.detector.detect = MagicMock(return_value=detected)
    pipeline.preprocessor.prepare_for_ocr = MagicMock(return_value=("pre", "orig"))
    pipeline.extractor.extract_hybrid = MagicMock(
        return_value={"document_type": expected_schema_type, "aadhaar_number": "276745824811"}
    )

    with patch("pytesseract.image_to_string", return_value="ocr text"):
        result = pipeline.process_single_image("sample.png", declared_doc_type=declared)

    pipeline.extractor.extract_hybrid.assert_called_once()
    assert pipeline.extractor.extract_hybrid.call_args.kwargs["doc_type"] == expected_schema_type
    assert result["_metadata"]["detected_type"] == detected
    assert result["_metadata"]["declared_type"] == declared


def test_field_matches_passport_given_name_from_manifest(manifest) -> None:
    from manifest_field_matches import field_matches_from_manifest

    doc = {
        "document_type": "passport",
        "passport_number": "I5108603",
        "given_names": "RAJESH",
        "surname": "SHARMA",
        "date_of_birth": "21/07/1987",
        "nationality": "INDIAN",
    }
    matches = {m.field: m for m in field_matches_from_manifest(doc, manifest)}
    assert matches["given_names"].ground_truth == "RAJESH"
    assert matches["given_names"].status == "match"
    assert matches["surname"].ground_truth == "SHARMA"
    assert matches["surname"].status == "match"


def test_field_matches_aadhaar_pincode_from_manifest(manifest) -> None:
    from manifest_field_matches import field_matches_from_manifest

    doc = {
        "document_type": "aadhaar",
        "aadhaar_number": "276745824811",
        "name": "RAJESH SHARMA",
        "dob": "21/07/1987",
        "gender": "MALE",
        "address": "42 Mahatma Gandhi Road, Andheri West, Mumbai",
        "pincode": "400058",
    }
    matches = {m.field: m for m in field_matches_from_manifest(doc, manifest)}
    assert matches["pincode"].ground_truth == "400058"
    assert matches["pincode"].status == "match"
