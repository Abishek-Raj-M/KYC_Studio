"""
OCR Context Builder
Properly formats OCR extracted data into readable context for LLM
"""

import json
from typing import Dict, List
from datetime import datetime


class OCRContextBuilder:
    """Build formatted context from OCR extracted documents"""
    
    def __init__(self, ocr_data_path: str = None):
        """
        Initialize context builder
        
        Args:
            ocr_data_path: Optional path to OCR data file
        """
        self.ocr_data_path = ocr_data_path
        self.ocr_documents = []
        
        if ocr_data_path:
            self._load_ocr_data()
    
    def _load_ocr_data(self):
        """Load OCR data from file"""
        with open(self.ocr_data_path, 'r', encoding='utf-8') as f:
            self.ocr_documents = json.load(f)
    
    def build_person_profile_context(self, ocr_doc: Dict) -> str:
        """
        Build a readable context string from OCR document
        
        Args:
            ocr_doc: OCR extracted document dictionary
            
        Returns:
            Formatted context string
        """
        doc_type = ocr_doc.get('document_type', 'unknown')
        
        # Route to appropriate formatter based on document type
        if doc_type == 'driver_license':
            return self._format_driver_license(ocr_doc)
        elif doc_type == 'passport':
            return self._format_passport(ocr_doc)
        elif doc_type == 'passport_card':
            return self._format_passport_card(ocr_doc)
        elif doc_type in ['permanent_resident_card', 'Permanent Resident Card']:
            return self._format_permanent_resident_card(ocr_doc)
        elif doc_type == 'social_security_card':
            return self._format_social_security_card(ocr_doc)
        else:
            # Generic formatter for unknown types
            return self._format_generic(ocr_doc)
    
    def _format_driver_license(self, doc: Dict) -> str:
        """Format driver license data"""
        lines = ["=== DRIVER LICENSE ===\n"]
        
        # Name
        name = doc.get('name', {})
        if isinstance(name, dict):
            first = name.get('first_name', '')
            last = name.get('last_name', '')
            middle = name.get('middle_name', '')
            full_name = f"{first} {middle} {last}".strip()
            lines.append(f"Full Name: {full_name}")
        
        # License details
        if 'license_number' in doc:
            lines.append(f"License Number: {doc['license_number']}")
        
        if 'date_of_birth' in doc:
            lines.append(f"Date of Birth: {doc['date_of_birth']}")
        
        if 'sex' in doc:
            lines.append(f"Sex: {doc['sex']}")
        
        if 'height' in doc:
            lines.append(f"Height: {doc['height']}")
        
        if 'weight_lb' in doc:
            lines.append(f"Weight: {doc['weight_lb']} lbs")
        
        if 'hair_color' in doc:
            lines.append(f"Hair Color: {doc['hair_color']}")
        
        if 'eye_color' in doc:
            lines.append(f"Eye Color: {doc['eye_color']}")
        
        # Address
        address = doc.get('address', {})
        if isinstance(address, dict):
            street = address.get('street', '')
            city = address.get('city', '')
            state = address.get('state', '')
            postal = address.get('postal_code', '')
            
            if any([street, city, state, postal]):
                addr_str = f"{street}, {city}, {state} {postal}".strip(', ')
                lines.append(f"Address: {addr_str}")
        
        # Dates
        if 'issue_date' in doc:
            lines.append(f"Issue Date: {doc['issue_date']}")
        
        if 'expiration_date' in doc:
            lines.append(f"Expiration Date: {doc['expiration_date']}")
        
        # Jurisdiction
        if 'issuing_jurisdiction' in doc:
            lines.append(f"Issuing Jurisdiction: {doc['issuing_jurisdiction']}")
        
        return "\n".join(lines)
    
    def _format_passport(self, doc: Dict) -> str:
        """Format passport data"""
        lines = ["=== PASSPORT ===\n"]
        
        # Name
        if 'surname' in doc:
            lines.append(f"Surname: {doc['surname']}")
        if 'given_names' in doc:
            lines.append(f"Given Names: {doc['given_names']}")
        
        # Passport details
        if 'passport_number' in doc:
            lines.append(f"Passport Number: {doc['passport_number']}")
        
        if 'date_of_birth' in doc:
            lines.append(f"Date of Birth: {doc['date_of_birth']}")
        
        if 'sex' in doc:
            lines.append(f"Sex: {doc['sex']}")
        
        if 'nationality' in doc:
            lines.append(f"Nationality: {doc['nationality']}")
        
        if 'country_of_birth' in doc:
            lines.append(f"Country of Birth: {doc['country_of_birth']}")
        
        if 'place_of_birth' in doc:
            lines.append(f"Place of Birth: {doc['place_of_birth']}")
        
        # Dates
        if 'issue_date' in doc:
            lines.append(f"Issue Date: {doc['issue_date']}")
        
        if 'expiration_date' in doc:
            lines.append(f"Expiration Date: {doc['expiration_date']}")
        
        # Issuing authority
        if 'issuing_authority' in doc:
            lines.append(f"Issuing Authority: {doc['issuing_authority']}")
        
        return "\n".join(lines)
    
    def _format_passport_card(self, doc: Dict) -> str:
        """Format passport card data"""
        lines = ["=== PASSPORT CARD ===\n"]
        
        # Name
        if 'surname' in doc:
            lines.append(f"Surname: {doc['surname']}")
        if 'given_names' in doc:
            lines.append(f"Given Names: {doc['given_names']}")
        
        # Card details
        if 'card_number' in doc:
            lines.append(f"Card Number: {doc['card_number']}")
        
        if 'date_of_birth' in doc:
            lines.append(f"Date of Birth: {doc['date_of_birth']}")
        
        if 'sex' in doc:
            lines.append(f"Sex: {doc['sex']}")
        
        if 'nationality' in doc:
            lines.append(f"Nationality: {doc['nationality']}")
        
        # Dates
        if 'issue_date' in doc:
            lines.append(f"Issue Date: {doc['issue_date']}")
        
        if 'expiration_date' in doc:
            lines.append(f"Expiration Date: {doc['expiration_date']}")
        
        return "\n".join(lines)
    
    def _format_permanent_resident_card(self, doc: Dict) -> str:
        """Format permanent resident card data"""
        lines = ["=== PERMANENT RESIDENT CARD ===\n"]
        
        # Name
        if 'surname' in doc:
            lines.append(f"Surname: {doc['surname']}")
        if 'given_name' in doc:
            lines.append(f"Given Name: {doc['given_name']}")
        
        # Card details
        if 'card_number' in doc:
            lines.append(f"Card Number: {doc['card_number']}")
        
        if 'uscis_number' in doc:
            lines.append(f"USCIS Number: {doc['uscis_number']}")
        
        if 'date_of_birth' in doc:
            lines.append(f"Date of Birth: {doc['date_of_birth']}")
        
        if 'sex' in doc:
            lines.append(f"Sex: {doc['sex']}")
        
        if 'country_of_birth' in doc:
            lines.append(f"Country of Birth: {doc['country_of_birth']}")
        
        # Dates
        if 'resident_since' in doc:
            lines.append(f"Resident Since: {doc['resident_since']}")
        
        if 'card_expires' in doc:
            lines.append(f"Card Expires: {doc['card_expires']}")
        
        # Category
        if 'category' in doc:
            lines.append(f"Category: {doc['category']}")
        
        return "\n".join(lines)
    
    def _format_social_security_card(self, doc: Dict) -> str:
        """Format social security card data"""
        lines = ["=== SOCIAL SECURITY CARD ===\n"]
        
        # Name
        name = doc.get('name', {})
        if isinstance(name, dict):
            full_name = name.get('full_name', '')
            lines.append(f"Full Name: {full_name}")
        
        # SSN
        if 'social_security_number' in doc:
            lines.append(f"Social Security Number: {doc['social_security_number']}")
        
        return "\n".join(lines)
    
    def _format_generic(self, doc: Dict) -> str:
        """Generic formatter for unknown document types"""
        lines = [f"=== {doc.get('document_type', 'UNKNOWN').upper()} ===\n"]
        
        # Skip metadata
        skip_keys = {'_metadata', 'document_type'}
        
        def format_value(val, indent=0):
            """Recursively format values"""
            prefix = "  " * indent
            
            if isinstance(val, dict):
                result = []
                for k, v in val.items():
                    if k in skip_keys:
                        continue
                    formatted = format_value(v, indent + 1)
                    result.append(f"{prefix}{k}: {formatted}")
                return "\n".join(result)
            elif isinstance(val, list):
                return ", ".join(str(v) for v in val)
            else:
                return str(val)
        
        for key, value in doc.items():
            if key in skip_keys:
                continue
            
            formatted = format_value(value)
            lines.append(formatted)
        
        return "\n".join(lines)
    
    def build_contexts_for_questions(self, questions: List[Dict]) -> Dict[str, str]:
        """
        Build contexts for a list of questions
        
        Args:
            questions: List of question dictionaries
            
        Returns:
            Dictionary mapping question to context
        """
        contexts = {}
        
        for q in questions:
            person_name = q.get('person_name')
            doc_type = q.get('document_type')
            
            # Find matching document
            matching_doc = self._find_matching_document(person_name, doc_type)
            
            if matching_doc:
                context = self.build_person_profile_context(matching_doc)
                contexts[q['question']] = context
            else:
                contexts[q['question']] = "No matching document found"
        
        return contexts
    
    def _find_matching_document(self, person_name: str, doc_type: str) -> Dict:
        """Find document matching person and type"""
        search_name = person_name.lower().strip()
        
        for doc in self.ocr_documents:
            # Check document type
            if doc.get('document_type') != doc_type:
                continue
            
            # Extract name from document
            doc_name = self._extract_name(doc).lower()
            
            # Match
            if search_name in doc_name or doc_name in search_name:
                return doc
        
        return None
    
    def _extract_name(self, doc: Dict) -> str:
        """Extract name from any document type"""
        doc_type = doc.get('document_type', '')
        
        # Driver license
        if doc_type == 'driver_license':
            name_obj = doc.get('name', {})
            if isinstance(name_obj, dict):
                first = name_obj.get('first_name', '')
                last = name_obj.get('last_name', '')
                return f"{first} {last}".strip()
        
        # Passport/passport card
        elif doc_type in ['passport', 'passport_card']:
            given = doc.get('given_names', '')
            surname = doc.get('surname', '')
            return f"{given} {surname}".strip()
        
        # Permanent resident card
        elif doc_type in ['permanent_resident_card', 'Permanent Resident Card']:
            given = doc.get('given_name', '')
            surname = doc.get('surname', '')
            return f"{given} {surname}".strip()
        
        # Social security card
        elif doc_type == 'social_security_card':
            name_obj = doc.get('name', {})
            if isinstance(name_obj, dict):
                return name_obj.get('full_name', '')
        
        return ""


# Test the formatter
if __name__ == "__main__":
    # Test with your driver license data
    test_doc = {
        "document_type": "driver_license",
        "name": {
            "first_name": "SIMRAN",
            "last_name": "PATEL"
        },
        "license_number": "1234568",
        "date_of_birth": "1971-04-04",
        "sex": "F",
        "height": "5'-05\"",
        "weight_lb": 125,
        "hair_color": "BRN",
        "eye_color": "BRN",
        "address": {
            "street": "2570 24TH STREET",
            "city": "ANYTOWN",
            "state": "CA",
            "postal_code": "95818"
        },
        "issue_date": "2022-08-14",
        "expiration_date": "2032-08-14",
        "issuing_jurisdiction": "California"
    }
    
    builder = OCRContextBuilder()
    context = builder.build_person_profile_context(test_doc)
    
    print("FORMATTED CONTEXT:")
    print("=" * 70)
    print(context)
    print("=" * 70)