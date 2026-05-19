from __future__ import annotations

from document_schemas import DocumentSchemaHandler


class ExtendedDocumentSchemaHandler(DocumentSchemaHandler):
    """Extends the base schema handler with Aadhaar and PAN document support."""

    DOCUMENT_KEYWORDS = {
        **DocumentSchemaHandler.DOCUMENT_KEYWORDS,
        "aadhaar": ["aadhaar", "uidai", "unique identification", "aadhaar number"],
        "pan": ["pan", "permanent account number", "income tax department"],
    }

    @staticmethod
    def get_gpt4_vision_prompt(doc_type: str, ocr_text: str = "") -> str:
        base_instruction = f"""You are a document processing expert. Extract information from this {doc_type.replace('_', ' ')} image.

OCR TEXT (may contain errors - verify with image):
{ocr_text if ocr_text else "No OCR text available"}

RULES:
1. Return ONLY valid JSON (no markdown, no explanations)
2. Use YYYY-MM-DD format for dates
3. If field not visible, use null
4. Be precise with names and numbers

"""

        schemas = {
            "passport": '''
{
  "document_type": "passport",
  "passport_number": "string",
  "surname": "string",
  "given_names": "string",
  "nationality": "string",
  "date_of_birth": "YYYY-MM-DD",
  "sex": "M/F",
  "place_of_birth": "string",
  "father_name": "string",
  "mother_name": "string",
  "date_of_issue": "YYYY-MM-DD",
  "date_of_expiration": "YYYY-MM-DD",
  "place_of_issue": "string",
  "signature_name": "string",
  "issuing_country": "string"
}''',
            "aadhaar": '''
{
  "document_type": "aadhaar",
  "aadhaar_number": "string",
  "name": "string",
  "dob": "YYYY-MM-DD",
  "gender": "string",
  "address": "string",
  "pincode": "string",
  "city": "string",
  "state": "string"
}''',
            "pan": '''
{
  "document_type": "pan",
  "pan_number": "string",
  "name": "string",
  "father_name": "string",
  "dob": "YYYY-MM-DD",
  "signature_name": "string"
}''',
            "unknown": '''
{
  "document_type": "unknown",
  "extracted_fields": {}
}''',
        }

        schema = schemas.get(doc_type, schemas["unknown"])
        return base_instruction + f"REQUIRED JSON SCHEMA:\n{schema}\n\nExtract now:"
