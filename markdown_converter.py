import re
import markdown
from markdownify import markdownify as md
from typing import List, Dict, Optional, Tuple
import logging
from pathlib import Path

from config import Config
from utils import setup_logging, clean_text

class MarkdownConverter:
    def __init__(self):
        self.logger = setup_logging()
        
        # Markdown extensions for better formatting
        self.md_extensions = Config.MARKDOWN_EXTENSIONS
        
        # Patterns for text analysis
        self.table_pattern = re.compile(r'(\|.*\|.*\n)+', re.MULTILINE)
        self.header_pattern = re.compile(r'^([A-ZА-Я][^.\n]{10,})\s*$', re.MULTILINE)
        self.number_list_pattern = re.compile(r'^\d+\.\s+', re.MULTILINE)
        self.bullet_pattern = re.compile(r'^[•·\-\*]\s+', re.MULTILINE)
        
    def text_to_markdown(self, text: str, page_num: int = 0) -> str:
        """Convert plain text to markdown with intelligent formatting"""
        if not text or not text.strip():
            return ""
        
        # Clean the text first
        text = clean_text(text)
        
        # Split into lines for processing
        lines = text.split('\n')
        processed_lines = []
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            if not line:
                processed_lines.append('')
                i += 1
                continue
            
            # Process different types of content
            if self._is_header(line):
                processed_lines.append(self._format_header(line))
            elif self._is_list_item(line):
                # Process list and advance counter
                list_lines, advance = self._process_list(lines[i:])
                processed_lines.extend(list_lines)
                i += advance - 1  # -1 because we'll increment at the end
            elif self._is_table_line(line):
                # Process table and advance counter
                table_lines, advance = self._process_table(lines[i:])
                processed_lines.extend(table_lines)
                i += advance - 1
            else:
                # Regular paragraph
                processed_lines.append(self._format_paragraph(line))
            
            i += 1
        
        # Join and clean up
        markdown_text = '\n'.join(processed_lines)
        markdown_text = self._cleanup_markdown(markdown_text)
        
        return markdown_text
    
    def _is_header(self, line: str) -> bool:
        """Determine if line is a header"""
        # Check for common header patterns
        if len(line) < 5 or len(line) > 100:
            return False
        
        # Headers usually:
        # - Start with uppercase
        # - Don't end with periods
        # - Are not too long
        # - Don't contain many numbers
        
        if not line[0].isupper():
            return False
        
        if line.endswith('.'):
            return False
        
        # Count letters vs numbers
        letters = sum(c.isalpha() for c in line)
        numbers = sum(c.isdigit() for c in line)
        
        return letters > numbers * 3
    
    def _format_header(self, line: str) -> str:
        """Format line as markdown header"""
        # Determine header level based on length and context
        if len(line) < 20:
            level = 2
        elif len(line) < 40:
            level = 3
        else:
            level = 4
        
        return f"{'#' * level} {line}\n"
    
    def _is_list_item(self, line: str) -> bool:
        """Check if line is a list item"""
        return bool(
            self.number_list_pattern.match(line) or 
            self.bullet_pattern.match(line) or
            line.startswith('- ') or
            line.startswith('* ')
        )
    
    def _process_list(self, lines: List[str]) -> Tuple[List[str], int]:
        """Process a list and return formatted markdown lines"""
        processed = []
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            if not line:
                processed.append('')
                i += 1
                continue
            
            if not self._is_list_item(line):
                break
            
            # Format list item
            if self.number_list_pattern.match(line):
                # Numbered list
                item_text = self.number_list_pattern.sub('', line).strip()
                processed.append(f"{i+1}. {item_text}")
            else:
                # Bullet list
                item_text = self.bullet_pattern.sub('', line).strip()
                if not item_text:
                    item_text = line.strip()
                processed.append(f"- {item_text}")
            
            i += 1
        
        if processed:
            processed.append('')  # Add blank line after list
        
        return processed, i
    
    def _is_table_line(self, line: str) -> bool:
        """Check if line looks like part of a table"""
        # Simple heuristic: contains multiple separators
        separators = line.count('|') + line.count('\t')
        return separators >= 2
    
    def _process_table(self, lines: List[str]) -> Tuple[List[str], int]:
        """Process table lines and return markdown table"""
        table_lines = []
        i = 0
        
        # Collect all table lines
        while i < len(lines):
            line = lines[i].strip()
            
            if not line:
                i += 1
                continue
            
            if not self._is_table_line(line):
                break
            
            table_lines.append(line)
            i += 1
        
        if not table_lines:
            return [], 0
        
        # Convert to markdown table
        markdown_table = self._format_table(table_lines)
        
        return markdown_table, i
    
    def _format_table(self, lines: List[str]) -> List[str]:
        """Format lines as markdown table"""
        if not lines:
            return []
        
        formatted_lines = []
        
        # Process each line
        for idx, line in enumerate(lines):
            # Split by common separators
            if '|' in line:
                cells = [cell.strip() for cell in line.split('|')]
            else:
                cells = [cell.strip() for cell in line.split('\t')]
            
            # Remove empty cells at start/end
            while cells and not cells[0]:
                cells.pop(0)
            while cells and not cells[-1]:
                cells.pop()
            
            if cells:
                formatted_lines.append('| ' + ' | '.join(cells) + ' |')
                
                # Add header separator after first row
                if idx == 0:
                    separator = '| ' + ' | '.join(['---'] * len(cells)) + ' |'
                    formatted_lines.append(separator)
        
        if formatted_lines:
            formatted_lines.append('')  # Add blank line after table
        
        return formatted_lines
    
    def _format_paragraph(self, line: str) -> str:
        """Format line as regular paragraph"""
        return line + '\n'
    
    def _cleanup_markdown(self, text: str) -> str:
        """Clean up markdown formatting"""
        # Remove excessive blank lines
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Fix spacing around headers
        text = re.sub(r'\n(#{1,6})', r'\n\n\1', text)
        text = re.sub(r'(#{1,6}.*)\n([^\n#])', r'\1\n\n\2', text)
        
        # Fix table formatting
        text = re.sub(r'\n(\|.*\|)\n([^\n|])', r'\n\1\n\n\2', text)
        
        return text.strip()
    
    def process_tables_from_data(self, tables: List[List[List[str]]]) -> str:
        """Convert table data to markdown tables"""
        if not tables:
            return ""
        
        markdown_tables = []
        
        for table_idx, table in enumerate(tables):
            if not table or not table[0]:
                continue
            
            markdown_lines = [f"\n### Таблица {table_idx + 1}\n"]
            
            # Process table rows
            for row_idx, row in enumerate(table):
                if not row:
                    continue
                
                # Clean cell content
                cleaned_row = [str(cell).strip() if cell else '' for cell in row]
                
                # Create markdown row
                markdown_row = '| ' + ' | '.join(cleaned_row) + ' |'
                markdown_lines.append(markdown_row)
                
                # Add header separator after first row
                if row_idx == 0:
                    separator = '| ' + ' | '.join(['---'] * len(cleaned_row)) + ' |'
                    markdown_lines.append(separator)
            
            markdown_lines.append('')  # Add blank line after table
            markdown_tables.extend(markdown_lines)
        
        return '\n'.join(markdown_tables)
    
    def combine_text_and_tables(self, text: str, tables: str) -> str:
        """Combine extracted text and tables into cohesive markdown"""
        combined = []
        
        if text:
            combined.append(text)
        
        if tables:
            if combined:
                combined.append('\n---\n')  # Separator
            combined.append(tables)
        
        return '\n'.join(combined)
    
    def add_page_metadata(self, content: str, page_num: int, metadata: Dict = None) -> str:
        """Add page metadata to markdown content"""
        header_lines = [
            f"# Страница {page_num + 1}",
            ""
        ]
        
        if metadata:
            if metadata.get('confidence'):
                header_lines.append(f"**Качество распознавания:** {metadata['confidence']:.1f}%")
            if metadata.get('method'):
                header_lines.append(f"**Метод извлечения:** {metadata['method']}")
            if metadata.get('content_type'):
                header_lines.append(f"**Тип контента:** {metadata['content_type']}")
            
            header_lines.append("")  # Blank line before content
        
        return '\n'.join(header_lines) + content
    
    def create_table_of_contents(self, pages_data: List[Dict]) -> str:
        """Create table of contents from pages data"""
        toc_lines = [
            "# Содержание",
            ""
        ]
        
        for page_data in pages_data:
            page_num = page_data.get('page_num', 0)
            confidence = page_data.get('confidence', 0)
            content_type = page_data.get('content_type', 'unknown')
            
            toc_lines.append(
                f"- [Страница {page_num + 1}](#страница-{page_num + 1}) "
                f"({content_type}, {confidence:.1f}%)"
            )
        
        toc_lines.extend(["", "---", ""])
        return '\n'.join(toc_lines)
    
    def save_markdown(self, content: str, output_path: str) -> bool:
        """Save markdown content to file"""
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self.logger.info(f"Markdown saved to: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving markdown: {e}")
            return False