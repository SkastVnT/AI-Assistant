"""
Multi-LLM Client - Unified interface with automatic retry mechanism
Supports Gemini (4 API keys with retry), OpenAI, and DeepSeek
"""

import os
import time
from typing import Tuple, Optional, Literal
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import individual clients
from .gemini_client import GeminiClient, GEMINI_AVAILABLE
from .openai_client import OpenAIClient, OPENAI_AVAILABLE
from .deepseek_client import DeepSeekClient, DEEPSEEK_AVAILABLE


class MultiLLMClient:
    """
    Unified LLM client with automatic retry and fallback
    
    Features:
    - Gemini: Retry with 4 API keys on quota exceeded
    - OpenAI: Single API key
    - DeepSeek: Single API key
    - Automatic model selection based on availability
    """
    
    def __init__(
        self,
        model_type: Literal["gemini", "openai", "deepseek"] = "gemini",
        auto_fallback: bool = True
    ):
        """
        Initialize Multi-LLM client
        
        Args:
            model_type: Primary model to use ("gemini", "openai", "deepseek")
            auto_fallback: Auto fallback to other models on failure
        """
        self.model_type = model_type
        self.auto_fallback = auto_fallback
        self.client = None
        self._is_loaded = False
        
        # Load all 4 Gemini API keys for retry
        self.gemini_keys = [
            os.getenv('GEMINI_API_KEY_1'),
            os.getenv('GEMINI_API_KEY_2'),
            os.getenv('GEMINI_API_KEY_3'),
            os.getenv('GEMINI_API_KEY_4')
        ]
        # Filter out None/empty keys
        self.gemini_keys = [k for k in self.gemini_keys if k]
        
    def load(self) -> float:
        """
        Initialize the selected LLM client
        
        Returns:
            Load time in seconds
        """
        print(f"[MultiLLM] Loading {self.model_type} client...")
        start_time = time.time()
        
        try:
            if self.model_type == "gemini":
                if not GEMINI_AVAILABLE:
                    raise ImportError("google-generativeai not installed. Run: pip install google-generativeai")
                if not self.gemini_keys:
                    raise ValueError("No Gemini API keys found in environment variables (GEMINI_API_KEY_1-4)")
                print(f"[MultiLLM] Found {len(self.gemini_keys)} Gemini API key(s)")
                # Use first available key for initial load
                self.client = GeminiClient(api_key=self.gemini_keys[0])
                
            elif self.model_type == "openai":
                if not OPENAI_AVAILABLE:
                    raise ImportError("openai library not installed. Run: pip install openai>=1.0.0")
                api_key = os.getenv('OPENAI_API_KEY')
                if not api_key:
                    raise ValueError("OPENAI_API_KEY not found in environment variables")
                self.client = OpenAIClient()
                
            elif self.model_type == "deepseek":
                if not DEEPSEEK_AVAILABLE:
                    raise ImportError("openai library not installed (required for DeepSeek). Run: pip install openai>=1.0.0")
                api_key = os.getenv('DEEPSEEK_API_KEY')
                if not api_key:
                    raise ValueError("DEEPSEEK_API_KEY not found in environment variables")
                self.client = DeepSeekClient()
                
            else:
                raise ValueError(f"Unsupported model type: {self.model_type}. Supported: gemini, openai, deepseek")
            
            load_time = self.client.load()
            self._is_loaded = True
            
            print(f"[MultiLLM] ✅ {self.model_type.upper()} loaded successfully in {load_time:.2f}s")
            return load_time
            
        except Exception as e:
            error_msg = f"Failed to load {self.model_type.upper()}: {str(e)}"
            print(f"[MultiLLM] ❌ {error_msg}")
            
            if self.auto_fallback:
                print(f"[MultiLLM] 🔄 Attempting fallback to other models...")
                return self._try_fallback()
            raise RuntimeError(error_msg) from e
    
    def _try_fallback(self) -> float:
        """Try to load alternative models with detailed error tracking"""
        fallback_order = ["gemini", "openai", "deepseek"]
        fallback_order.remove(self.model_type)
        
        errors = {self.model_type: "Failed (original)"}
        
        for model in fallback_order:
            try:
                print(f"[MultiLLM] 🔄 Attempting fallback: {self.model_type} → {model.upper()}...")
                original_type = self.model_type
                self.model_type = model
                self._is_loaded = False  # Reset load state
                load_time = self.load()
                print(f"[MultiLLM] ✅ Fallback successful: {original_type} → {model.upper()}")
                return load_time
            except Exception as e:
                errors[model] = str(e)
                print(f"[MultiLLM] ❌ {model.upper()} fallback failed: {e}")
                continue
        
        # All models failed
        error_summary = "\n".join([f"  - {m.upper()}: {err}" for m, err in errors.items()])
        raise RuntimeError(f"All LLM models failed to load:\n{error_summary}")
    
    def generate(
        self,
        prompt: str,
        max_new_tokens: int = 4096,
        temperature: float = 0.3,
        top_p: float = 0.9,
        **kwargs
    ) -> Tuple[str, float]:
        """
        Generate response with automatic retry (Gemini only)
        
        Args:
            prompt: Input prompt
            max_new_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            top_p: Nucleus sampling parameter
            **kwargs: Additional generation parameters
            
        Returns:
            Tuple of (response, generation_time)
        """
        if not self._is_loaded:
            self.load()
        
        # For Gemini: Try all 4 API keys on quota exceeded
        if self.model_type == "gemini" and len(self.gemini_keys) > 1:
            return self._generate_with_gemini_retry(
                prompt, max_new_tokens, temperature, top_p, **kwargs
            )
        
        # For other models: Direct call
        return self.client.generate(prompt, max_new_tokens, temperature, top_p, **kwargs)
    
    def _generate_with_gemini_retry(
        self,
        prompt: str,
        max_new_tokens: int,
        temperature: float,
        top_p: float,
        **kwargs
    ) -> Tuple[str, float]:
        """
        Generate with Gemini, retry with 4 API keys on quota exceeded
        
        Returns:
            Tuple of (response, generation_time)
        """
        last_error = None
        
        for idx, api_key in enumerate(self.gemini_keys):
            try:
                print(f"[MultiLLM] 🔑 Trying Gemini API Key #{idx + 1}/{len(self.gemini_keys)}...")
                
                # Emit progress via callback if provided
                if 'progress_callback' in kwargs:
                    kwargs['progress_callback'](f"Trying Gemini API Key #{idx + 1}/{len(self.gemini_keys)}...")
                
                # Create new client with this API key
                gemini = GeminiClient(api_key=api_key)
                gemini.load()
                
                # Try to generate
                response, gen_time = gemini.generate(
                    prompt, max_new_tokens, temperature, top_p, **kwargs
                )
                
                if idx > 0:
                    success_msg = f"✅ Success with Gemini API Key #{idx + 1}"
                    print(f"[MultiLLM] {success_msg}")
                    if 'progress_callback' in kwargs:
                        kwargs['progress_callback'](success_msg)
                
                return response, gen_time
                
            except Exception as e:
                error_msg = str(e)
                last_error = error_msg
                
                # Check if quota exceeded
                is_quota_error = (
                    "429" in error_msg or 
                    "quota" in error_msg.lower() or 
                    "rate limit" in error_msg.lower() or
                    "resource exhausted" in error_msg.lower()
                )
                
                if is_quota_error:
                    warning_msg = f"⚠️ Gemini quota exceeded - API Key #{idx + 1}"
                    print(f"[MultiLLM] {warning_msg}")
                    if 'progress_callback' in kwargs:
                        kwargs['progress_callback'](warning_msg)
                    
                    # If not the last key, try next
                    if idx < len(self.gemini_keys) - 1:
                        retry_msg = f"🔄 Retrying with next Gemini API key..."
                        print(f"[MultiLLM] {retry_msg}")
                        if 'progress_callback' in kwargs:
                            kwargs['progress_callback'](retry_msg)
                        time.sleep(1)  # Small delay before retry
                        continue
                    else:
                        exhausted_msg = f"❌ All {len(self.gemini_keys)} Gemini API keys exhausted"
                        print(f"[MultiLLM] {exhausted_msg}")
                        if 'progress_callback' in kwargs:
                            kwargs['progress_callback'](exhausted_msg)
                else:
                    # Non-quota error, fail immediately
                    error_detail = f"❌ Gemini error (not quota): {error_msg[:100]}"
                    print(f"[MultiLLM] {error_detail}")
                    if 'progress_callback' in kwargs:
                        kwargs['progress_callback'](error_detail)
                    raise
        
        # All keys exhausted
        raise RuntimeError(f"All Gemini API keys exhausted. Last error: {last_error}")
    
    def clean_transcript(
        self,
        whisper_text: str,
        phowhisper_text: str,
        prompt_template: Optional[str] = None,
        **generation_kwargs
    ) -> Tuple[str, float]:
        """
        Clean and enhance dual transcripts
        
        Args:
            whisper_text: Whisper transcript
            phowhisper_text: PhoWhisper transcript
            prompt_template: Custom prompt template
            **generation_kwargs: Additional generation parameters
            
        Returns:
            Tuple of (cleaned_transcript, processing_time)
        """
        if not self._is_loaded:
            self.load()
        
        # For Gemini with retry
        if self.model_type == "gemini" and len(self.gemini_keys) > 1:
            # Build prompt
            if prompt_template is None:
                from app.core.prompts.templates import PromptTemplates
                prompt = PromptTemplates.build_gemini_prompt(whisper_text, phowhisper_text)
            else:
                prompt = prompt_template.format(
                    whisper=whisper_text,
                    phowhisper=phowhisper_text
                )
            
            return self._generate_with_gemini_retry(prompt, **generation_kwargs)
        
        # For other models
        return self.client.clean_transcript(
            whisper_text, phowhisper_text, prompt_template, **generation_kwargs
        )
    
    def save_result(self, text: str, output_path: str):
        """Save generated text to file"""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"[MultiLLM] Saved: {output_path}")
    
    def __repr__(self):
        status = "loaded" if self._is_loaded else "not loaded"
        gemini_keys_info = f", {len(self.gemini_keys)} keys" if self.model_type == "gemini" else ""
        return f"MultiLLMClient(model={self.model_type}{gemini_keys_info}, status={status})"
