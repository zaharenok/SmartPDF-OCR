import os
import json
from pathlib import Path
from typing import List, Dict, Optional
import logging
from datetime import datetime

from config import Config
from utils import setup_logging, format_progress
from markdown_converter import MarkdownConverter

class PageMerger:
    def __init__(self, output_structure: Dict[str, str]):
        self.output_structure = output_structure
        self.logger = setup_logging()
        self.markdown_converter = MarkdownConverter()
    
    def merge_pages_to_document(
        self, 
        pages_data: List[Dict], 
        pdf_metadata: Dict = None
    ) -> Dict[str, str]:
        """Merge all processed pages into final documents"""
        
        self.logger.info(f"Merging {len(pages_data)} pages into final document")
        
        # Sort pages by page number
        pages_data.sort(key=lambda x: x.get('page_num', 0))
        
        # Create different output formats
        outputs = {}
        
        # 1. Full markdown document
        outputs['full_markdown'] = self._create_full_markdown(pages_data, pdf_metadata)
        
        # 2. Text-only version (for LLM processing)
        outputs['text_only'] = self._create_text_only(pages_data)
        
        # 3. Structured JSON
        outputs['structured_json'] = self._create_structured_json(pages_data, pdf_metadata)
        
        # 4. Summary document
        outputs['summary'] = self._create_summary(pages_data, pdf_metadata)
        
        # Save all outputs
        self._save_outputs(outputs)
        
        return outputs
    
    def _create_full_markdown(self, pages_data: List[Dict], pdf_metadata: Dict = None) -> str:
        """Create comprehensive markdown document"""
        
        document_parts = []
        
        # Document header
        document_parts.append(self._create_document_header(pdf_metadata))
        
        # Table of contents
        document_parts.append(self.markdown_converter.create_table_of_contents(pages_data))
        
        # Processing summary
        document_parts.append(self._create_processing_summary(pages_data))
        
        # Main content
        for page_data in pages_data:
            page_content = self._format_page_content(page_data)
            if page_content.strip():
                document_parts.append(page_content)
        
        # Document footer
        document_parts.append(self._create_document_footer(pages_data))
        
        return '\n\n'.join(document_parts)
    
    def _create_text_only(self, pages_data: List[Dict]) -> str:
        """Create text-only version optimized for LLM processing"""
        
        text_parts = []
        
        for page_data in pages_data:
            page_num = page_data.get('page_num', 0)
            text = page_data.get('text', '')
            
            if text and text.strip():
                # Simple page separator for LLM
                text_parts.append(f"--- Страница {page_num + 1} ---")
                text_parts.append(text.strip())
                text_parts.append("")  # Blank line
        
        return '\n'.join(text_parts)
    
    def _create_structured_json(self, pages_data: List[Dict], pdf_metadata: Dict = None) -> str:
        """Create structured JSON representation"""
        
        structured_data = {
            'metadata': pdf_metadata or {},
            'processing_info': {
                'total_pages': len(pages_data),
                'processing_date': datetime.now().isoformat(),
                'successful_pages': len([p for p in pages_data if p.get('text', '').strip()]),
                'average_confidence': self._calculate_average_confidence(pages_data)
            },
            'pages': []
        }
        
        for page_data in pages_data:
            page_info = {
                'page_number': page_data.get('page_num', 0) + 1,
                'content_type': page_data.get('content_type', 'unknown'),
                'extraction_method': page_data.get('method', 'unknown'),
                'confidence': page_data.get('confidence', 0.0),
                'text_length': len(page_data.get('text', '')),
                'has_tables': page_data.get('has_tables', False),
                'table_count': page_data.get('table_count', 0),
                'text': page_data.get('text', ''),
                'processing_time': page_data.get('processing_time', 0.0)
            }
            structured_data['pages'].append(page_info)
        
        return json.dumps(structured_data, ensure_ascii=False, indent=2)
    
    def _create_summary(self, pages_data: List[Dict], pdf_metadata: Dict = None) -> str:
        """Create processing summary document"""
        
        summary_parts = []
        
        # Title
        summary_parts.append("# Отчет об обработке PDF")
        summary_parts.append("")
        
        # Basic statistics
        total_pages = len(pages_data)
        successful_pages = len([p for p in pages_data if p.get('text', '').strip()])
        avg_confidence = self._calculate_average_confidence(pages_data)
        
        summary_parts.extend([
            "## Статистика обработки",
            "",
            f"- **Всего страниц:** {total_pages}",
            f"- **Успешно обработано:** {successful_pages}",
            f"- **Процент успеха:** {(successful_pages/total_pages*100):.1f}%",
            f"- **Средняя уверенность OCR:** {avg_confidence:.1f}%",
            ""
        ])
        
        # Method statistics
        method_stats = self._calculate_method_statistics(pages_data)
        if method_stats:
            summary_parts.extend([
                "## Статистика по методам извлечения",
                ""
            ])
            for method, count in method_stats.items():
                percentage = (count / total_pages) * 100
                summary_parts.append(f"- **{method}:** {count} страниц ({percentage:.1f}%)")
            summary_parts.append("")
        
        # Content type statistics
        content_stats = self._calculate_content_statistics(pages_data)
        if content_stats:
            summary_parts.extend([
                "## Статистика по типам контента",
                ""
            ])
            for content_type, count in content_stats.items():
                percentage = (count / total_pages) * 100
                summary_parts.append(f"- **{content_type}:** {count} страниц ({percentage:.1f}%)")
            summary_parts.append("")
        
        # Problem pages
        problem_pages = [
            p for p in pages_data 
            if p.get('confidence', 0) < Config.OCR_CONFIDENCE_THRESHOLD or 
               not p.get('text', '').strip()
        ]
        
        if problem_pages:
            summary_parts.extend([
                "## Проблемные страницы",
                "",
                "Страницы с низким качеством распознавания или без текста:",
                ""
            ])
            
            for page in problem_pages:
                page_num = page.get('page_num', 0) + 1
                confidence = page.get('confidence', 0)
                method = page.get('method', 'unknown')
                summary_parts.append(
                    f"- **Страница {page_num}:** {confidence:.1f}% уверенности ({method})"
                )
            summary_parts.append("")
        
        # Processing time
        total_time = sum(p.get('processing_time', 0) for p in pages_data)
        avg_time = total_time / len(pages_data) if pages_data else 0
        
        summary_parts.extend([
            "## Производительность",
            "",
            f"- **Общее время обработки:** {total_time:.2f} сек",
            f"- **Среднее время на страницу:** {avg_time:.2f} сек",
            ""
        ])
        
        return '\n'.join(summary_parts)
    
    def _create_document_header(self, pdf_metadata: Dict = None) -> str:
        """Create document header with metadata"""
        
        header_parts = []
        
        if pdf_metadata:
            title = pdf_metadata.get('title', 'Untitled Document')
            if not title or title.strip() == '':
                title = Path(pdf_metadata.get('file_name', 'document.pdf')).stem
            
            header_parts.extend([
                f"# {title}",
                "",
                "## Информация о документе",
                ""
            ])
            
            if pdf_metadata.get('author'):
                header_parts.append(f"**Автор:** {pdf_metadata['author']}")
            
            if pdf_metadata.get('subject'):
                header_parts.append(f"**Тема:** {pdf_metadata['subject']}")
            
            header_parts.extend([
                f"**Страниц:** {pdf_metadata.get('pages', 0)}",
                f"**Размер файла:** {pdf_metadata.get('file_size', 0):,} байт",
                f"**Дата обработки:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                ""
            ])
        else:
            header_parts.extend([
                "# Извлеченный документ",
                "",
                f"**Дата обработки:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                ""
            ])
        
        return '\n'.join(header_parts)
    
    def _create_processing_summary(self, pages_data: List[Dict]) -> str:
        """Create processing summary section"""
        
        total_pages = len(pages_data)
        avg_confidence = self._calculate_average_confidence(pages_data)
        
        summary_parts = [
            "## Сводка обработки",
            "",
            f"- Всего страниц обработано: {total_pages}",
            f"- Средняя уверенность OCR: {avg_confidence:.1f}%",
            f"- Дата обработки: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            ""
        ]
        
        return '\n'.join(summary_parts)
    
    def _format_page_content(self, page_data: Dict) -> str:
        """Format content for a single page"""
        
        page_num = page_data.get('page_num', 0)
        text = page_data.get('text', '')
        confidence = page_data.get('confidence', 0)
        method = page_data.get('method', 'unknown')
        content_type = page_data.get('content_type', 'unknown')
        
        if not text or not text.strip():
            return f"## Страница {page_num + 1}\n\n*Текст не обнаружен или не извлечен*\n"
        
        # Add page metadata
        content_parts = [
            f"## Страница {page_num + 1}",
            "",
            f"*Метод извлечения: {method} | Уверенность: {confidence:.1f}% | Тип: {content_type}*",
            "",
            text,
            ""
        ]
        
        return '\n'.join(content_parts)
    
    def _create_document_footer(self, pages_data: List[Dict]) -> str:
        """Create document footer"""
        
        total_time = sum(p.get('processing_time', 0) for p in pages_data)
        
        footer_parts = [
            "---",
            "",
            "## Информация о генерации",
            "",
            f"Документ создан автоматически системой SmartPDF-OCR",
            f"Время обработки: {total_time:.2f} секунд",
            f"Дата создания: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            ""
        ]
        
        return '\n'.join(footer_parts)
    
    def _calculate_average_confidence(self, pages_data: List[Dict]) -> float:
        """Calculate average confidence across all pages"""
        
        confidences = [p.get('confidence', 0) for p in pages_data if p.get('confidence', 0) > 0]
        return sum(confidences) / len(confidences) if confidences else 0.0
    
    def _calculate_method_statistics(self, pages_data: List[Dict]) -> Dict[str, int]:
        """Calculate statistics by extraction method"""
        
        method_counts = {}
        for page in pages_data:
            method = page.get('method', 'unknown')
            method_counts[method] = method_counts.get(method, 0) + 1
        
        return method_counts
    
    def _calculate_content_statistics(self, pages_data: List[Dict]) -> Dict[str, int]:
        """Calculate statistics by content type"""
        
        content_counts = {}
        for page in pages_data:
            content_type = page.get('content_type', 'unknown')
            content_counts[content_type] = content_counts.get(content_type, 0) + 1
        
        return content_counts
    
    def _save_outputs(self, outputs: Dict[str, str]):
        """Save all output formats to files"""
        
        output_files = {
            'full_markdown': 'complete_document.md',
            'text_only': 'text_only.txt',
            'structured_json': 'structured_data.json',
            'summary': 'processing_summary.md'
        }
        
        for output_type, content in outputs.items():
            if content:
                filename = output_files.get(output_type, f'{output_type}.txt')
                output_path = os.path.join(self.output_structure['base'], filename)
                
                try:
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    self.logger.info(f"Saved {output_type} to: {output_path}")
                    
                except Exception as e:
                    self.logger.error(f"Error saving {output_type}: {e}")
    
    def create_individual_page_files(self, pages_data: List[Dict]):
        """Save individual page files for debugging/review"""
        
        for page_data in pages_data:
            page_num = page_data.get('page_num', 0)
            text = page_data.get('text', '')
            
            if text and text.strip():
                # Save as markdown
                page_content = self._format_page_content(page_data)
                page_file = os.path.join(
                    self.output_structure['markdown'], 
                    f'page_{page_num:04d}.md'
                )
                
                try:
                    with open(page_file, 'w', encoding='utf-8') as f:
                        f.write(page_content)
                except Exception as e:
                    self.logger.warning(f"Error saving page {page_num}: {e}")
                
                # Save as plain text
                text_file = os.path.join(
                    self.output_structure['text'], 
                    f'page_{page_num:04d}.txt'
                )
                
                try:
                    with open(text_file, 'w', encoding='utf-8') as f:
                        f.write(text)
                except Exception as e:
                    self.logger.warning(f"Error saving text for page {page_num}: {e}")
    
    def get_merge_statistics(self, pages_data: List[Dict]) -> Dict:
        """Get detailed merge statistics"""
        
        return {
            'total_pages': len(pages_data),
            'successful_extractions': len([p for p in pages_data if p.get('text', '').strip()]),
            'average_confidence': self._calculate_average_confidence(pages_data),
            'method_distribution': self._calculate_method_statistics(pages_data),
            'content_type_distribution': self._calculate_content_statistics(pages_data),
            'total_text_length': sum(len(p.get('text', '')) for p in pages_data),
            'processing_time': sum(p.get('processing_time', 0) for p in pages_data)
        }