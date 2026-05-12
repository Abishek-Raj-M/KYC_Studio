"""
Tests OCR extraction on given images

USAGE:
    python test_ocr_samples.py
"""

import os
import sys
from dotenv import load_dotenv

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

from ocr_extraction_pipeline import OCRExtractionPipeline


def main():
    print("="*70)
    print("TESTING OCR ON GIVEN IMAGES")
    print("="*70)
    
    # Load API key
    load_dotenv()
    api_key = os.getenv("DIAL_API_KEY")
    
    if not api_key:
        print(" DIAL_API_KEY not found in .env")
        return
    
    # Initialize pipeline
    tesseract_path = "C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
    pipeline = OCRExtractionPipeline(api_key, tesseract_path)
    
    # Sample images
    sample_images = [
       # "C:\\Users\\SatyaprasadDakinedi\\Desktop\\images\\driver_license.png",  # Driver License
        "C:\\Users\\SatyaprasadDakinedi\\Desktop\\images\\green_card.png",  # Green Card
       #"C:\\Users\\SatyaprasadDakinedi\\Desktop\\images\\passport.png",  # Passport Card
       # "C:\\Users\\SatyaprasadDakinedi\\Desktop\\images\\green_card_fake.png"
        #"C:\\Users\\SatyaprasadDakinedi\\Desktop\\images\\driver_license_tainted.png" # Random Image (should produce error)
    ]
    
    # Process each
    for image_path in sample_images:
        if os.path.exists(image_path):
            result = pipeline.process_single_image(image_path)
            pipeline.results.append(result)
        else:
            print(f"  Image not found: {image_path}")
    
    # Save results
    if pipeline.results:
        output_dir = "ocr_test_results"
        pipeline.save_results(output_dir)
        
        print(f"\n{'='*70}")
        print(" TEST COMPLETE!")
        print(f"{'='*70}")
        print(f"\nCheck results in: {output_dir}/")
        print(f"  • driver_license_*.json")
        print(f"  • green_card_*.json")
        print(f"  • passport_*.json")
        print(f"  • all_extracted_documents.json")


if __name__ == "__main__":
    main()