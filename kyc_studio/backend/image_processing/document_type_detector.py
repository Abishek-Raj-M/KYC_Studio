"""
Document Type Detector
Auto-detects document type from image and OCR text
"""

import re
from typing import Optional


class DocumentTypeDetector:
    """Detect document type from OCR text and visual features"""
    
    # Active KYC document types supported by KYC Studio.
    KEYWORDS = {
        "passport": [
            "passport", "travel document", "u.s. department of state",
            "passport no", "nationality", "place of birth"
        ],
        "pan": [
            "pan card", "permanent account number", "income tax department",
            "pan number", "income tax", "government of india", "pancard"
        ],
        "aadhaar": [
            "aadhaar", "uidai", "unique identification", "aadhaar number"
        ],
    }

    # Legacy document families kept here for future reuse, but they are intentionally
    # not part of the active KYC classifier so the product stays focused on the three
    # supported Indian document types.
    # LEGACY_KEYWORDS = {
    #     "driver_license": [...],
    #     "passport_card": [...],
    #     "permanent_resident_card": [...],
    #     "birth_certificate": [...],
    #     "social_security_card": [...],
    #     "bank_statement": [...],
    #     "w2": [...],
    #     "utility_bill": [...],
    # }
    
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
            if "pan" in filename_lower:
                print("  🎯 Detected from filename: pan")
                return "pan"
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