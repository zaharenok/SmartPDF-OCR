import os
import fitz  # PyMuPDF
import pdfplumber
from pdf2image import convert_from_path
from PIL import Image
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

from config import Config
from utils import setup_logging, get_file_hash, ensure_output_structure

class PDFProcessor:
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.pdf_name = Path(pdf_path).name
        self.file_hash = get_file_hash(pdf_path)
        self.logger = setup_logging()
        
        # Initialize output structure
        self.output_structure = ensure_output_structure(Config.OUTPUT_DIR, self.pdf_name)
        
        # PDF documents for different libraries
        self.pymupdf_doc = None
        self.pdfplumber_doc = None
        
        self._load_documents()
    
    def _load_documents(self):
        """Load PDF with different libraries"""
        try:
            self.pymupdf_doc = fitz.open(self.pdf_path)
            self.pdfplumber_doc = pdfplumber.open(self.pdf_path)
            self.logger.info(f"PDF loaded successfully: {self.pdf_name}")
            self.logger.info(f"Total pages: {len(self.pymupdf_doc)}")
        except Exception as e:
            self.logger.error(f"Error loading PDF: {e}")
            raise
    
    def get_page_count(self) -> int:
        """Get total number of pages"""
        return len(self.pymupdf_doc) if self.pymupdf_doc else 0
    
    def get_metadata(self) -> Dict:
        """Extract PDF metadata"""
        if not self.pymupdf_doc:
            return {}
        
        metadata = self.pymupdf_doc.metadata
        return {
            'title': metadata.get('title', ''),
            'author': metadata.get('author', ''),
            'subject': metadata.get('subject', ''),
            'creator': metadata.get('creator', ''),
            'producer': metadata.get('producer', ''),
            'creation_date': metadata.get('creationDate', ''),
            'modification_date': metadata.get('modDate', ''),
            'pages': self.get_page_count(),
            'file_size': os.path.getsize(self.pdf_path),
            'file_hash': self.file_hash
        }
    
    def extract_page_text_native(self, page_num: int) -> str:
        """Extract text using native PDF text extraction"""
        try:
            # Try PyMuPDF first
            page = self.pymupdf_doc[page_num]
            text_pymupdf = page.get_text()
            
            # Try pdfplumber as fallback
            if len(text_pymupdf.strip()) < Config.MIN_TEXT_LENGTH:
                page_plumber = self.pdfplumber_doc.pages[page_num]
                text_plumber = page_plumber.extract_text() or ""
                
                # Return the longer text
                if len(text_plumber) > len(text_pymupdf):
                    return text_plumber
            
            return text_pymupdf
            
        except Exception as e:
            self.logger.warning(f"Error extracting native text from page {page_num}: {e}")
            return ""
    
    def convert_page_to_image(self, page_num: int, dpi: int = Config.PDF_DPI) -> Optional[Image.Image]:
        """Convert PDF page to image"""
        try:
            # Use pdf2image for conversion
            images = convert_from_path(
                self.pdf_path,
                first_page=page_num + 1,
                last_page=page_num + 1,
                dpi=dpi,
                fmt=Config.PDF_FORMAT.lower()
            )
            
            if images:
                # Save image for debugging/caching
                image_path = os.path.join(
                    self.output_structure['images'], 
                    f"page_{page_num:04d}.{Config.PDF_FORMAT.lower()}"
                )
                images[0].save(image_path)
                
                return images[0]
                
        except Exception as e:
            self.logger.error(f"Error converting page {page_num} to image: {e}")
            return None
    
    def analyze_page_content(self, page_num: int) -> Dict:
        """Analyze page content to determine best extraction method"""
        try:
            # Get native text
            native_text = self.extract_page_text_native(page_num)
            
            # Analyze with pdfplumber for tables and layout
            page = self.pdfplumber_doc.pages[page_num]
            
            # Check for tables
            tables = page.find_tables()
            
            # Check for images
            if self.pymupdf_doc:
                page_pymupdf = self.pymupdf_doc[page_num]
                images = page_pymupdf.get_images()
            else:
                images = []
            
            # Determine content type
            content_type = "text"
            if tables:
                content_type = "table"
            elif images and len(native_text.strip()) < Config.MIN_TEXT_LENGTH:
                content_type = "image"
            elif len(native_text.strip()) < Config.MIN_TEXT_LENGTH:
                content_type = "mixed"
            
            return {
                'page_num': page_num,
                'content_type': content_type,
                'native_text_length': len(native_text.strip()),
                'has_tables': len(tables) > 0,
                'table_count': len(tables),
                'has_images': len(images) > 0,
                'image_count': len(images),
                'needs_ocr': len(native_text.strip()) < Config.MIN_TEXT_LENGTH
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing page {page_num}: {e}")
            return {
                'page_num': page_num,
                'content_type': 'mixed',
                'needs_ocr': True
            }
    
    def extract_tables_from_page(self, page_num: int) -> List[List[List[str]]]:
        """Extract tables from page using pdfplumber"""
        try:
            page = self.pdfplumber_doc.pages[page_num]
            tables = page.find_tables()
            
            extracted_tables = []
            for table in tables:
                table_data = table.extract()
                if table_data:
                    extracted_tables.append(table_data)
            
            return extracted_tables
            
        except Exception as e:
            self.logger.warning(f"Error extracting tables from page {page_num}: {e}")
            return []
    
    def process_pages_parallel(self, max_workers: int = Config.MAX_WORKERS) -> List[Dict]:
        """Process all pages in parallel to analyze content"""
        pages_info = []
        total_pages = self.get_page_count()
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all page analysis tasks
            future_to_page = {
                executor.submit(self.analyze_page_content, page_num): page_num 
                for page_num in range(total_pages)
            }
            
            # Collect results with progress bar
            with tqdm(total=total_pages, desc="Analyzing pages") as pbar:
                for future in as_completed(future_to_page):
                    page_num = future_to_page[future]
                    try:
                        page_info = future.result()
                        pages_info.append(page_info)
                        pbar.update(1)
                    except Exception as e:
                        self.logger.error(f"Error processing page {page_num}: {e}")
                        pbar.update(1)
        
        # Sort by page number
        pages_info.sort(key=lambda x: x['page_num'])
        return pages_info
    
    def get_page_dimensions(self, page_num: int) -> Tuple[float, float]:
        """Get page dimensions in points"""
        try:
            page = self.pymupdf_doc[page_num]
            rect = page.rect
            return rect.width, rect.height
        except Exception as e:
            self.logger.warning(f"Error getting dimensions for page {page_num}: {e}")
            return 595.0, 842.0  # Default A4 size
    
    def close(self):
        """Close all PDF documents"""
        if self.pymupdf_doc:
            self.pymupdf_doc.close()
        if self.pdfplumber_doc:
            self.pdfplumber_doc.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()