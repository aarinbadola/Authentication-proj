"""
Optimized OCR Service for Real Aadhaar Cards
Handles glare, blur, and other image issues
"""

import cv2
import pytesseract
import re
import tempfile
import os
import numpy as np
from config import OCR_CONFIDENCE_THRESHOLD

def preprocess_for_ocr(image):
    """
    Try multiple preprocessing approaches for better OCR
    Returns list of processed images to try
    """
    processed_images = []
    
    # Convert to grayscale
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    
    # Method 1: OTSU thresholding (best for normal images)
    _, thresh1 = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    processed_images.append(("OTSU", thresh1))
    
    # Method 2: Adaptive thresholding (best for glare/uneven lighting)
    adaptive = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                   cv2.THRESH_BINARY, 11, 2)
    processed_images.append(("ADAPTIVE", adaptive))
    
    # Method 3: Enhanced contrast + OTSU (for blur/low contrast)
    enhanced = cv2.equalizeHist(gray)
    denoised = cv2.bilateralFilter(enhanced, 9, 75, 75)
    _, thresh3 = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    processed_images.append(("ENHANCED", thresh3))
    
    # Method 4: Morphological operations (for broken text)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    morph = cv2.morphologyEx(thresh1, cv2.MORPH_CLOSE, kernel)
    processed_images.append(("MORPH", morph))
    
    return processed_images

def extract_text_hybrid(processed_images):
    """
    Try OCR on multiple processed versions, return best result
    """
    best_result = {"text": "", "confidence": 0, "method": ""}
    
    # Try different Tesseract configurations
    configs = [
        ("STANDARD", r'--oem 3 --psm 6'),
        ("SINGLE_BLOCK", r'--oem 3 --psm 8'),
        ("SINGLE_LINE", r'--oem 3 --psm 7'),
    ]
    
    for method_name, processed_img in processed_images:
        for config_name, config in configs:
            try:
                # Get text with confidence data
                data = pytesseract.image_to_data(processed_img, config=config, 
                                               output_type=pytesseract.Output.DICT)
                
                # Calculate average confidence
                confidences = [int(conf) for conf in data['conf'] if conf != '-1' and int(conf) > 0]
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0
                
                # Get clean text
                text = ' '.join([data['text'][i] for i in range(len(data['text'])) 
                               if int(data['conf'][i]) > OCR_CONFIDENCE_THRESHOLD])
                
                # Keep best result
                if avg_confidence > best_result["confidence"] and text.strip():
                    best_result = {
                        "text": text,
                        "confidence": avg_confidence,
                        "method": f"{method_name}+{config_name}"
                    }
                    
            except Exception:
                continue  # Try next approach
    
    return best_result

def extract_aadhaar_fields(text):
    """Extract Aadhaar number and name from text"""
    
    # Find Aadhaar number (12 digits with optional spaces/formatting)
    aadhaar_patterns = [
        r'\b\d{4}\s?\d{4}\s?\d{4}\b',  # Standard format
        r'\b\d{12}\b',                 # No spaces
        r'\b\d{4}[-\s]\d{4}[-\s]\d{4}\b'  # With dashes
    ]
    
    aadhaar_number = None
    for pattern in aadhaar_patterns:
        match = re.search(pattern, text)
        if match:
            # Clean the number
            aadhaar_number = re.sub(r'[^\d]', '', match.group())
            if len(aadhaar_number) == 12:
                break
    
    # Find name (multiple strategies)
    name = "Unknown"
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    # Strategy 1: Look for ALL CAPS words (common in Aadhaar)
    for line in lines:
        caps_words = [w for w in line.split() if w.isupper() and w.isalpha() and len(w) > 2]
        if len(caps_words) >= 2:  # At least first + last name
            name = ' '.join(caps_words[:3])  # Max 3 words
            break
    
    # Strategy 2: Look after common keywords
    if name == "Unknown":
        keywords = ['name', 'नाम', 'Name', 'NAME']
        for line in lines:
            for keyword in keywords:
                if keyword in line:
                    # Try to get name from same line or next line
                    words = line.replace(keyword, '').strip().split()
                    clean_words = [w for w in words if w.isalpha() and len(w) > 1]
                    if clean_words:
                        name = ' '.join(clean_words[:3])
                        break
    
    return aadhaar_number, name

async def extract_aadhaar_data(image_file):
    """
    Main function: Extract Aadhaar data with hybrid approach
    User never knows about multiple attempts
    """
    temp_file = None
    
    try:
        # Save uploaded file temporarily
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
        temp_file.write(await image_file.read())
        temp_file.close()
        
        # Load image
        image = cv2.imread(temp_file.name)
        if image is None:
            return {
                "success": False,
                "error": "Invalid image file",
                "confidence": 0
            }
        
        # Preprocess image with multiple methods
        processed_images = preprocess_for_ocr(image)
        
        # Try OCR with hybrid approach (user doesn't see individual failures)
        ocr_result = extract_text_hybrid(processed_images)
        
        if not ocr_result["text"] or ocr_result["confidence"] < 30:
            return {
                "success": False,
                "error": "Could not extract text from image",
                "confidence": 0
            }
        
        # Extract specific fields
        aadhaar_number, name = extract_aadhaar_fields(ocr_result["text"])
        
        # Validate results
        success = (aadhaar_number is not None and 
                  len(aadhaar_number) == 12 and 
                  aadhaar_number.isdigit() and
                  name != "Unknown")
        
        return {
            "success": success,
            "confidence": ocr_result["confidence"] / 100.0,  # Convert to 0-1
            "method_used": ocr_result["method"],  # For debugging
            "extracted_data": {
                "name": name,
                "aadhaar_number": aadhaar_number
            },
            "error": None if success else "Could not extract valid Aadhaar data"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"OCR processing failed: {str(e)}",
            "confidence": 0
        }
        
    finally:
        # Clean up
        if temp_file and os.path.exists(temp_file.name):
            os.unlink(temp_file.name)