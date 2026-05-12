"""
Document Type Detector
Auto-detects document type from image and OCR text
"""

import re
from typing import Optional


class DocumentTypeDetector:
    """Detect document type from OCR text and visual features"""
    
    # Keywords for each document type
    KEYWORDS = {
        "driver_license": [
            "driver license", "driver's license", "driving license",
            "dl ", "class c", "class a", "class b", "issued by dmv"
        ],
        "passport": [
            "passport", "travel document", "u.s. department of state",
            "passport no", "nationality", "place of birth"
        ],
        "passport_card": [
            "passport card", "travel document", "card no"
        ],
        "permanent_resident_card": [
            "permanent resident", "green card", "uscis",
            "resident since", "category", "card expires"
        ],
        "birth_certificate": [
            "birth certificate", "certificate of birth",
            "born on", "date of birth", "mother", "father"
        ],
        "social_security_card": [
            "social security", "social security number",
            "social security administration"
        ],
        "bank_statement": [
            "bank statement", "account summary", "checking account",
            "statement period", "balance"
        ],
        "w2": [
            "form w-2", "wage and tax statement", "employer's ein",
            "wages, tips", "federal income tax"
        ],
        "utility_bill": [
            "utility bill", "electric", "gas", "water",
            "account number", "service address"
        ]
    }
    
    def detect(self, ocr_text: str, image_filename: str = "") -> str:
        """
        Detect document type from OCR text
        
        Args:
            ocr_text: Raw OCR extracted text
            image_filename: Optional filename for hints
            
        Returns:
            Document type string
        """
        if not ocr_text:
            return "unknown"
        
        text_lower = ocr_text.lower()
        
        # Score each document type
        scores = {}
        for doc_type, keywords in self.KEYWORDS.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            scores[doc_type] = score
        
        # Get best match
        if max(scores.values()) > 0:
            detected_type = max(scores, key=scores.get)
            confidence = scores[detected_type]
            print(f"  🎯 Detected: {detected_type} (confidence: {confidence} keywords)")
            return detected_type
        
        # Fallback: check filename
        if image_filename:
            filename_lower = image_filename.lower()
            for doc_type in self.KEYWORDS.keys():
                if doc_type.replace("_", "") in filename_lower.replace("_", ""):
                    print(f"  🎯 Detected from filename: {doc_type}")
                    return doc_type
        
        print(f"  ⚠️  Could not detect document type")
        return "unknown"
    
    def get_confidence(self, ocr_text: str, doc_type: str) -> float:
        """Get confidence score for a specific document type"""
        text_lower = ocr_text.lower()
        keywords = self.KEYWORDS.get(doc_type, [])
        
        if not keywords:
            return 0.0
        
        matches = sum(1 for keyword in keywords if keyword in text_lower)
        confidence = matches / len(keywords)
        
        return confidence