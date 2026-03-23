"""
OCR Integration for Chatbot
Provides text extraction from images and documents via Vision APIs.
Uses cloud Vision APIs (OpenAI, Gemini, Grok) - no local OCR service needed.
"""

import os
import base64
import requests
import logging
from pathlib import Path
from typing import Dict, Any, Tuple
import io

logger = logging.getLogger(__name__)


class OCRIntegration:
    """Handles OCR processing for uploaded files via Vision APIs."""

    def __init__(self):
        self.enabled = True

    @staticmethod
    def _detect_media_type(filename: str) -> str:
        ext = Path(filename).suffix.lower()
        return {
            '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
            '.gif': 'image/gif', '.webp': 'image/webp', '.bmp': 'image/bmp',
        }.get(ext, 'image/png')

    def extract_text_from_image(self, image_data: bytes, filename: str = "image.png") -> Dict[str, Any]:
        """Extract text from image using Vision APIs. Priority: OpenAI > Gemini > Grok."""
        result = {"success": False, "text": "", "confidence": 0, "language": "unknown", "method": "none"}

        base64_image = base64.b64encode(image_data).decode('utf-8')
        media_type = self._detect_media_type(filename)

        ocr_prompt = "Extract ALL text from this image. Return ONLY the extracted text, preserving layout where possible. If there's no text, return 'NO_TEXT_FOUND'."

        # Try OpenAI Vision
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            try:
                return self._ocr_openai(base64_image, media_type, filename, openai_key, ocr_prompt)
            except Exception as e:
                logger.warning(f"[OCR] OpenAI Vision failed: {e}")

        # Try Gemini Vision
        gemini_key = os.getenv("GEMINI_API_KEY_1") or os.getenv("GEMINI_API_KEY_2")
        if gemini_key:
            try:
                return self._ocr_gemini(base64_image, media_type, filename, gemini_key, ocr_prompt)
            except Exception as e:
                logger.warning(f"[OCR] Gemini Vision failed: {e}")

        # Try Grok Vision
        grok_key = os.getenv("GROK_API_KEY")
        if grok_key:
            try:
                return self._ocr_grok(base64_image, media_type, filename, grok_key, ocr_prompt)
            except Exception as e:
                logger.warning(f"[OCR] Grok Vision failed: {e}")

        result["error"] = "No Vision API key available for OCR"
        return result

    def _ocr_openai(self, base64_image: str, media_type: str, filename: str, api_key: str, prompt: str) -> Dict[str, Any]:
        """OCR via OpenAI Vision API (gpt-4o-mini)."""
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{base64_image}"}}
                ]}],
                "max_tokens": 4000
            },
            timeout=30
        )
        response.raise_for_status()
        text = response.json()["choices"][0]["message"]["content"].strip()
        if text and text != "NO_TEXT_FOUND":
            logger.info(f"[OCR] OpenAI extracted {len(text)} chars from {filename}")
            return {"success": True, "text": text, "confidence": 0.9, "language": "auto", "method": "openai_vision"}
        return {"success": False, "text": "", "confidence": 0, "language": "unknown", "method": "openai_vision"}

    def _ocr_gemini(self, base64_image: str, media_type: str, filename: str, api_key: str, prompt: str) -> Dict[str, Any]:
        """OCR via Gemini Vision API."""
        response = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}",
            headers={"Content-Type": "application/json"},
            json={"contents": [{"parts": [
                {"text": prompt},
                {"inline_data": {"mime_type": media_type, "data": base64_image}}
            ]}]},
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        if text and text != "NO_TEXT_FOUND":
            logger.info(f"[OCR] Gemini extracted {len(text)} chars from {filename}")
            return {"success": True, "text": text, "confidence": 0.88, "language": "auto", "method": "gemini_vision"}
        return {"success": False, "text": "", "confidence": 0, "language": "unknown", "method": "gemini_vision"}

    def _ocr_grok(self, base64_image: str, media_type: str, filename: str, api_key: str, prompt: str) -> Dict[str, Any]:
        """OCR via Grok/xAI Vision API (grok-4)."""
        response = requests.post(
            "https://api.x.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": "grok-4-1-fast-non-reasoning",
                "messages": [{"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{base64_image}"}}
                ]}],
                "max_tokens": 4000
            },
            timeout=30
        )
        response.raise_for_status()
        text = response.json()["choices"][0]["message"]["content"].strip()
        if text and text != "NO_TEXT_FOUND":
            logger.info(f"[OCR] Grok extracted {len(text)} chars from {filename}")
            return {"success": True, "text": text, "confidence": 0.85, "language": "auto", "method": "grok_vision"}
        return {"success": False, "text": "", "confidence": 0, "language": "unknown", "method": "grok_vision"}

    def extract_text_from_pdf(self, pdf_data: bytes, filename: str = "document.pdf") -> Dict[str, Any]:
        """Extract text from PDF using PyPDF2."""
        result = {"success": False, "text": "", "pages": 0, "method": "none"}
        try:
            import PyPDF2
            reader = PyPDF2.PdfReader(io.BytesIO(pdf_data))
            text_parts = [page.extract_text() or "" for page in reader.pages]
            result["success"] = True
            result["text"] = "\n\n".join(text_parts)
            result["pages"] = len(reader.pages)
            result["method"] = "pypdf2"
            logger.info(f"[OCR] Extracted {len(result['text'])} chars from {filename}")
        except Exception as e:
            logger.error(f"[OCR] PDF extraction failed: {e}")
        return result

    def process_file(self, file_data: bytes, filename: str, content_type: str = None) -> Dict[str, Any]:
        """Process any file and extract text."""
        ext = Path(filename).suffix.lower()

        if ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.tiff']:
            return self.extract_text_from_image(file_data, filename)
        if ext == '.pdf':
            return self.extract_text_from_pdf(file_data, filename)
        if ext in ['.txt', '.md', '.py', '.js', '.ts', '.html', '.css', '.json', '.xml',
                   '.csv', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.log', '.sql', '.sh', '.bat']:
            try:
                text = file_data.decode('utf-8')
            except UnicodeDecodeError:
                text = file_data.decode('latin-1', errors='replace')
            return {"success": True, "text": text, "method": "direct_read", "file_type": ext[1:]}
        if ext in ['.docx', '.doc']:
            return self._extract_from_docx(file_data, filename)
        if ext in ['.xlsx', '.xls']:
            return self._extract_from_excel(file_data, filename)
        return {"success": False, "text": "", "error": f"Unsupported file type: {ext}"}

    def _extract_from_docx(self, file_data: bytes, filename: str) -> Dict[str, Any]:
        """Extract text from Word documents."""
        try:
            from docx import Document
            doc = Document(io.BytesIO(file_data))
            text_parts = [para.text for para in doc.paragraphs]
            for table in doc.tables:
                for row in table.rows:
                    text_parts.append(" | ".join(cell.text for cell in row.cells))
            return {"success": True, "text": "\n".join(text_parts), "method": "python_docx", "file_type": "docx"}
        except Exception as e:
            logger.error(f"[OCR] DOCX extraction failed: {e}")
            return {"success": False, "text": "", "error": str(e)}

    def _extract_from_excel(self, file_data: bytes, filename: str) -> Dict[str, Any]:
        """Extract text from Excel files."""
        try:
            import pandas as pd
            xlsx = pd.ExcelFile(io.BytesIO(file_data))
            text_parts = []
            for sheet_name in xlsx.sheet_names:
                df = pd.read_excel(xlsx, sheet_name=sheet_name)
                text_parts.append(f"=== Sheet: {sheet_name} ===")
                text_parts.append(df.to_string())
            return {"success": True, "text": "\n\n".join(text_parts), "method": "pandas",
                    "file_type": "xlsx", "sheets": xlsx.sheet_names}
        except Exception as e:
            logger.error(f"[OCR] Excel extraction failed: {e}")
            return {"success": False, "text": "", "error": str(e)}


# Global instance
ocr_client = OCRIntegration()


def extract_file_content(file_data: bytes, filename: str) -> Tuple[bool, str]:
    """Convenience function to extract content from file."""
    result = ocr_client.process_file(file_data, filename)
    return result.get("success", False), result.get("text", "")
