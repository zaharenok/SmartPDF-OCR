import os
import shutil
from pathlib import Path
from typing import Optional, Dict, Any

class OutputManager:
    """
    Manages the output directory structure for PDF processing and AI transformations.
    
    Provides a clean, organized approach to storing processed files:
    - Separate directories for different processing stages
    - Clear naming conventions
    - Automatic cleanup and management
    """
    
    def __init__(self, base_output_dir: str = 'output'):
        """
        Initialize output directories with a structured approach.
        
        Args:
            base_output_dir (str): Base directory for all output files
        """
        self.base_dir = Path(base_output_dir)
        self.dirs = {
            'base': self.base_dir,
            'ocr': self.base_dir / 'ocr',
            'ai_processed': self.base_dir / 'ai_processed',
            'markdown': self.base_dir / 'markdown',
            'pages': self.base_dir / 'pages',
            'images': self.base_dir / 'images'
        }
        
        # Create all necessary directories
        for dir_path in self.dirs.values():
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def create_document_output_structure(self, document_name: str) -> Dict[str, Path]:
        """
        Create a structured output directory for a specific document.
        
        Args:
            document_name (str): Name of the document being processed
        
        Returns:
            Dict with paths to different output subdirectories
        """
        doc_base = self.base_dir / document_name
        doc_dirs = {
            'base': doc_base,
            'ocr': doc_base / 'ocr',
            'ai_processed': doc_base / 'ai_processed',
            'markdown': doc_base / 'markdown',
            'pages': doc_base / 'pages',
            'images': doc_base / 'images'
        }
        
        # Create all document-specific directories
        for dir_path in doc_dirs.values():
            dir_path.mkdir(parents=True, exist_ok=True)
        
        return doc_dirs
    
    def save_page(self, 
                  content: str, 
                  document_name: str, 
                  page_number: int, 
                  processing_type: str = 'ocr') -> Path:
        """
        Save a processed page to the appropriate directory.
        
        Args:
            content (str): Text content of the page
            document_name (str): Name of the document
            page_number (int): Page number
            processing_type (str): Type of processing (ocr, ai_processed)
        
        Returns:
            Path to the saved page file
        """
        doc_dirs = self.create_document_output_structure(document_name)
        
        # Choose the right directory based on processing type
        if processing_type == 'ai_processed':
            output_dir = doc_dirs['ai_processed']
        else:
            output_dir = doc_dirs['ocr']
        
        # Create filename with zero-padded page number
        filename = f'page_{page_number:04d}.txt'
        file_path = output_dir / filename
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return file_path
    
    def save_markdown(self, 
                      content: str, 
                      document_name: str, 
                      ai_processed: bool = False) -> Path:
        """
        Save Markdown output with optional AI processing indicator.
        
        Args:
            content (str): Markdown content
            document_name (str): Name of the document
            ai_processed (bool): Whether the content is AI-processed
        
        Returns:
            Path to the saved Markdown file
        """
        doc_dirs = self.create_document_output_structure(document_name)
        markdown_dir = doc_dirs['markdown']
        
        # Create filename with timestamp and AI indicator
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        prefix = "ai_" if ai_processed else "v2_"
        filename = f'{prefix}complete_document_{timestamp}.md'
        file_path = markdown_dir / filename
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return file_path
    
    def cleanup(self, 
                document_name: Optional[str] = None, 
                keep_days: int = 7) -> None:
        """
        Clean up old output files and directories.
        
        Args:
            document_name (Optional[str]): Specific document to clean
            keep_days (int): Number of days to keep files
        """
        import time
        current_time = time.time()
        
        if document_name:
            doc_base = self.base_dir / document_name
            if doc_base.exists():
                self._remove_old_files(doc_base, current_time, keep_days)
        else:
            # Clean entire output directory
            for item in self.base_dir.iterdir():
                if item.is_dir():
                    self._remove_old_files(item, current_time, keep_days)
    
    def _remove_old_files(self, path: Path, current_time: float, keep_days: int) -> None:
        """
        Remove files older than specified number of days.
        
        Args:
            path (Path): Directory to clean
            current_time (float): Current timestamp
            keep_days (int): Number of days to keep files
        """
        for item in path.iterdir():
            if item.is_file():
                file_age = current_time - item.stat().st_mtime
                if file_age > (keep_days * 86400):  # 86400 seconds in a day
                    item.unlink()
            elif item.is_dir():
                self._remove_old_files(item, current_time, keep_days)
                
                # Remove empty directories
                try:
                    item.rmdir()
                except OSError:
                    pass  # Directory not empty or other error

# Example usage
if __name__ == "__main__":
    output_manager = OutputManager()
    output_manager.save_page("Sample page content", "example_document", 1)
    output_manager.save_markdown("# Markdown Content", "example_document")
    output_manager.cleanup()