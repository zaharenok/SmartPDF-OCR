import os
import logging
import hashlib
from pathlib import Path
from typing import Optional, List, Dict, Any
import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
from config import Config

def setup_logging(level: str = Config.LOG_LEVEL) -> logging.Logger:
    """Set up logging configuration"""
    logging.basicConfig(
        level=getattr(logging, level),
        format=Config.LOG_FORMAT,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('pdf_extraction.log')
        ]
    )
    return logging.getLogger(__name__)

def create_cache_key(data: str) -> str:
    """Create a cache key from data"""
    return hashlib.md5(data.encode()).hexdigest()

def save_to_cache(key: str, data: Any, cache_dir: str = Config.CACHE_DIR) -> None:
    """Save data to cache"""
    cache_path = Path(cache_dir) / f"{key}.cache"
    with open(cache_path, 'w', encoding='utf-8') as f:
        f.write(str(data))

def load_from_cache(key: str, cache_dir: str = Config.CACHE_DIR) -> Optional[str]:
    """Load data from cache"""
    cache_path = Path(cache_dir) / f"{key}.cache"
    if cache_path.exists():
        with open(cache_path, 'r', encoding='utf-8') as f:
            return f.read()
    return None

def preprocess_image(image: Image.Image, preprocessing: List[str]) -> Image.Image:
    """Apply preprocessing to image before OCR"""
    processed = image.copy()
    
    for operation in preprocessing:
        if operation == "deskew":
            processed = deskew_image(processed)
        elif operation == "noise_removal":
            processed = remove_noise(processed)
        elif operation == "contrast_enhancement":
            processed = enhance_contrast(processed)
        elif operation == "line_detection":
            processed = enhance_lines(processed)
    
    return processed

def deskew_image(image: Image.Image) -> Image.Image:
    """Correct skew in image"""
    # Convert PIL to OpenCV
    opencv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(opencv_image, cv2.COLOR_BGR2GRAY)
    
    # Apply threshold to get binary image
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # Find contours
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Calculate skew angle
    if contours:
        largest_contour = max(contours, key=cv2.contourArea)
        rect = cv2.minAreaRect(largest_contour)
        angle = rect[2]
        
        # Correct angle
        if angle < -45:
            angle = 90 + angle
        
        # Rotate image
        if abs(angle) > 0.5:  # Only rotate if angle is significant
            h, w = opencv_image.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            rotated = cv2.warpAffine(opencv_image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
            
            # Convert back to PIL
            return Image.fromarray(cv2.cvtColor(rotated, cv2.COLOR_BGR2RGB))
    
    return image

def remove_noise(image: Image.Image) -> Image.Image:
    """Remove noise from image"""
    # Convert to grayscale for noise removal
    gray = image.convert('L')
    
    # Apply median filter to remove noise
    filtered = gray.filter(ImageFilter.MedianFilter(size=3))
    
    # Convert back to RGB
    return filtered.convert('RGB')

def enhance_contrast(image: Image.Image) -> Image.Image:
    """Enhance image contrast"""
    enhancer = ImageEnhance.Contrast(image)
    return enhancer.enhance(1.5)

def enhance_lines(image: Image.Image) -> Image.Image:
    """Enhance lines in image for table detection"""
    opencv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(opencv_image, cv2.COLOR_BGR2GRAY)
    
    # Apply morphological operations to enhance lines
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 1))
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 25))
    
    horizontal_lines = cv2.morphologyEx(gray, cv2.MORPH_OPEN, horizontal_kernel, iterations=2)
    vertical_lines = cv2.morphologyEx(gray, cv2.MORPH_OPEN, vertical_kernel, iterations=2)
    
    # Combine lines
    lines = cv2.addWeighted(horizontal_lines, 0.5, vertical_lines, 0.5, 0.0)
    
    # Add lines back to original
    enhanced = cv2.addWeighted(gray, 0.8, lines, 0.2, 0.0)
    
    # Convert back to PIL RGB
    enhanced_rgb = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2RGB)
    return Image.fromarray(enhanced_rgb)

def clean_text(text: str) -> str:
    """Clean extracted text"""
    if not text:
        return ""
    
    # Remove extra whitespace
    text = ' '.join(text.split())
    
    # Remove common OCR artifacts
    text = text.replace('|', 'I')  # Common OCR mistake
    text = text.replace('0', 'O')  # In text context
    
    return text.strip()

def is_text_meaningful(text: str, min_length: int = Config.MIN_TEXT_LENGTH) -> bool:
    """Check if extracted text is meaningful"""
    if not text or len(text.strip()) < min_length:
        return False
    
    # Check if text contains mostly special characters
    alphanumeric_chars = sum(c.isalnum() for c in text)
    return alphanumeric_chars > len(text) * 0.7

def get_file_hash(file_path: str) -> str:
    """Get MD5 hash of file for caching"""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def ensure_output_structure(base_path: str, pdf_name: str) -> Dict[str, str]:
    """Create output directory structure for a PDF"""
    pdf_base = Path(pdf_name).stem
    structure = {
        'base': os.path.join(base_path, pdf_base),
        'pages': os.path.join(base_path, pdf_base, 'pages'),
        'images': os.path.join(base_path, pdf_base, 'images'),
        'text': os.path.join(base_path, pdf_base, 'text'),
        'markdown': os.path.join(base_path, pdf_base, 'markdown')
    }
    
    for path in structure.values():
        Path(path).mkdir(parents=True, exist_ok=True)
    
    return structure

def format_progress(current: int, total: int, prefix: str = "Progress") -> str:
    """Format progress string"""
    percentage = (current / total) * 100 if total > 0 else 0
    return f"{prefix}: {current}/{total} ({percentage:.1f}%)"