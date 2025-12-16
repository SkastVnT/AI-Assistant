"""
Gemini Client - Google Gemini 2.0 Flash (Free) for STT Transcript Cleaning
Cloud-based LLM for cleaning and enhancing speech-to-text transcripts
"""

import os
import time
from typing import Tuple, Optional
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("[Gemini] Warning: google-generativeai not installed. Install with: pip install google-generativeai")


class GeminiClient:
    """
    Client for Google Gemini 2.0 Flash (Free) model
    Used for cleaning and enhancing STT transcripts
    """
    
    def __init__(
        self,
        model_name: str = "gemini-1.5-flash",
        api_key: Optional[str] = None,
    ):
        """
        Initialize Gemini client
        
        Args:
            model_name: Gemini model name (default: gemini-1.5-flash - free tier)
            api_key: Google API key (reads from GEMINI_API_KEY env if None)
        """
        if not GEMINI_AVAILABLE:
            raise ImportError("google-generativeai package not installed")
            
        self.model_name = model_name
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
            
        self.model = None
        self._is_loaded = False
        
    def load(self) -> float:
        """
        Initialize Gemini model
        
        Returns:
            Load time in seconds
        """
        print(f"[Gemini] Initializing {self.model_name}...")
        start_time = time.time()
        
        try:
            # Configure Gemini API
            genai.configure(api_key=self.api_key)
            
            # Initialize model
            self.model = genai.GenerativeModel(self.model_name)
            
            load_time = time.time() - start_time
            self._is_loaded = True
            
            print(f"[Gemini] Initialized in {load_time:.2f}s")
            return load_time
            
        except Exception as e:
            print(f"[Gemini] Initialization failed: {e}")
            raise
        
    def generate(
        self,
        prompt: str,
        max_new_tokens: int = 4096,
        temperature: float = 0.3,
        top_p: float = 0.9,
        **kwargs
    ) -> Tuple[str, float]:
        """
        Generate response from prompt using Gemini
        
        Args:
            prompt: Input prompt
            max_new_tokens: Maximum tokens to generate (max_output_tokens in Gemini)
            temperature: Sampling temperature (0.0 = deterministic)
            top_p: Nucleus sampling parameter
            **kwargs: Additional generation parameters
            
        Returns:
            Tuple of (response, generation_time)
        """
        if not self._is_loaded:
            self.load()
            
        print(f"[Gemini] Processing prompt ({len(prompt)} chars)...")
        start_time = time.time()
        
        try:
            # Configure generation parameters
            generation_config = genai.GenerationConfig(
                temperature=temperature,
                top_p=top_p,
                max_output_tokens=max_new_tokens,
            )
            
            # Generate response
            response = self.model.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            # Extract text from response
            response_text = response.text
            
            generation_time = time.time() - start_time
            
            print(f"[Gemini] Generated in {generation_time:.2f}s ({len(response_text)} chars)")
            return response_text.strip(), generation_time
            
        except Exception as e:
            print(f"[Gemini] Generation failed: {e}")
            raise
        
    def clean_transcript(
        self,
        whisper_text: str,
        phowhisper_text: str,
        prompt_template: Optional[str] = None,
        **generation_kwargs
    ) -> Tuple[str, float]:
        """
        Clean and enhance dual transcripts using Gemini
        
        Args:
            whisper_text: Whisper transcript
            phowhisper_text: PhoWhisper transcript
            prompt_template: Custom prompt template (uses default if None)
            **generation_kwargs: Additional generation parameters
            
        Returns:
            Tuple of (cleaned_transcript, processing_time)
        """
        if prompt_template is None:
            # Use default STT cleaning prompt
            from core.prompts.templates import PromptTemplates
            prompt = PromptTemplates.build_gemini_prompt(whisper_text, phowhisper_text)
        else:
            prompt = prompt_template.format(
                whisper=whisper_text,
                phowhisper=phowhisper_text
            )
        
        return self.generate(prompt, **generation_kwargs)
        
    def save_result(self, text: str, output_path: str):
        """Save generated text to file"""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"[Gemini] Saved: {output_path}")
        
    def __repr__(self):
        status = "loaded" if self._is_loaded else "not loaded"
        return f"GeminiClient(model={self.model_name}, status={status})"
