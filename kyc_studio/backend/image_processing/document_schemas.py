"""
Dynamic Document Schema Handler
Provides JSON schemas and GPT-4o Vision prompts for all document types
"""

from typing import Dict, Any, List
import json


class DocumentSchemaHandler:
    """Handles document schemas and validation dynamically"""
    
  # Active KYC document types supported by the application.
    DOCUMENT_KEYWORDS = {
        "passport": ["passport", "travel document", "nationality", "passport no"],
    "pan": ["pan", "permanent account number", "income tax department", "pan card"],
    "aadhaar": ["aadhaar", "uidai", "unique identification", "aadhaar number"],
    }

  # Legacy document families are intentionally kept as commented references only.
  # They can be restored later if the product scope expands beyond the three
  # supported Indian KYC document types.
  # LEGACY_DOCUMENT_KEYWORDS = {
  #     "driver_license": [...],
  #     "birth_certificate": [...],
  #     "green_card": [...],
  #     "ssn_card": [...],
  #     "bank_statement": [...],
  #     "w2": [...],
  #     "utility_bill": [...],
  #     "portrait_photo": [...],
  # }
    
    @staticmethod
    def detect_document_type(text: str) -> str:
        """Detect document type from OCR text"""
        text_lower = text.lower()
        
        # Check for specific keywords
        for doc_type, keywords in DocumentSchemaHandler.DOCUMENT_KEYWORDS.items():
            if any(keyword in text_lower for keyword in keywords):
                return doc_type
        
        return "unknown"
    
    @staticmethod
    def get_gpt4_vision_prompt(doc_type: str, ocr_text: str = "") -> str:
        """Generate GPT-4o Vision prompt for document extraction"""
        
        base_instruction = f"""You are a document processing expert. Extract information from this {doc_type.replace('_', ' ')} image.

OCR TEXT (may contain errors - verify with image):
{ocr_text if ocr_text else "No OCR text available"}

RULES:
1. Return ONLY valid JSON (no markdown, no explanations)
2. Use YYYY-MM-DD format for dates
3. If field not visible, use null
4. Be precise with names and numbers

"""
        
        # Schema definitions
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
  "date_of_issue": "YYYY-MM-DD",
  "date_of_expiration": "YYYY-MM-DD",
  "issuing_country": "string"
}''',
            
            "pan": '''
{
  "document_type": "pan",
  "pan_number": "string",
  "name": "string",
  "father_name": "string",
  "dob": "YYYY-MM-DD"
}''',

            "aadhaar": '''
{
  "document_type": "aadhaar",
  "aadhaar_number": "string",
  "name": "string",
  "dob": "YYYY-MM-DD",
  "gender": "string",
  "address": "string",
  "pincode": "string"
}''',

            # Legacy prompt schemas kept as comments only for future reuse.
            # "driver_license": '''...''',
            # "birth_certificate": '''...''',
            # "green_card": '''...''',
            # "ssn_card": '''...''',
            
            "unknown": '''
{
  "document_type": "unknown",
  "extracted_fields": {}
}'''
        }
        
        schema = schemas.get(doc_type, schemas["unknown"])
        
        return base_instruction + f"REQUIRED JSON SCHEMA:\n{schema}\n\nExtract now:"
    
    @staticmethod
    def validate_json(json_data: Dict[str, Any], doc_type: str) -> tuple[bool, List[str]]:
        """Validate extracted JSON"""
        errors = []
        
        if "document_type" not in json_data:
            errors.append("Missing document_type field")
        
        return len(errors) == 0, errors