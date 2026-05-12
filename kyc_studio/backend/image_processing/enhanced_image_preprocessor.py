"""
Enhanced Image Preprocessor for ID Cards
Specialized preprocessing for driver licenses, passports, green cards
"""

import cv2
import numpy as np
from PIL import Image
from typing import Tuple


class ImagePreprocessor:
    """Advanced image preprocessing for ID card OCR"""
    
    def __init__(self):
        self.target_dpi = 300  # Optimal for OCR
        self.min_width = 1000
        
    def prepare_for_ocr(self, image_path: str) -> Tuple[np.ndarray, Image.Image]:
        """
        Complete preprocessing pipeline
        
        Returns:
            preprocessed_cv: OpenCV image for Tesseract
            original_pil: PIL image for GPT-4o Vision
        """
        # Load image
        img = cv2.imread(image_path)
        original_pil = Image.open(image_path)
        
        if img is None:
            raise ValueError(f"Could not load image: {image_path}")
        
        print(f"  📸 Original size: {img.shape[1]}x{img.shape[0]}")
        
        # Step 1: Resize if needed
        img = self._resize_optimal(img)
        
        # Step 2: Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Step 3: Denoise
        denoised = cv2.fastNlMeansDenoising(gray, None, h=10, templateWindowSize=7, searchWindowSize=21)
        
        # Step 4: Enhance contrast
        enhanced = self._enhance_contrast(denoised)
        
        # Step 5: Adaptive thresholding
        thresh = cv2.adaptiveThreshold(
            enhanced, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11, 2
        )
        
        print(f"   Preprocessed size: {thresh.shape[1]}x{thresh.shape[0]}")
        
        return thresh, original_pil
    
    def _resize_optimal(self, img: np.ndarray) -> np.ndarray:
        """Resize to optimal dimensions for OCR"""
        height, width = img.shape[:2]
        
        # If too small, upscale
        if width < self.min_width:
            scale = self.min_width / width
            new_width = int(width * scale)
            new_height = int(height * scale)
            img = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
            print(f"      Upscaled to {new_width}x{new_height}")
        
        # If too large, downscale
        elif width > 3000:
            scale = 3000 / width
            new_width = int(width * scale)
            new_height = int(height * scale)
            img = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_AREA)
            print(f"      Downscaled to {new_width}x{new_height}")
        
        return img
    
    def _enhance_contrast(self, img: np.ndarray) -> np.ndarray:
        """Enhance contrast using CLAHE"""
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(img)
        return enhanced
    
    def save_preprocessed(self, img: np.ndarray, output_path: str):
        """Save preprocessed image for debugging"""
        cv2.imwrite(output_path, img)
        print(f"   Saved preprocessed: {output_path}")