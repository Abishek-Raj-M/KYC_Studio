"""
Document Type Detector
Auto-detects document type from image and OCR text
"""

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
            "pan number", "income tax", "pancard", "permanent account"
        ],
        "aadhaar": [
            "aadhaar", "uidai", "unique identification", "aadhaar number",
            "enrollment", "your aadhaar", "government of india", "भारत सरकार",
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
    
    def detect(self, ocr_text: str) -> str:
        """
        Detect document type from OCR text only (no filename hints).

        Args:
            ocr_text: Raw OCR extracted text

        Returns:
            Document type string
        """
        if not ocr_text:
            return "unknown"
        
        text_lower = ocr_text.lower()
        
        # Score each document type (strong signals weighted higher)
        scores = {}
        for doc_type, keywords in self.KEYWORDS.items():
            score = 0
            for keyword in keywords:
                if keyword in text_lower:
                    score += 2 if doc_type == "aadhaar" and keyword in {"uidai", "aadhaar number", "your aadhaar"} else 1
            scores[doc_type] = score

        # Generic "government of india" appears on Aadhaar and PAN — do not let it alone pick PAN
        if scores.get("pan", 0) <= 1 and "government of india" in text_lower:
            scores["pan"] = 0
        if "uidai" in text_lower or "aadhaar" in text_lower:
            scores["aadhaar"] = scores.get("aadhaar", 0) + 2
        
        # Get best match
        if max(scores.values()) > 0:
            detected_type = max(scores, key=scores.get)
            confidence = scores[detected_type]
            print(f"  🎯 Detected: {detected_type} (confidence: {confidence} keywords)")
            return detected_type

        print("  ⚠️  Could not detect document type from OCR text")
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