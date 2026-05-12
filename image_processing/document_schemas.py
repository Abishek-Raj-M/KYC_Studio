"""
Dynamic Document Schema Handler
Provides JSON schemas and GPT-4o Vision prompts for all document types
"""

from typing import Dict, Any, List
import json


class DocumentSchemaHandler:
    """Handles document schemas and validation dynamically"""
    
    # Document type keywords for detection
    DOCUMENT_KEYWORDS = {
        "passport": ["passport", "travel document", "nationality", "passport no"],
        "driver_license": ["driver license", "driver's license", "dl no", "license no"],
        "birth_certificate": ["birth certificate", "certificate of birth", "born on"],
        "green_card": ["permanent resident", "uscis", "green card", "resident card"],
        "ssn_card": ["social security", "ssn", "social security number"],
        "bank_statement": ["bank statement", "account number", "statement period"],
        "w2": ["form w-2", "wage and tax", "employer's ein"],
        "utility_bill": ["utility", "electric", "gas", "water", "bill date"],
        "portrait_photo": ["photo", "portrait", "photograph"]
    }
    
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
            
            "driver_license": '''
{
  "document_type": "driver_license",
  "name": {"first_name": "string", "last_name": "string"},
  "license_number": "string",
  "date_of_birth": "YYYY-MM-DD",
  "sex": "M/F",
  "height": "string",
  "weight_lb": "integer or null",
  "hair_color": "string",
  "eye_color": "string",
  "address": {
    "street": "string",
    "city": "string",
    "state": "string",
    "postal_code": "string"
  },
  "issue_date": "YYYY-MM-DD",
  "expiration_date": "YYYY-MM-DD",
  "issuing_jurisdiction": "string"
}''',
            
            "birth_certificate": '''
{
  "document_type": "birth_certificate",
  "subject": {"full_name": "string"},
  "birth": {"date": "YYYY-MM-DD", "place": "string"},
  "parents": {"mother_name": "string", "father_name": "string"},
  "issuer": {"name": "string"}
}''',
            
            "green_card": '''
{
  "document_type": "permanent_resident_card",
  "given_name": "string",
  "surname": "string",
  "uscis_number": "string",
  "date_of_birth": "YYYY-MM-DD",
  "country_of_birth": "string",
  "sex": "M/F",
  "resident_since": "YYYY-MM-DD",
  "card_expires": "YYYY-MM-DD",
  "category": "string",
  "issuing_country": "string"
}''',
            
            "ssn_card": '''
{
  "document_type": "social_security_card",
  "name": {"full_name": "string"},
  "ssn": "XXX-XX-XXXX",
  "issuing_agency": "Social Security Administration (USA)"
}''',
            
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