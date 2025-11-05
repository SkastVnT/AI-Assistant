"""
Advanced Features for Document Intelligence Service
New capabilities: Batch processing, Templates, History, Quick actions
"""
import logging
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import re

logger = logging.getLogger(__name__)


class BatchProcessor:
    """
    Process multiple documents at once
    """
    
    def __init__(self, ocr_processor, max_batch_size: int = 10):
        """
        Initialize batch processor
        
        Args:
            ocr_processor: OCR processor instance
            max_batch_size: Maximum files per batch
        """
        self.ocr_processor = ocr_processor
        self.max_batch_size = max_batch_size
        logger.info(f"📦 Batch Processor initialized (max: {max_batch_size})")
    
    def process_batch(self, file_paths: List[str], options: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process multiple files
        
        Args:
            file_paths: List of file paths
            options: Processing options
            
        Returns:
            Batch processing results
        """
        if len(file_paths) > self.max_batch_size:
            return {
                "success": False,
                "error": f"Batch size exceeds limit ({len(file_paths)} > {self.max_batch_size})"
            }
        
        logger.info(f"🚀 Processing batch of {len(file_paths)} files...")
        
        results = []
        success_count = 0
        error_count = 0
        
        for idx, file_path in enumerate(file_paths):
            try:
                logger.info(f"📄 Processing {idx + 1}/{len(file_paths)}: {Path(file_path).name}")
                result = self.ocr_processor.process_file(file_path, options)
                
                if result.get('success', False):
                    success_count += 1
                else:
                    error_count += 1
                
                results.append({
                    "file": Path(file_path).name,
                    "index": idx + 1,
                    "result": result
                })
                
            except Exception as e:
                logger.error(f"❌ Error processing {file_path}: {e}")
                error_count += 1
                results.append({
                    "file": Path(file_path).name,
                    "index": idx + 1,
                    "result": {
                        "success": False,
                        "error": str(e)
                    }
                })
        
        return {
            "success": True,
            "total_files": len(file_paths),
            "success_count": success_count,
            "error_count": error_count,
            "results": results,
            "processed_at": datetime.now().isoformat()
        }


class DocumentTemplates:
    """
    Predefined templates for common Vietnamese documents
    """
    
    TEMPLATES = {
        "CMND/CCCD": {
            "name": "Chứng minh nhân dân / Căn cước công dân",
            "icon": "📇",
            "fields": [
                "Họ và tên",
                "Số CMND/CCCD",
                "Ngày sinh",
                "Giới tính",
                "Nơi sinh",
                "Quê quán",
                "Địa chỉ thường trú",
                "Ngày cấp",
                "Có giá trị đến"
            ],
            "validation_rules": {
                "Số CMND/CCCD": r"^\d{9,12}$",
                "Ngày sinh": r"\d{2}/\d{2}/\d{4}"
            }
        },
        "Hóa đơn": {
            "name": "Hóa đơn VAT / Hóa đơn bán hàng",
            "icon": "🧾",
            "fields": [
                "Tên công ty",
                "Mã số thuế",
                "Số hóa đơn",
                "Ngày hóa đơn",
                "Hàng hóa/Dịch vụ",
                "Số tiền",
                "VAT (%)",
                "Tổng tiền"
            ],
            "validation_rules": {
                "Mã số thuế": r"^\d{10}(-\d{3})?$"
            }
        },
        "Hợp đồng": {
            "name": "Hợp đồng",
            "icon": "📄",
            "fields": [
                "Số hợp đồng",
                "Loại hợp đồng",
                "Bên A (tên)",
                "Bên B (tên)",
                "Ngày ký",
                "Thời hạn",
                "Giá trị hợp đồng",
                "Nội dung chính"
            ]
        },
        "Đơn từ": {
            "name": "Đơn xin nghỉ / Đơn xin việc",
            "icon": "📋",
            "fields": [
                "Loại đơn",
                "Người làm đơn",
                "Chức vụ",
                "Ngày làm đơn",
                "Lý do",
                "Thời gian (nếu có)"
            ]
        },
        "Bảng lương": {
            "name": "Phiếu lương / Bảng thanh toán",
            "icon": "💰",
            "fields": [
                "Tên nhân viên",
                "Mã nhân viên",
                "Tháng/Năm",
                "Lương cơ bản",
                "Phụ cấp",
                "Thưởng",
                "Khấu trừ",
                "Thực lĩnh"
            ]
        }
    }
    
    @classmethod
    def get_all_templates(cls) -> Dict[str, Any]:
        """Get all templates"""
        return cls.TEMPLATES
    
    @classmethod
    def get_template(cls, template_name: str) -> Optional[Dict[str, Any]]:
        """Get specific template"""
        return cls.TEMPLATES.get(template_name)
    
    @classmethod
    def match_document(cls, text: str) -> Optional[str]:
        """
        Match document to best template based on content
        
        Args:
            text: Document text
            
        Returns:
            Template name or None
        """
        text_lower = text.lower()
        
        # Simple keyword matching
        keywords = {
            "CMND/CCCD": ["căn cước", "chứng minh", "cccd", "cmnd", "số định danh"],
            "Hóa đơn": ["hóa đơn", "vat", "mã số thuế", "invoice"],
            "Hợp đồng": ["hợp đồng", "contract", "bên a", "bên b"],
            "Đơn từ": ["đơn xin", "kính gửi", "người làm đơn"],
            "Bảng lương": ["bảng lương", "phiếu lương", "thực lĩnh", "salary"]
        }
        
        for template_name, kws in keywords.items():
            if any(kw in text_lower for kw in kws):
                return template_name
        
        return None


class ProcessingHistory:
    """
    Track and manage processing history
    """
    
    def __init__(self, history_file: Path):
        """
        Initialize history tracker
        
        Args:
            history_file: Path to history JSON file
        """
        self.history_file = history_file
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        
        if not self.history_file.exists():
            self._save_history([])
        
        logger.info(f"📜 History tracker initialized: {history_file}")
    
    def add_entry(self, entry: Dict[str, Any]) -> None:
        """
        Add new processing entry
        
        Args:
            entry: Processing result
        """
        history = self._load_history()
        
        # Add metadata
        entry['id'] = len(history) + 1
        entry['timestamp'] = datetime.now().isoformat()
        
        history.append(entry)
        
        # Keep only last 100 entries
        if len(history) > 100:
            history = history[-100:]
        
        self._save_history(history)
        logger.info(f"📝 Added entry #{entry['id']} to history")
    
    def get_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent history"""
        history = self._load_history()
        return history[-limit:][::-1]  # Latest first
    
    def search_history(self, query: str) -> List[Dict[str, Any]]:
        """
        Search history by filename or content
        
        Args:
            query: Search query
            
        Returns:
            Matching entries
        """
        history = self._load_history()
        query_lower = query.lower()
        
        results = []
        for entry in history:
            # Search in filename
            filename = entry.get('filename', '').lower()
            # Search in extracted text
            text = entry.get('text', '').lower()
            
            if query_lower in filename or query_lower in text:
                results.append(entry)
        
        return results[::-1]  # Latest first
    
    def clear_history(self) -> None:
        """Clear all history"""
        self._save_history([])
        logger.info("🗑️ History cleared")
    
    def _load_history(self) -> List[Dict[str, Any]]:
        """Load history from file"""
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading history: {e}")
            return []
    
    def _save_history(self, history: List[Dict[str, Any]]) -> None:
        """Save history to file"""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving history: {e}")


class TextFormatter:
    """
    Text formatting and cleaning utilities
    """
    
    @staticmethod
    def remove_duplicates(text: str) -> str:
        """
        Remove duplicate lines
        
        Args:
            text: Input text
            
        Returns:
            Text without duplicates
        """
        lines = text.split('\n')
        seen = set()
        unique_lines = []
        
        for line in lines:
            line_stripped = line.strip()
            if line_stripped and line_stripped not in seen:
                seen.add(line_stripped)
                unique_lines.append(line)
        
        return '\n'.join(unique_lines)
    
    @staticmethod
    def fix_spacing(text: str) -> str:
        """
        Fix spacing issues (multiple spaces, extra newlines)
        
        Args:
            text: Input text
            
        Returns:
            Fixed text
        """
        # Fix multiple spaces
        text = re.sub(r' +', ' ', text)
        
        # Fix multiple newlines
        text = re.sub(r'\n\n+', '\n\n', text)
        
        # Remove trailing spaces
        lines = [line.rstrip() for line in text.split('\n')]
        
        return '\n'.join(lines)
    
    @staticmethod
    def capitalize_sentences(text: str) -> str:
        """
        Capitalize first letter of each sentence
        
        Args:
            text: Input text
            
        Returns:
            Capitalized text
        """
        sentences = re.split(r'([.!?]\s+)', text)
        result = []
        
        for i, part in enumerate(sentences):
            if i % 2 == 0 and part:  # Text parts (not punctuation)
                result.append(part[0].upper() + part[1:] if len(part) > 0 else part)
            else:
                result.append(part)
        
        return ''.join(result)
    
    @staticmethod
    def add_line_numbers(text: str) -> str:
        """
        Add line numbers to text
        
        Args:
            text: Input text
            
        Returns:
            Text with line numbers
        """
        lines = text.split('\n')
        numbered = [f"{i+1:3d} | {line}" for i, line in enumerate(lines)]
        return '\n'.join(numbered)
    
    @staticmethod
    def extract_numbers(text: str) -> List[str]:
        """
        Extract all numbers from text
        
        Args:
            text: Input text
            
        Returns:
            List of numbers found
        """
        # Match integers and decimals
        numbers = re.findall(r'\b\d+(?:[.,]\d+)*\b', text)
        return numbers
    
    @staticmethod
    def extract_dates(text: str) -> List[str]:
        """
        Extract dates from text (DD/MM/YYYY format)
        
        Args:
            text: Input text
            
        Returns:
            List of dates found
        """
        dates = re.findall(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b', text)
        return dates
    
    @staticmethod
    def extract_emails(text: str) -> List[str]:
        """
        Extract email addresses
        
        Args:
            text: Input text
            
        Returns:
            List of emails found
        """
        emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
        return emails
    
    @staticmethod
    def extract_phones(text: str) -> List[str]:
        """
        Extract Vietnamese phone numbers
        
        Args:
            text: Input text
            
        Returns:
            List of phone numbers found
        """
        # Vietnamese phone patterns: 0xxx-xxx-xxx, (+84)xxx-xxx-xxx
        phones = re.findall(r'(?:\+84|0)(?:\d{9,10}|\d{3}[-.\s]?\d{3}[-.\s]?\d{3,4})', text)
        return phones


class QuickActions:
    """
    Quick actions for common tasks
    """
    
    def __init__(self):
        """Initialize quick actions"""
        self.formatter = TextFormatter()
        logger.info("⚡ Quick Actions initialized")
    
    def clean_text(self, text: str) -> Dict[str, Any]:
        """
        Apply multiple cleaning operations
        
        Args:
            text: Input text
            
        Returns:
            Cleaned text and stats
        """
        original_length = len(text)
        original_lines = len(text.split('\n'))
        
        # Apply cleaners
        text = self.formatter.remove_duplicates(text)
        text = self.formatter.fix_spacing(text)
        
        cleaned_length = len(text)
        cleaned_lines = len(text.split('\n'))
        
        return {
            "success": True,
            "text": text,
            "stats": {
                "original_length": original_length,
                "cleaned_length": cleaned_length,
                "saved_chars": original_length - cleaned_length,
                "original_lines": original_lines,
                "cleaned_lines": cleaned_lines,
                "removed_lines": original_lines - cleaned_lines
            }
        }
    
    def extract_info(self, text: str) -> Dict[str, Any]:
        """
        Extract key information (numbers, dates, emails, phones)
        
        Args:
            text: Input text
            
        Returns:
            Extracted information
        """
        return {
            "success": True,
            "numbers": self.formatter.extract_numbers(text),
            "dates": self.formatter.extract_dates(text),
            "emails": self.formatter.extract_emails(text),
            "phones": self.formatter.extract_phones(text)
        }
    
    def format_text(self, text: str, action: str) -> Dict[str, Any]:
        """
        Apply specific formatting
        
        Args:
            text: Input text
            action: Format action (capitalize, line_numbers, etc.)
            
        Returns:
            Formatted text
        """
        actions = {
            "capitalize": self.formatter.capitalize_sentences,
            "line_numbers": self.formatter.add_line_numbers,
            "remove_duplicates": self.formatter.remove_duplicates,
            "fix_spacing": self.formatter.fix_spacing
        }
        
        if action not in actions:
            return {
                "success": False,
                "error": f"Unknown action: {action}"
            }
        
        formatted_text = actions[action](text)
        
        return {
            "success": True,
            "text": formatted_text,
            "action": action
        }

