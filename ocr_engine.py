import os
import pytesseract
import easyocr
from PIL import Image
import numpy as np
from typing import Dict, List, Optional, Tuple
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

from config import Config, DOCUMENT_TYPES
from utils import (
    setup_logging, preprocess_image, clean_text, 
    is_text_meaningful, create_cache_key, save_to_cache, load_from_cache
)

class OCREngine:
    def __init__(self):
        self.logger = setup_logging()
        self.tesseract_path = Config.get_tesseract_path()
        self.easyocr_reader = None
        
        self._setup_tesseract()
        self._setup_easyocr()
    
    def _setup_tesseract(self):
        """Setup Tesseract OCR"""
        try:
            # Set Tesseract path if found
            if os.path.exists(self.tesseract_path):
                pytesseract.pytesseract.tesseract_cmd = self.tesseract_path
            
            # Test Tesseract
            version = pytesseract.get_tesseract_version()
            self.logger.info(f"Tesseract version: {version}")
            self.tesseract_available = True
            
        except Exception as e:
            self.logger.warning(f"Tesseract not available: {e}")
            self.tesseract_available = False
    
    def _setup_easyocr(self):
        """Setup EasyOCR"""
        try:
            self.easyocr_reader = easyocr.Reader(
                Config.EASYOCR_LANGS, 
                gpu=Config.EASYOCR_GPU
            )
            self.easyocr_available = True
            self.logger.info("EasyOCR initialized successfully")
            
        except Exception as e:
            self.logger.warning(f"EasyOCR not available: {e}")
            self.easyocr_available = False
    
    def extract_with_tesseract(
        self, 
        image: Image.Image, 
        config: str = Config.TESSERACT_CONFIG,
        lang: str = Config.TESSERACT_LANG
    ) -> Tuple[str, float]:
        """Extract text using Tesseract OCR with confidence score"""
        if not self.tesseract_available:
            return "", 0.0
        
        try:
            # Get text with confidence data
            data = pytesseract.image_to_data(
                image, 
                config=config,
                lang=lang,
                output_type=pytesseract.Output.DICT
            )
            
            # Extract text and calculate average confidence
            texts = []
            confidences = []
            
            for i, conf in enumerate(data['conf']):
                if int(conf) > 0:  # Valid confidence
                    text = data['text'][i].strip()
                    if text:
                        texts.append(text)
                        confidences.append(int(conf))
            
            # Combine text
            full_text = ' '.join(texts)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            # Clean text
            cleaned_text = clean_text(full_text)
            
            return cleaned_text, avg_confidence
            
        except Exception as e:
            self.logger.error(f"Tesseract OCR error: {e}")
            return "", 0.0
    
    def extract_with_easyocr(self, image: Image.Image) -> Tuple[str, float]:
        """Extract text using EasyOCR with confidence score"""
        if not self.easyocr_available:
            return "", 0.0
        
        try:
            # Convert PIL image to numpy array
            image_array = np.array(image)
            
            # Run EasyOCR
            results = self.easyocr_reader.readtext(image_array)
            
            # Extract text and confidence
            texts = []
            confidences = []
            
            for (bbox, text, confidence) in results:
                if confidence > 0.1:  # Filter very low confidence
                    texts.append(text.strip())
                    confidences.append(confidence * 100)  # Convert to 0-100 scale
            
            # Combine text
            full_text = ' '.join(texts)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            # Clean text
            cleaned_text = clean_text(full_text)
            
            return cleaned_text, avg_confidence
            
        except Exception as e:
            self.logger.error(f"EasyOCR error: {e}")
            return "", 0.0
    
    def extract_with_preprocessing(
        self, 
        image: Image.Image, 
        document_type: str = "mixed"
    ) -> Dict[str, Tuple[str, float]]:
        """Extract text with different preprocessing methods"""
        results = {}
        
        # Get preprocessing methods for document type
        doc_config = DOCUMENT_TYPES.get(document_type, DOCUMENT_TYPES["mixed"])
        preprocessing_methods = doc_config["preprocessing"]
        
        # Try without preprocessing
        results["no_preprocessing"] = self._extract_with_both_engines(image)
        
        # Try with preprocessing
        preprocessed_image = preprocess_image(image, preprocessing_methods)
        results["with_preprocessing"] = self._extract_with_both_engines(preprocessed_image)
        
        return results
    
    def _extract_with_both_engines(self, image: Image.Image) -> Dict[str, Tuple[str, float]]:
        """Extract text with both OCR engines"""
        results = {}
        
        # Tesseract
        if self.tesseract_available:
            text, conf = self.extract_with_tesseract(image)
            results["tesseract"] = (text, conf)
        
        # EasyOCR
        if self.easyocr_available:
            text, conf = self.extract_with_easyocr(image)
            results["easyocr"] = (text, conf)
        
        return results
    
    def choose_best_result(self, results: Dict[str, Dict[str, Tuple[str, float]]]) -> Tuple[str, float, str]:
        """Choose the best OCR result based on confidence and text quality"""
        best_text = ""
        best_confidence = 0.0
        best_method = "none"
        
        for preprocessing_type, engine_results in results.items():
            for engine, (text, confidence) in engine_results.items():
                
                # Skip if text is not meaningful
                if not is_text_meaningful(text):
                    continue
                
                # Calculate quality score (combine confidence and text length)
                text_length_score = min(len(text) / 100, 1.0)  # Normalize to 0-1
                quality_score = (confidence * 0.7) + (text_length_score * 30)
                
                # Choose best result
                if quality_score > best_confidence:
                    best_text = text
                    best_confidence = confidence
                    best_method = f"{engine}_{preprocessing_type}"
        
        return best_text, best_confidence, best_method
    
    def extract_text_comprehensive(
        self, 
        image: Image.Image, 
        document_type: str = "mixed",
        use_cache: bool = True
    ) -> Dict:
        """Comprehensive text extraction with multiple methods"""
        
        # Create cache key
        if use_cache:
            cache_key = create_cache_key(f"{image.tobytes()}_{document_type}")
            cached_result = load_from_cache(cache_key)
            if cached_result:
                return eval(cached_result)  # Convert string back to dict
        
        start_time = time.time()
        
        # Extract with preprocessing
        results = self.extract_with_preprocessing(image, document_type)
        
        # Choose best result
        best_text, best_confidence, best_method = self.choose_best_result(results)
        
        processing_time = time.time() - start_time
        
        # Prepare final result
        final_result = {
            'text': best_text,
            'confidence': best_confidence,
            'method': best_method,
            'processing_time': processing_time,
            'all_results': results,
            'text_length': len(best_text),
            'is_meaningful': is_text_meaningful(best_text),
            'document_type': document_type
        }
        
        # Cache result
        if use_cache:
            save_to_cache(cache_key, str(final_result))
        
        return final_result
    
    def batch_extract(
        self, 
        images: List[Image.Image], 
        document_types: List[str] = None,
        max_workers: int = Config.MAX_WORKERS
    ) -> List[Dict]:
        """Batch extract text from multiple images"""
        
        if document_types is None:
            document_types = ["mixed"] * len(images)
        
        results = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_index = {
                executor.submit(
                    self.extract_text_comprehensive, 
                    image, 
                    doc_type
                ): i
                for i, (image, doc_type) in enumerate(zip(images, document_types))
            }
            
            # Collect results
            for future in as_completed(future_to_index):
                index = future_to_index[future]
                try:
                    result = future.result()
                    result['page_index'] = index
                    results.append(result)
                except Exception as e:
                    self.logger.error(f"Error processing image {index}: {e}")
                    results.append({
                        'page_index': index,
                        'text': '',
                        'confidence': 0.0,
                        'method': 'failed',
                        'error': str(e)
                    })
        
        # Sort by page index
        results.sort(key=lambda x: x['page_index'])
        return results
    
    def get_engine_status(self) -> Dict:
        """Get status of available OCR engines"""
        return {
            'tesseract': {
                'available': self.tesseract_available,
                'path': self.tesseract_path,
                'version': pytesseract.get_tesseract_version() if self.tesseract_available else None
            },
            'easyocr': {
                'available': self.easyocr_available,
                'languages': Config.EASYOCR_LANGS if self.easyocr_available else None,
                'gpu_enabled': Config.EASYOCR_GPU if self.easyocr_available else None
            }
        }