"""
Main OCR Extraction Pipeline
Processes scanned ID card images and extracts structured JSON data

USAGE:
    python ocr_extraction_pipeline.py --input images/ --output ocr_results/
    python ocr_extraction_pipeline.py --single driver_license.jpg
"""

import os
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from dotenv import load_dotenv

from enhanced_image_preprocessor import ImagePreprocessor
from document_type_detector import DocumentTypeDetector
from hybrid_ocr_extractor import HybridOCRExtractor


class OCRExtractionPipeline:
    """Complete OCR extraction pipeline for ID cards"""
    
    def __init__(self, api_key: str, tesseract_path: str = None):
        """Initialize pipeline components"""
        self.preprocessor = ImagePreprocessor()
        self.detector = DocumentTypeDetector()
        self.extractor = HybridOCRExtractor(api_key, tesseract_path)
        self.results = []
    
    def process_single_image(self, image_path: str, declared_doc_type: Optional[str] = None) -> Dict:
        """
        Process a single ID card image
        
        Args:
            image_path: Path to image file
            declared_doc_type: Upload slot type from UI (overrides detector when set)
            
        Returns:
            Extracted JSON data
        """
        print(f"\n{'='*70}")
        print(f"PROCESSING: {os.path.basename(image_path)}")
        print(f"{'='*70}")
        
        try:
            # Step 1: Preprocess image
            print("\n[1/4] Preprocessing image...")
            preprocessed, original = self.preprocessor.prepare_for_ocr(image_path)
            
            # Step 2: Quick OCR for document type detection
            print("\n[2/4] Detecting document type...")
            import pytesseract
            quick_ocr = pytesseract.image_to_string(original)
            print("@@@@@@@@@@@@@ quick_ocr is:", quick_ocr)
            detected_type = self.detector.detect(quick_ocr)
            doc_type = detected_type
            if declared_doc_type:
                declared = str(declared_doc_type).lower().strip()
                alias = {"pan_card": "pan", "pancard": "pan", "aadhar": "aadhaar"}
                doc_type = alias.get(declared, declared)
                if detected_type != doc_type and detected_type != "unknown":
                    print(
                        f"  ⚠️  Declared type '{doc_type}' overrides detector '{detected_type}'"
                    )
            
            # Step 3: Hybrid extraction
            print("\n[3/4] Extracting structured data...")
            extracted_data = self.extractor.extract_hybrid(
                preprocessed_image=preprocessed,
                original_image=original,
                doc_type=doc_type
            )
            
            # Step 4: Add metadata
            extracted_data["_metadata"] = {
                "source_file": os.path.basename(image_path),
                "extraction_timestamp": datetime.now().isoformat(),
                "detected_type": detected_type,
                "declared_type": declared_doc_type,
                "confidence": self.detector.get_confidence(quick_ocr, doc_type)
            }
            
            print(f"\n✅ Successfully extracted {doc_type}")
            print(f"   Fields: {list(extracted_data.keys())}")
            
            return extracted_data
        
        except Exception as e:
            print(f"\n Error processing {image_path}: {e}")
            import traceback
            traceback.print_exc()
            
            return {
                "document_type": "error",
                "error": str(e),
                "_metadata": {
                    "source_file": os.path.basename(image_path),
                    "extraction_timestamp": datetime.now().isoformat()
                }
            }
    
    def process_directory(self, input_dir: str) -> List[Dict]:
        """
        Process all images in a directory
        
        Args:
            input_dir: Directory containing images
            
        Returns:
            List of extracted data dictionaries
        """
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff'}
        image_files = []
        
        # Find all image files
        for ext in image_extensions:
            image_files.extend(Path(input_dir).glob(f"*{ext}"))
            image_files.extend(Path(input_dir).glob(f"*{ext.upper()}"))
        
        print(f"\n{'='*70}")
        print(f"FOUND {len(image_files)} IMAGES IN {input_dir}")
        print(f"{'='*70}")
        
        results = []
        for image_file in image_files:
            result = self.process_single_image(str(image_file))
            results.append(result)
        
        return results
    
    def save_results(self, output_dir: str, consolidated: bool = True):
        """
        Save extraction results
        
        Args:
            output_dir: Output directory
            consolidated: Also save consolidated JSON
        """
        os.makedirs(output_dir, exist_ok=True)
        
        # Save individual JSONs
        for result in self.results:
            if result.get("document_type") == "error":
                continue
            
            filename = result["_metadata"]["source_file"]
            doc_type = result["document_type"]
            
            # Create filename: {doc_type}_{original_name}.json
            base_name = Path(filename).stem
            output_file = f"{doc_type}_{base_name}.json"
            output_path = os.path.join(output_dir, output_file)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            
            print(f"  💾 Saved: {output_file}")
        
        # Save consolidated JSON
        if consolidated and self.results:
            consolidated_path = os.path.join(output_dir, "all_extracted_documents.json")
            
            with open(consolidated_path, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, indent=2, ensure_ascii=False)
            
            print(f"\n   Saved consolidated: all_extracted_documents.json")
        
        # Save summary
        summary = {
            "total_processed": len(self.results),
            "successful": len([r for r in self.results if r.get("document_type") != "error"]),
            "failed": len([r for r in self.results if r.get("document_type") == "error"]),
            "document_types": {}
        }
        
        for result in self.results:
            doc_type = result.get("document_type", "unknown")
            summary["document_types"][doc_type] = summary["document_types"].get(doc_type, 0) + 1
        
        summary_path = os.path.join(output_dir, "extraction_summary.json")
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)
        
        print(f"\n   Summary:")
        print(f"     Total: {summary['total_processed']}")
        print(f"     Success: {summary['successful']}")
        print(f"     Failed: {summary['failed']}")
        print(f"     Types: {summary['document_types']}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="OCR Extraction Pipeline for ID Cards")
    parser.add_argument('--input', '-i', help='Input directory or single image file')
    parser.add_argument('--output', '-o', default='ocr_results', help='Output directory')
    parser.add_argument('--tesseract', '-t', default='C:\\Program Files\\Tesseract-OCR\\tesseract.exe',
                       help='Path to Tesseract executable')
    
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv()
    api_key = os.getenv("DIAL_API_KEY")
    
    if not api_key:
        print(" Error: DIAL_API_KEY not found in environment")
        print("   Please set it in .env file")
        return
    
    # Initialize pipeline
    print("="*70)
    print("OCR EXTRACTION PIPELINE FOR ID CARDS")
    print("="*70)
    
    pipeline = OCRExtractionPipeline(api_key, args.tesseract)
    
    # Process input
    if not args.input:
        print("\n   No input specified. Using default test images...")
        # Default: process uploaded sample images
        args.input = "C:\\Users\\SatyaprasadDakinedi\\Desktop\\images"
        
        # Process only the 3 latest images (your samples)
        import glob
        all_images = sorted(glob.glob(f"{args.input}/*_image.png"))
        # process all the images
        sample_images = all_images  # All images
        #sample_images = all_images[-3:]  # Last 3 images
        
        print(f"\nProcessing {len(sample_images)} sample images:")
        for img in sample_images:
            print(f"  - {os.path.basename(img)}")
        
        for image_path in sample_images:
            result = pipeline.process_single_image(image_path)
            pipeline.results.append(result)
    
    elif os.path.isfile(args.input):
        # Single file
        result = pipeline.process_single_image(args.input)
        pipeline.results.append(result)
    
    elif os.path.isdir(args.input):
        # Directory
        pipeline.results = pipeline.process_directory(args.input)
    
    else:
        print(f" Error: {args.input} not found")
        return
    
    # Save results
    if pipeline.results:
        print(f"\n{'='*70}")
        print("SAVING RESULTS")
        print(f"{'='*70}")
        pipeline.save_results(args.output)
        
        print(f"\n{'='*70}")
        print("✅ EXTRACTION COMPLETE!")
        print(f"{'='*70}")
        print(f"\nResults saved to: {args.output}/")
        print(f"  • Individual JSONs: {args.output}/{{doc_type}}_{{filename}}.json")
        print(f"  • Consolidated: {args.output}/all_extracted_documents.json")
        print(f"  • Summary: {args.output}/extraction_summary.json")


if __name__ == "__main__":
    main()