"""
Hybrid OCR Extractor
Combines Tesseract OCR with GPT-4o Vision for accurate field extraction
"""

import os
import json
import base64
from io import BytesIO
from typing import Dict, Optional
import pytesseract
from PIL import Image
import requests

from document_schemas import DocumentSchemaHandler


class HybridOCRExtractor:
    """Extract structured data using Tesseract + GPT-4o Vision"""
    
    def __init__(self, api_key: str, tesseract_path: Optional[str] = None):
        """
        Initialize extractor
        
        Args:
            api_key: DIAL API key for GPT-4o Vision
            tesseract_path: Path to tesseract executable (Windows)
        """
        self.api_key = api_key
        self.endpoint = "https://ai-proxy.lab.epam.com"
        self.schema_handler = DocumentSchemaHandler()
        
        # Set Tesseract path if provided
        if tesseract_path and os.path.exists(tesseract_path):
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
            print(f"✅ Tesseract configured: {tesseract_path}")
        
        # Verify Tesseract
        try:
            version = pytesseract.get_tesseract_version()
            print(f"✅ Tesseract version: {version}")
        except Exception as e:
            print(f"  Tesseract warning: {e}")
    
    def extract_with_tesseract(self, preprocessed_image) -> str:
        """
        Extract text using Tesseract OCR
        
        Args:
            preprocessed_image: Preprocessed numpy/PIL image
            
        Returns:
            Raw OCR text
        """
        try:
            # Custom config for better accuracy
            custom_config = r'--oem 3 --psm 6 --dpi 300'
            
            # Extract text
            text = pytesseract.image_to_string(preprocessed_image, config=custom_config)
            
            print(f"   OCR extracted {len(text)} characters")
            
            return text.strip()
        
        except Exception as e:
            print(f"    OCR error: {e}")
            return ""
    
    def extract_with_gpt4_vision(
        self,
        original_image: Image.Image,
        doc_type: str,
        ocr_hint: str = ""
    ) -> Dict:
        """
        Extract structured data using GPT-4o Vision
        
        Args:
            original_image: Original PIL image
            doc_type: Detected document type
            ocr_hint: OCR text as hint
            
        Returns:
            Structured JSON data
        """
        print(f"   Using GPT-4o Vision for {doc_type}...")
        
        # Convert image to base64
        buffered = BytesIO()
        original_image.save(buffered, format="PNG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode()
        
        # Get schema-specific prompt
        prompt = self.schema_handler.get_gpt4_vision_prompt(doc_type, ocr_hint)
        
        # Call GPT-4o Vision API
        try:
            url = f"{self.endpoint}/openai/deployments/gpt-4o/chat/completions?api-version=2024-02-01"
            
            headers = {
                "Content-Type": "application/json",
                "api-key": self.api_key
            }
            
            payload = {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/png;base64,{img_base64}"}
                            }
                        ]
                    }
                ],
                "max_tokens": 4096,
                "temperature": 0.0  # Deterministic for data extraction
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            # Clean and parse JSON
            cleaned = content.replace("```json", "").replace("```", "").strip()
            data = json.loads(cleaned)
            
            print(f"  ✅ Structured data extracted")
            
            return data
        
        except requests.exceptions.RequestException as e:
            print(f"  ❌ API error: {e}")
            raise
        
        except json.JSONDecodeError as e:
            print(f"  ❌ JSON parsing error: {e}")
            print(f"     Response preview: {content[:200]}")
            raise
    
    def extract_hybrid(
        self,
        preprocessed_image,
        original_image: Image.Image,
        doc_type: str
    ) -> Dict:
        """
        Complete hybrid extraction pipeline
        
        Args:
            preprocessed_image: Preprocessed image for Tesseract
            original_image: Original image for GPT-4o Vision
            doc_type: Document type
            
        Returns:
            Structured JSON data
        """
        # Phase 1: Tesseract OCR
        ocr_text = self.extract_with_tesseract(preprocessed_image)
        
        # Phase 2: GPT-4o Vision structuring
        structured_data = self.extract_with_gpt4_vision(
            original_image=original_image,
            doc_type=doc_type,
            ocr_hint=ocr_text
        )
        
        # Ensure document_type is set
        if "document_type" not in structured_data:
            structured_data["document_type"] = doc_type
        
        return structured_data