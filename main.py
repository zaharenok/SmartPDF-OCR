#!/usr/bin/env python3
"""
SmartPDF-OCR: Intelligent PDF Text Extraction System

A comprehensive system for page-by-page PDF text extraction using multiple OCR engines
with intelligent preprocessing and markdown output optimized for LLM workflows.
"""

import argparse
import sys
import os
from pathlib import Path
from typing import List, Dict, Optional
import time
from tqdm import tqdm
import logging

# Import our modules
from config import Config
from utils import setup_logging, format_progress, ensure_output_structure
from pdf_processor import PDFProcessor
from ocr_engine import OCREngine
from markdown_converter import MarkdownConverter
from page_merger import PageMerger

class SmartPDFOCR:
    """Main application class for PDF text extraction"""
    
    def __init__(self, 
                 pdf_path: str, 
                 output_dir: str = None,
                 language: str = None,
                 dpi: int = None,
                 max_workers: int = None):
        
        self.pdf_path = pdf_path
        self.output_dir = output_dir or Config.OUTPUT_DIR
        self.language = language or Config.TESSERACT_LANG
        self.dpi = dpi or Config.PDF_DPI
        self.max_workers = max_workers or Config.MAX_WORKERS
        
        # Setup logging
        self.logger = setup_logging()
        
        # Ensure directories exist
        Config.ensure_dirs()
        
        # Initialize components
        self.pdf_processor = None
        self.ocr_engine = OCREngine()
        self.markdown_converter = MarkdownConverter()
        self.page_merger = None
        
        # Statistics
        self.start_time = None
        self.processing_stats = {}
    
    def validate_input(self) -> bool:
        """Validate input parameters and files"""
        
        # Check if PDF file exists
        if not os.path.exists(self.pdf_path):
            self.logger.error(f"PDF file not found: {self.pdf_path}")
            return False
        
        # Check if file is actually a PDF
        if not self.pdf_path.lower().endswith('.pdf'):
            self.logger.error(f"File is not a PDF: {self.pdf_path}")
            return False
        
        # Check file size (warn if very large)
        file_size = os.path.getsize(self.pdf_path)
        if file_size > 100 * 1024 * 1024:  # 100MB
            self.logger.warning(f"Large file detected ({file_size/1024/1024:.1f}MB). Processing may take a while.")
        
        # Check OCR engines availability
        engine_status = self.ocr_engine.get_engine_status()
        available_engines = [name for name, status in engine_status.items() if status['available']]
        
        if not available_engines:
            self.logger.error("No OCR engines available. Please install Tesseract or EasyOCR.")
            return False
        
        self.logger.info(f"Available OCR engines: {', '.join(available_engines)}")
        return True
    
    def process_pdf(self) -> Dict:
        """Main processing function"""
        
        self.start_time = time.time()
        
        try:
            # Initialize PDF processor
            self.pdf_processor = PDFProcessor(self.pdf_path)
            
            # Get PDF metadata
            pdf_metadata = self.pdf_processor.get_metadata()
            self.logger.info(f"Processing PDF: {pdf_metadata.get('title', 'Untitled')}")
            self.logger.info(f"Pages: {pdf_metadata.get('pages', 0)}")
            
            # Analyze all pages first
            self.logger.info("Analyzing page content...")
            pages_analysis = self.pdf_processor.process_pages_parallel(self.max_workers)
            
            # Initialize page merger
            self.page_merger = PageMerger(self.pdf_processor.output_structure)
            
            # Process each page for text extraction
            self.logger.info("Extracting text from pages...")
            pages_data = self._process_pages_for_extraction(pages_analysis)
            
            # Merge pages into final documents
            self.logger.info("Merging pages into final documents...")
            final_outputs = self.page_merger.merge_pages_to_document(pages_data, pdf_metadata)
            
            # Save individual page files for review
            self.page_merger.create_individual_page_files(pages_data)
            
            # Calculate final statistics
            processing_time = time.time() - self.start_time
            final_stats = self.page_merger.get_merge_statistics(pages_data)
            final_stats['total_processing_time'] = processing_time
            
            self.processing_stats = final_stats
            
            # Log completion
            self.logger.info(f"Processing completed in {processing_time:.2f} seconds")
            self.logger.info(f"Successfully processed {final_stats['successful_extractions']}/{final_stats['total_pages']} pages")
            self.logger.info(f"Average confidence: {final_stats['average_confidence']:.1f}%")
            
            return {
                'success': True,
                'outputs': final_outputs,
                'statistics': final_stats,
                'output_directory': self.pdf_processor.output_structure['base']
            }
            
        except Exception as e:
            self.logger.error(f"Error processing PDF: {e}")
            return {
                'success': False,
                'error': str(e),
                'statistics': self.processing_stats
            }
        
        finally:
            if self.pdf_processor:
                self.pdf_processor.close()
    
    def _process_pages_for_extraction(self, pages_analysis: List[Dict]) -> List[Dict]:
        """Process pages for text extraction based on analysis"""
        
        pages_data = []
        total_pages = len(pages_analysis)
        
        with tqdm(total=total_pages, desc="Extracting text") as pbar:
            for page_info in pages_analysis:
                page_num = page_info['page_num']
                content_type = page_info['content_type']
                needs_ocr = page_info['needs_ocr']
                
                try:
                    page_data = self._process_single_page(page_num, content_type, needs_ocr)
                    page_data.update(page_info)  # Merge analysis data
                    pages_data.append(page_data)
                    
                except Exception as e:
                    self.logger.error(f"Error processing page {page_num}: {e}")
                    pages_data.append({
                        'page_num': page_num,
                        'text': '',
                        'confidence': 0.0,
                        'method': 'failed',
                        'error': str(e)
                    })
                
                pbar.update(1)
                pbar.set_postfix({
                    'page': page_num + 1,
                    'type': content_type
                })
        
        return pages_data
    
    def _process_single_page(self, page_num: int, content_type: str, needs_ocr: bool) -> Dict:
        """Process a single page for text extraction"""
        
        page_start_time = time.time()
        
        # First try native text extraction
        native_text = self.pdf_processor.extract_page_text_native(page_num)
        
        if not needs_ocr and len(native_text.strip()) >= Config.MIN_TEXT_LENGTH:
            # Native text is sufficient
            processing_time = time.time() - page_start_time
            
            # Convert to markdown
            markdown_text = self.markdown_converter.text_to_markdown(native_text, page_num)
            
            return {
                'page_num': page_num,
                'text': markdown_text,
                'confidence': 100.0,  # Native text is always 100% confident
                'method': 'native_text',
                'processing_time': processing_time,
                'content_type': content_type
            }
        
        # Need OCR processing
        image = self.pdf_processor.convert_page_to_image(page_num, self.dpi)
        
        if image is None:
            return {
                'page_num': page_num,
                'text': native_text,  # Fallback to native text even if short
                'confidence': 50.0 if native_text else 0.0,
                'method': 'native_fallback',
                'processing_time': time.time() - page_start_time,
                'content_type': content_type
            }
        
        # Run comprehensive OCR
        ocr_result = self.ocr_engine.extract_text_comprehensive(
            image, 
            document_type=content_type,
            use_cache=True
        )
        
        # Choose best text (OCR vs native)
        ocr_text = ocr_result.get('text', '')
        final_text = ocr_text if len(ocr_text) > len(native_text) else native_text
        final_method = ocr_result.get('method', 'ocr') if len(ocr_text) > len(native_text) else 'native'
        
        # Handle tables if present
        if content_type == 'table':
            tables = self.pdf_processor.extract_tables_from_page(page_num)
            if tables:
                table_markdown = self.markdown_converter.process_tables_from_data(tables)
                final_text = self.markdown_converter.combine_text_and_tables(final_text, table_markdown)
        
        # Convert to markdown
        if final_text:
            final_text = self.markdown_converter.text_to_markdown(final_text, page_num)
        
        processing_time = time.time() - page_start_time
        
        return {
            'page_num': page_num,
            'text': final_text,
            'confidence': ocr_result.get('confidence', 0.0),
            'method': final_method,
            'processing_time': processing_time,
            'content_type': content_type,
            'ocr_details': ocr_result
        }
    
    def print_summary(self, result: Dict):
        """Print processing summary to console"""
        
        print("\n" + "="*60)
        print("PROCESSING SUMMARY")
        print("="*60)
        
        if result['success']:
            stats = result['statistics']
            
            print(f" Processing completed successfully")
            print(f"=Ä Total pages: {stats['total_pages']}")
            print(f" Successfully extracted: {stats['successful_extractions']}")
            print(f"=Ê Success rate: {(stats['successful_extractions']/stats['total_pages']*100):.1f}%")
            print(f"<¯ Average confidence: {stats['average_confidence']:.1f}%")
            print(f"ñ  Total processing time: {stats['total_processing_time']:.2f} seconds")
            print(f"=Á Output directory: {result['output_directory']}")
            
            print(f"\n=Ë Method distribution:")
            for method, count in stats['method_distribution'].items():
                percentage = (count / stats['total_pages']) * 100
                print(f"   {method}: {count} pages ({percentage:.1f}%)")
            
            print(f"\n=Ë Content type distribution:")
            for content_type, count in stats['content_type_distribution'].items():
                percentage = (count / stats['total_pages']) * 100
                print(f"   {content_type}: {count} pages ({percentage:.1f}%)")
            
        else:
            print(f"L Processing failed: {result['error']}")
        
        print("="*60 + "\n")

