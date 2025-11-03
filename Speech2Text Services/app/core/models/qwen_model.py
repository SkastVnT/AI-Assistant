"""
Qwen Client - Alibaba Qwen2.5-1.5B-Instruct for Smart Fusion
Lightweight LLM for combining and enhancing dual transcripts
"""

import time
import torch
from typing import Tuple, Optional
from pathlib import Path


class QwenClient:
    """
    Client for Qwen2.5-1.5B-Instruct model
    Used for smart fusion of multiple transcripts with speaker separation
    """
    
    def __init__(
        self,
        model_name: str = "Qwen/Qwen2.5-1.5B-Instruct",
        device: Optional[str] = None,
        torch_dtype: Optional[torch.dtype] = None,
    ):
        """
        Initialize Qwen client
        
        Args:
            model_name: HuggingFace model name
            device: Device to use (auto, cuda, cpu)
            torch_dtype: Data type (float16, float32, or None for auto)
        """
        self.model_name = model_name
        self.device = device or "auto"
        
        if torch_dtype is None:
            self.torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32
        else:
            self.torch_dtype = torch_dtype
            
        self.model = None
        self.tokenizer = None
        self._is_loaded = False
        
    def load(self) -> float:
        """
        Load Qwen model and tokenizer
        
        Returns:
            Load time in seconds
        """
        from transformers import AutoTokenizer, AutoModelForCausalLM
        
        # Clear GPU memory
        if torch.cuda.is_available():
            print("[Qwen] Clearing VRAM...")
            torch.cuda.empty_cache()
            import gc
            gc.collect()
            vram = torch.cuda.get_device_properties(0).total_memory / 1024**3
            print(f"[Qwen] VRAM available: {vram:.1f}GB")
        
        print(f"[Qwen] Loading {self.model_name}...")
        start_time = time.time()
        
        # Load tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_name,
            trust_remote_code=True
        )
        
        # Load model
        if torch.cuda.is_available():
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=self.torch_dtype,
                device_map="auto",
                low_cpu_mem_usage=True,
                trust_remote_code=True,
            )
        else:
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                device_map="cpu",
                trust_remote_code=True,
            )
        
        load_time = time.time() - start_time
        self._is_loaded = True
        
        print(f"[Qwen] Loaded in {load_time:.2f}s")
        return load_time
        
    def generate(
        self,
        prompt: str,
        max_new_tokens: int = 3072,
        min_new_tokens: int = 500,
        temperature: float = 0.3,
        top_p: float = 0.9,
        repetition_penalty: float = 1.1,
        **kwargs
    ) -> Tuple[str, float]:
        """
        Generate response from prompt
        
        Args:
            prompt: Input prompt (should follow Qwen format)
            max_new_tokens: Maximum tokens to generate
            min_new_tokens: Minimum tokens to generate
            temperature: Sampling temperature (0.0 = deterministic)
            top_p: Nucleus sampling parameter
            repetition_penalty: Penalty for repetition
            **kwargs: Additional generation parameters
            
        Returns:
            Tuple of (response, generation_time)
        """
        if not self._is_loaded:
            self.load()
            
        print(f"[Qwen] Processing prompt ({len(prompt)} chars)...")
        start_time = time.time()
        
        # Tokenize
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        
        # Generate with optimized parameters
        with torch.inference_mode():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                min_new_tokens=min_new_tokens,
                temperature=temperature,
                top_p=top_p,
                do_sample=temperature > 0,
                repetition_penalty=repetition_penalty,
                pad_token_id=self.tokenizer.eos_token_id,
                **kwargs
            )
        
        # Decode response (exclude input tokens)
        response = self.tokenizer.decode(
            outputs[0][len(inputs["input_ids"][0]):],
            skip_special_tokens=True
        )
        
        generation_time = time.time() - start_time
        
        print(f"[Qwen] Generated in {generation_time:.2f}s ({len(response)} chars)")
        return response.strip(), generation_time
        
    def fuse_transcripts(
        self,
        whisper_text: str,
        phowhisper_text: str,
        prompt_template: Optional[str] = None,
        **generation_kwargs
    ) -> Tuple[str, float]:
        """
        Fuse two transcripts using Qwen
        
        Args:
            whisper_text: Whisper transcript
            phowhisper_text: PhoWhisper transcript
            prompt_template: Custom prompt template (uses default if None)
            **generation_kwargs: Additional generation parameters
            
        Returns:
            Tuple of (fused_transcript, processing_time)
        """
        if prompt_template is None:
            # Use default fusion prompt
            from app.core.prompts import build_fusion_prompt
            prompt = build_fusion_prompt(whisper_text, phowhisper_text)
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
        print(f"[Qwen] Saved: {output_path}")
        
    def __repr__(self):
        status = "loaded" if self._is_loaded else "not loaded"
        dtype = str(self.torch_dtype).split(".")[-1]
        return f"QwenClient(model={self.model_name}, dtype={dtype}, status={status})"
