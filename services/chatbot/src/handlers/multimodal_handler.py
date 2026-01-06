"""
Multimodal AI Handler - Vision + Text + Audio Integration
Supports: Image analysis, Document OCR, Audio transcription, Combined analysis
"""

import os
import base64
import requests
import logging
from typing import Dict, List, Optional, Union, Tuple
from pathlib import Path
import mimetypes
from PIL import Image
import io

from google import genai
from openai import OpenAI

logger = logging.getLogger(__name__)


class MultimodalHandler:
    """
    Advanced multimodal AI handler supporting vision, audio, and text
    
    Features:
    - Image analysis with Gemini 2.0 Flash Vision
    - Document OCR with PaddleOCR integration
    - Audio transcription with Speech2Text service
    - Combined multimodal analysis
    - Context-aware responses
    """
    
    def __init__(
        self,
        gemini_api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        speech2text_url: Optional[str] = None,
        document_intelligence_url: Optional[str] = None
    ):
        """
        Initialize multimodal handler
        
        Args:
            gemini_api_key: Gemini API key for vision
            openai_api_key: OpenAI API key for GPT-4 Vision
            speech2text_url: URL to Speech2Text service
            document_intelligence_url: URL to Document Intelligence service
        """
        self.gemini_api_key = gemini_api_key or os.getenv('GEMINI_API_KEY')
        self.openai_api_key = openai_api_key or os.getenv('OPENAI_API_KEY')
        self.speech2text_url = speech2text_url or os.getenv(
            'SPEECH2TEXT_URL', 
            'http://localhost:5002'
        )
        self.document_intelligence_url = document_intelligence_url or os.getenv(
            'DOCUMENT_INTELLIGENCE_URL',
            'http://localhost:5003'
        )
        
        # Initialize clients
        if self.gemini_api_key:
            self.gemini_client = genai.Client(api_key=self.gemini_api_key)
            logger.info("✅ Gemini Vision initialized")
        else:
            self.gemini_client = None
            logger.warning("⚠️ Gemini API key not found")
        
        if self.openai_api_key:
            self.openai_client = OpenAI(api_key=self.openai_api_key)
            logger.info("✅ OpenAI Vision initialized")
        else:
            self.openai_client = None
            logger.warning("⚠️ OpenAI API key not found")
    
    # =========================================================================
    # IMAGE ANALYSIS
    # =========================================================================
    
    def analyze_image(
        self,
        image_path: str,
        prompt: str = "Analyze this image in detail",
        model: str = "gemini",
        language: str = "vi"
    ) -> Dict:
        """
        Analyze image with vision AI
        
        Args:
            image_path: Path to image file
            prompt: Analysis prompt
            model: 'gemini' or 'gpt4-vision'
            language: Response language ('vi' or 'en')
        
        Returns:
            {
                'analysis': str,
                'objects_detected': List[str],
                'scene_description': str,
                'text_detected': str,
                'model_used': str,
                'processing_time': float
            }
        """
        import time
        start_time = time.time()
        
        try:
            if model == "gemini" and self.gemini_client:
                result = self._analyze_with_gemini(image_path, prompt, language)
            elif model == "gpt4-vision" and self.openai_client:
                result = self._analyze_with_gpt4_vision(image_path, prompt, language)
            else:
                return {
                    'error': f"Model {model} not available",
                    'available_models': self._get_available_models()
                }
            
            result['processing_time'] = time.time() - start_time
            return result
            
        except Exception as e:
            logger.error(f"Image analysis failed: {e}")
            return {
                'error': str(e),
                'processing_time': time.time() - start_time
            }
    
    def _analyze_with_gemini(
        self,
        image_path: str,
        prompt: str,
        language: str = "vi"
    ) -> Dict:
        """Analyze image with Gemini Vision"""
        
        # Load image
        image = Image.open(image_path)
        
        # Create enhanced prompt
        lang_instruction = "Trả lời bằng tiếng Việt." if language == "vi" else "Answer in English."
        enhanced_prompt = f"""
{prompt}

{lang_instruction}

Hãy phân tích chi tiết:
1. Mô tả tổng quan về hình ảnh
2. Các đối tượng chính trong ảnh
3. Màu sắc và bố cục
4. Văn bản nếu có (OCR)
5. Cảm xúc và không khí
6. Ngữ cảnh và bối cảnh

Trả về JSON format:
{{
    "analysis": "Phân tích chi tiết",
    "objects_detected": ["object1", "object2"],
    "scene_description": "Mô tả cảnh",
    "text_detected": "Văn bản trong ảnh",
    "colors": ["color1", "color2"],
    "mood": "Cảm xúc chung"
}}
"""
        
        # Call GROK Vision
        response = self.gemini_client.models.generate_content(
            model='grok-3',
            contents=[enhanced_prompt, image]
        )
        
        # Parse response
        try:
            import json
            result = json.loads(response.text)
        except:
            # Fallback if not JSON
            result = {
                'analysis': response.text,
                'objects_detected': [],
                'scene_description': response.text[:200],
                'text_detected': '',
                'colors': [],
                'mood': ''
            }
        
        result['model_used'] = 'grok-3'
        result['raw_response'] = response.text
        
        return result
    
    def _analyze_with_gpt4_vision(
        self,
        image_path: str,
        prompt: str,
        language: str = "vi"
    ) -> Dict:
        """Analyze image with GPT-4 Vision"""
        
        # Encode image to base64
        with open(image_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')
        
        # Create prompt
        lang_instruction = "Respond in Vietnamese." if language == "vi" else "Respond in English."
        enhanced_prompt = f"{prompt}\n\n{lang_instruction}"
        
        # Call GPT-4 Vision
        response = self.openai_client.chat.completions.create(
            model="gpt-4-vision-preview",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": enhanced_prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=1000
        )
        
        analysis = response.choices[0].message.content
        
        return {
            'analysis': analysis,
            'objects_detected': [],  # GPT-4V doesn't return structured data by default
            'scene_description': analysis[:200],
            'text_detected': '',
            'model_used': 'gpt-4-vision-preview',
            'raw_response': analysis
        }
    
    # =========================================================================
    # DOCUMENT OCR
    # =========================================================================
    
    def analyze_document(
        self,
        document_path: str,
        analysis_type: str = "full",
        language: str = "vi"
    ) -> Dict:
        """
        Analyze document with OCR and AI
        
        Args:
            document_path: Path to document (PDF, image)
            analysis_type: 'ocr', 'classify', 'extract', 'full'
            language: Document language
        
        Returns:
            {
                'text': str,
                'classification': str,
                'entities': Dict,
                'summary': str,
                'processing_time': float
            }
        """
        import time
        start_time = time.time()
        
        try:
            # Call Document Intelligence service
            with open(document_path, 'rb') as f:
                files = {'file': f}
                data = {
                    'analysis_type': analysis_type,
                    'language': language
                }
                
                response = requests.post(
                    f"{self.document_intelligence_url}/api/analyze",
                    files=files,
                    data=data,
                    timeout=120
                )
            
            if response.status_code == 200:
                result = response.json()
                result['processing_time'] = time.time() - start_time
                return result
            else:
                return {
                    'error': f"Document Intelligence service error: {response.status_code}",
                    'processing_time': time.time() - start_time
                }
                
        except requests.exceptions.ConnectionError:
            logger.warning("Document Intelligence service not available, using fallback")
            # Fallback: Use Gemini Vision for document analysis
            return self.analyze_image(
                document_path,
                prompt=f"Extract and analyze all text from this document. Type: {analysis_type}",
                language=language
            )
        except Exception as e:
            logger.error(f"Document analysis failed: {e}")
            return {
                'error': str(e),
                'processing_time': time.time() - start_time
            }
    
    # =========================================================================
    # AUDIO TRANSCRIPTION
    # =========================================================================
    
    def transcribe_audio(
        self,
        audio_path: str,
        model: str = "smart",
        enable_diarization: bool = True,
        language: str = "vi"
    ) -> Dict:
        """
        Transcribe audio with Speech2Text service
        
        Args:
            audio_path: Path to audio file
            model: 'smart' (dual model), 'fast', 'whisper', 'phowhisper'
            enable_diarization: Enable speaker detection
            language: Audio language
        
        Returns:
            {
                'transcript': str,
                'timeline': List[Dict],
                'speakers': int,
                'duration': float,
                'processing_time': float
            }
        """
        import time
        start_time = time.time()
        
        try:
            # Upload audio to Speech2Text service
            with open(audio_path, 'rb') as f:
                files = {'file': f}
                
                response = requests.post(
                    f"{self.speech2text_url}/upload",
                    files=files,
                    timeout=30
                )
            
            if response.status_code != 200:
                return {
                    'error': f"Upload failed: {response.status_code}",
                    'processing_time': time.time() - start_time
                }
            
            file_id = response.json().get('file_id')
            
            # Start transcription
            response = requests.post(
                f"{self.speech2text_url}/transcribe",
                json={
                    'file_id': file_id,
                    'model': model,
                    'language': language,
                    'enable_diarization': enable_diarization
                },
                timeout=30
            )
            
            if response.status_code != 200:
                return {
                    'error': f"Transcription failed: {response.status_code}",
                    'processing_time': time.time() - start_time
                }
            
            job_id = response.json().get('job_id')
            
            # Poll for results (max 10 minutes)
            max_wait = 600
            poll_interval = 2
            elapsed = 0
            
            while elapsed < max_wait:
                response = requests.get(
                    f"{self.speech2text_url}/status/{job_id}",
                    timeout=10
                )
                
                if response.status_code == 200:
                    status = response.json()
                    
                    if status.get('status') == 'completed':
                        result = status.get('result', {})
                        result['processing_time'] = time.time() - start_time
                        return result
                    
                    elif status.get('status') == 'failed':
                        return {
                            'error': status.get('error', 'Transcription failed'),
                            'processing_time': time.time() - start_time
                        }
                
                time.sleep(poll_interval)
                elapsed += poll_interval
            
            return {
                'error': 'Transcription timeout',
                'processing_time': time.time() - start_time
            }
            
        except requests.exceptions.ConnectionError:
            return {
                'error': 'Speech2Text service not available',
                'processing_time': time.time() - start_time
            }
        except Exception as e:
            logger.error(f"Audio transcription failed: {e}")
            return {
                'error': str(e),
                'processing_time': time.time() - start_time
            }
    
    # =========================================================================
    # MULTIMODAL COMBINED ANALYSIS
    # =========================================================================
    
    def analyze_multimodal(
        self,
        inputs: List[Dict],
        query: str,
        language: str = "vi"
    ) -> Dict:
        """
        Combined multimodal analysis
        
        Args:
            inputs: List of input dictionaries:
                [
                    {'type': 'image', 'path': 'path/to/image.jpg'},
                    {'type': 'audio', 'path': 'path/to/audio.mp3'},
                    {'type': 'document', 'path': 'path/to/doc.pdf'},
                    {'type': 'text', 'content': 'Some text'}
                ]
            query: User's question about the inputs
            language: Response language
        
        Returns:
            {
                'response': str,
                'sources_analyzed': List[str],
                'combined_insights': str,
                'processing_time': float
            }
        """
        import time
        start_time = time.time()
        
        try:
            # Process each input
            processed_inputs = []
            
            for input_item in inputs:
                input_type = input_item.get('type')
                
                if input_type == 'image':
                    result = self.analyze_image(
                        input_item['path'],
                        prompt=query,
                        language=language
                    )
                    processed_inputs.append({
                        'type': 'image',
                        'result': result
                    })
                
                elif input_type == 'audio':
                    result = self.transcribe_audio(
                        input_item['path'],
                        language=language
                    )
                    processed_inputs.append({
                        'type': 'audio',
                        'result': result
                    })
                
                elif input_type == 'document':
                    result = self.analyze_document(
                        input_item['path'],
                        language=language
                    )
                    processed_inputs.append({
                        'type': 'document',
                        'result': result
                    })
                
                elif input_type == 'text':
                    processed_inputs.append({
                        'type': 'text',
                        'content': input_item['content']
                    })
            
            # Combine insights with AI
            combined_response = self._combine_multimodal_insights(
                processed_inputs,
                query,
                language
            )
            
            combined_response['processing_time'] = time.time() - start_time
            return combined_response
            
        except Exception as e:
            logger.error(f"Multimodal analysis failed: {e}")
            return {
                'error': str(e),
                'processing_time': time.time() - start_time
            }
    
    def _combine_multimodal_insights(
        self,
        processed_inputs: List[Dict],
        query: str,
        language: str = "vi"
    ) -> Dict:
        """Combine insights from multiple modalities"""
        
        # Build context from all inputs
        context_parts = []
        sources = []
        
        for item in processed_inputs:
            if item['type'] == 'image':
                analysis = item['result'].get('analysis', '')
                context_parts.append(f"[IMAGE ANALYSIS]: {analysis}")
                sources.append('image')
            
            elif item['type'] == 'audio':
                transcript = item['result'].get('transcript', '')
                context_parts.append(f"[AUDIO TRANSCRIPT]: {transcript}")
                sources.append('audio')
            
            elif item['type'] == 'document':
                text = item['result'].get('text', '')
                context_parts.append(f"[DOCUMENT TEXT]: {text}")
                sources.append('document')
            
            elif item['type'] == 'text':
                content = item['content']
                context_parts.append(f"[TEXT]: {content}")
                sources.append('text')
        
        combined_context = "\n\n".join(context_parts)
        
        # Create synthesis prompt
        lang_instruction = "Trả lời bằng tiếng Việt." if language == "vi" else "Answer in English."
        synthesis_prompt = f"""
Bạn là AI assistant phân tích đa phương thức (multimodal).

CONTEXT từ nhiều nguồn:
{combined_context}

QUESTION: {query}

{lang_instruction}

Hãy tổng hợp thông tin từ TẤT CẢ các nguồn trên để trả lời câu hỏi.
Nêu rõ thông tin từ nguồn nào và làm rõ mối liên hệ giữa các nguồn.
"""
        
        # Use Gemini for synthesis
        if self.gemini_vision_model:
            response = self.gemini_vision_model.generate_content(synthesis_prompt)
            
            return {
                'response': response.text,
                'sources_analyzed': sources,
                'combined_insights': response.text,
                'context_used': combined_context[:500] + "..."
            }
        else:
            return {
                'error': 'No AI model available for synthesis',
                'sources_analyzed': sources,
                'context_used': combined_context[:500] + "..."
            }
    
    # =========================================================================
    # UTILITY METHODS
    # =========================================================================
    
    def _get_available_models(self) -> List[str]:
        """Get list of available models"""
        models = []
        if self.gemini_vision_model:
            models.append('gemini')
        if self.openai_client:
            models.append('gpt4-vision')
        return models
    
    def get_capabilities(self) -> Dict:
        """Get handler capabilities"""
        return {
            'vision': {
                'enabled': bool(self.gemini_vision_model or self.openai_client),
                'models': self._get_available_models()
            },
            'audio': {
                'enabled': True,
                'service_url': self.speech2text_url
            },
            'document': {
                'enabled': True,
                'service_url': self.document_intelligence_url
            },
            'multimodal': {
                'enabled': True,
                'max_inputs': 10
            }
        }


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def get_multimodal_handler() -> MultimodalHandler:
    """Get singleton multimodal handler instance"""
    global _multimodal_handler
    
    if '_multimodal_handler' not in globals():
        _multimodal_handler = MultimodalHandler()
    
    return _multimodal_handler


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    # Initialize handler
    handler = MultimodalHandler()
    
    print("=== Multimodal Handler Capabilities ===")
    print(handler.get_capabilities())
    
    # Example 1: Image analysis
    print("\n=== Image Analysis Example ===")
    # result = handler.analyze_image(
    #     "path/to/image.jpg",
    #     prompt="What's in this image?",
    #     model="gemini",
    #     language="vi"
    # )
    # print(result)
    
    # Example 2: Audio transcription
    print("\n=== Audio Transcription Example ===")
    # result = handler.transcribe_audio(
    #     "path/to/audio.mp3",
    #     model="smart",
    #     enable_diarization=True
    # )
    # print(result)
    
    # Example 3: Multimodal analysis
    print("\n=== Multimodal Analysis Example ===")
    # result = handler.analyze_multimodal(
    #     inputs=[
    #         {'type': 'image', 'path': 'chart.png'},
    #         {'type': 'audio', 'path': 'explanation.mp3'},
    #         {'type': 'text', 'content': 'Additional context...'}
    #     ],
    #     query="Explain the relationship between the visual data and audio explanation",
    #     language="vi"
    # )
    # print(result)
