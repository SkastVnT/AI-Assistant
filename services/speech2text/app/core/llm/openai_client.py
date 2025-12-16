"""
OpenAI Client - GPT-4o-mini for STT Transcript Cleaning
Cloud-based LLM for cleaning and enhancing speech-to-text transcripts
Cost: $0.15/$0.60 per 1M tokens (input/output)
"""

import os
import time
from typing import Tuple, Optional
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("[OpenAI] Warning: openai not installed. Install with: pip install openai")


class OpenAIClient:
    """
    Client for OpenAI GPT-4o-mini model
    Used for cleaning and enhancing STT transcripts
    """
    
    def __init__(
        self,
        model_name: str = "gpt-4o-mini",
        api_key: Optional[str] = None,
    ):
        """
        Initialize OpenAI client
        
        Args:
            model_name: OpenAI model name (default: gpt-4o-mini)
            api_key: OpenAI API key (reads from OPENAI_API_KEY env if None)
        """
        if not OPENAI_AVAILABLE:
            raise ImportError("openai package not installed")
            
        self.model_name = model_name
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
            
        self.client = None
        self._is_loaded = False
        
    def load(self) -> float:
        """
        Initialize OpenAI client
        
        Returns:
            Load time in seconds
        """
        print(f"[OpenAI] Initializing {self.model_name}...")
        start_time = time.time()
        
        try:
            # Initialize OpenAI client
            self.client = openai.OpenAI(api_key=self.api_key)
            
            load_time = time.time() - start_time
            self._is_loaded = True
            
            print(f"[OpenAI] Initialized in {load_time:.2f}s")
            return load_time
            
        except Exception as e:
            print(f"[OpenAI] Initialization failed: {e}")
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
        Generate response from prompt using OpenAI
        
        Args:
            prompt: Input prompt
            max_new_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 = deterministic)
            top_p: Nucleus sampling parameter
            **kwargs: Additional generation parameters
            
        Returns:
            Tuple of (response, generation_time)
        """
        if not self._is_loaded:
            self.load()
            
        print(f"[OpenAI] Processing prompt ({len(prompt)} chars)...")
        start_time = time.time()
        
        try:
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert in cleaning and enhancing Vietnamese speech-to-text transcripts."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_new_tokens
            )
            
            # Extract text from response
            response_text = response.choices[0].message.content
            
            generation_time = time.time() - start_time
            
            print(f"[OpenAI] Generated in {generation_time:.2f}s ({len(response_text)} chars)")
            return response_text.strip(), generation_time
            
        except Exception as e:
            print(f"[OpenAI] Generation failed: {e}")
            raise
        
    def clean_transcript(
        self,
        whisper_text: str,
        phowhisper_text: str,
        prompt_template: Optional[str] = None,
        **generation_kwargs
    ) -> Tuple[str, float]:
        """
        Clean and enhance dual transcripts using OpenAI
        
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
            from app.core.prompts.templates import PromptTemplates
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
        print(f"[OpenAI] Saved: {output_path}")
        
    def __repr__(self):
        status = "loaded" if self._is_loaded else "not loaded"
        return f"OpenAIClient(model={self.model_name}, status={status})"