def create_argument_parser() -> argparse.ArgumentParser:
    """Create command line argument parser"""
    
    parser = argparse.ArgumentParser(
        description="SmartPDF-OCR: Intelligent PDF Text Extraction System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s document.pdf
  %(prog)s document.pdf --output ./extracted --language rus+eng
  %(prog)s document.pdf --dpi 600 --workers 8
        """
    )
    
    parser.add_argument(
        'pdf_path',
        help='Path to the PDF file to process'
    )
    
    parser.add_argument(
        '--output', '-o',
        default=Config.OUTPUT_DIR,
        help=f'Output directory (default: {Config.OUTPUT_DIR})'
    )
    
    parser.add_argument(
        '--language', '-l',
        default=Config.TESSERACT_LANG,
        help=f'OCR language(s) (default: {Config.TESSERACT_LANG})'
    )
    
    parser.add_argument(
        '--dpi',
        type=int,
        default=Config.PDF_DPI,
        help=f'DPI for PDF to image conversion (default: {Config.PDF_DPI})'
    )
    
    parser.add_argument(
        '--workers',
        type=int,
        default=Config.MAX_WORKERS,
        help=f'Number of parallel workers (default: {Config.MAX_WORKERS})'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='SmartPDF-OCR 1.0.0'
    )
    
    return parser

def main():
    """Main entry point"""
    
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Initialize and run the processor
    processor = SmartPDFOCR(
        pdf_path=args.pdf_path,
        output_dir=args.output,
        language=args.language,
        dpi=args.dpi,
        max_workers=args.workers
    )
    
    # Validate input
    if not processor.validate_input():
        sys.exit(1)
    
    # Process the PDF
    result = processor.process_pdf()
    
    # Print summary
    processor.print_summary(result)
    
    # Exit with appropriate code
    sys.exit(0 if result['success'] else 1)

if __name__ == "__main__":
    main()