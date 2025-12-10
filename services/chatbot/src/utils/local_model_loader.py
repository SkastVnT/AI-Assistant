"""
Local Model Loader for ChatBot
Supports: BloomVN-8B, Qwen1.5-1.8B, Qwen2.5-14B
"""

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import os
import logging

logger = logging.getLogger(__name__)

class LocalModelLoader:
    def __init__(self):
        self.models = {}
        self.tokenizers = {}
        self.base_path = os.path.join(os.path.dirname(__file__), '..', '..', 'models')
        
        # Model configurations
        self.model_configs = {
            'bloomvn': {
                'path': 'BloomVN-8B-chat',
                'name': 'BloomVN-8B Local',
                'max_tokens': 1000,
                'quantize': True  # Use 8-bit for VRAM saving
            },
            'qwen1.5': {
                'path': 'Qwen1.5-1.8B-Chat',
                'name': 'Qwen1.5-1.8B Local',
                'max_tokens': 1000,
                'quantize': False  # Small model, no need
            },
            'qwen2.5': {
                'path': 'Qwen2.5-14B-Instruct',
                'name': 'Qwen2.5-14B Local',
                'max_tokens': 2000,
                'quantize': True  # Use 8-bit: 14GB → 7GB VRAM
            }
        }
    
    def load_model(self, model_key):
        """Load model and tokenizer if not already loaded"""
        if model_key in self.models:
            logger.info(f"Model {model_key} already loaded")
            return self.models[model_key], self.tokenizers[model_key]
        
        try:
            config = self.model_configs.get(model_key)
            if not config:
                raise ValueError(f"Unknown model key: {model_key}")
            
            model_path = os.path.join(self.base_path, config['path'])
            
            if not os.path.exists(model_path):
                raise FileNotFoundError(f"Model not found at: {model_path}")
            
            logger.info(f"Loading {config['name']} from {model_path}...")
            
            # Load tokenizer with proper handling
            try:
                tokenizer = AutoTokenizer.from_pretrained(
                    model_path,
                    trust_remote_code=True,
                    use_fast=False  # Use slow tokenizer for compatibility
                )
            except Exception as e:
                logger.warning(f"Failed to load AutoTokenizer, trying PreTrainedTokenizerFast: {e}")
                from transformers import PreTrainedTokenizerFast
                tokenizer = PreTrainedTokenizerFast.from_pretrained(
                    model_path,
                    trust_remote_code=True
                )
            
            # Ensure pad token is set
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token
            
            # Load model with optimizations
            device = "cuda" if torch.cuda.is_available() else "cpu"
            
            if device == "cuda":
                # Use quantization for large models to save VRAM
                if config.get('quantize', False):
                    logger.info(f"Loading with 8-bit quantization to save VRAM...")
                    from transformers import BitsAndBytesConfig
                    
                    # Configure 8-bit quantization with CPU offloading
                    quantization_config = BitsAndBytesConfig(
                        load_in_8bit=True,
                        llm_int8_enable_fp32_cpu_offload=True  # Allow CPU offloading
                    )
                    
                    # Adjust memory limits based on model size
                    if model_key == 'qwen2.5':
                        # Qwen2.5-14B needs more VRAM
                        max_memory = {0: "7GB", "cpu": "40GB"}
                    else:
                        max_memory = {0: "6GB", "cpu": "30GB"}
                    
                    model = AutoModelForCausalLM.from_pretrained(
                        model_path,
                        device_map="auto",
                        quantization_config=quantization_config,
                        trust_remote_code=True,
                        max_memory=max_memory,
                        low_cpu_mem_usage=True  # Reduce CPU memory during loading
                    )
                else:
                    model = AutoModelForCausalLM.from_pretrained(
                        model_path,
                        device_map="auto",
                        torch_dtype=torch.float16,
                        trust_remote_code=True,
                        low_cpu_mem_usage=True
                    )
            else:
                # CPU mode
                logger.warning(f"No GPU detected, loading on CPU (will be slow)")
                model = AutoModelForCausalLM.from_pretrained(
                    model_path,
                    device_map="cpu",
                    trust_remote_code=True
                )
            
            self.models[model_key] = model
            self.tokenizers[model_key] = tokenizer
            
            logger.info(f"✅ {config['name']} loaded successfully on {device}")
            return model, tokenizer
            
        except Exception as e:
            logger.error(f"❌ Failed to load model {model_key}: {e}")
            raise
    
    def generate(self, model_key, messages, system_prompt="", max_tokens=None, temperature=0.7):
        """Generate response from local model"""
        try:
            model, tokenizer = self.load_model(model_key)
            config = self.model_configs[model_key]
            
            if max_tokens is None:
                max_tokens = config['max_tokens']
            
            # Format messages based on model type
            if model_key == 'bloomvn':
                prompt = self._format_bloomvn_prompt(messages, system_prompt)
            elif model_key.startswith('qwen'):
                prompt = self._format_qwen_prompt(messages, system_prompt)
            else:
                prompt = self._format_generic_prompt(messages, system_prompt)
            
            # Tokenize
            inputs = tokenizer(prompt, return_tensors="pt", padding=True)
            
            # Move inputs to the same device as model
            device = next(model.parameters()).device
            inputs = {k: v.to(device) for k, v in inputs.items()}
            
            # Generate
            with torch.no_grad():
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=max_tokens,
                    temperature=temperature,
                    do_sample=True,
                    top_p=0.95,
                    repetition_penalty=1.1,
                    pad_token_id=tokenizer.pad_token_id,
                    eos_token_id=tokenizer.eos_token_id
                )
            
            # Decode response (skip input tokens)
            response = tokenizer.decode(
                outputs[0][inputs['input_ids'].shape[1]:], 
                skip_special_tokens=True
            )
            
            return response.strip()
            
        except Exception as e:
            logger.error(f"Error generating with {model_key}: {e}")
            raise
    
    def _format_bloomvn_prompt(self, messages, system_prompt):
        """Format prompt for BloomVN (Vietnamese)"""
        prompt = f"{system_prompt}\n\n" if system_prompt else ""
        
        for msg in messages[-5:]:  # Last 5 messages for context
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            
            if role == 'user':
                prompt += f"Người dùng: {content}\n"
            elif role == 'assistant':
                prompt += f"Trợ lý: {content}\n"
        
        prompt += "Trợ lý:"
        return prompt
    
    def _format_qwen_prompt(self, messages, system_prompt):
        """Format prompt for Qwen models (uses chat template)"""
        prompt = ""
        
        if system_prompt:
            prompt += f"<|im_start|>system\n{system_prompt}<|im_end|>\n"
        
        for msg in messages[-5:]:  # Last 5 messages
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            prompt += f"<|im_start|>{role}\n{content}<|im_end|>\n"
        
        prompt += "<|im_start|>assistant\n"
        return prompt
    
    def _format_generic_prompt(self, messages, system_prompt):
        """Generic prompt format"""
        prompt = f"System: {system_prompt}\n\n" if system_prompt else ""
        
        for msg in messages[-5:]:
            role = msg.get('role', 'user').capitalize()
            content = msg.get('content', '')
            prompt += f"{role}: {content}\n"
        
        prompt += "Assistant:"
        return prompt
    
    def unload_model(self, model_key):
        """Unload model to free memory"""
        if model_key in self.models:
            del self.models[model_key]
            del self.tokenizers[model_key]
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            logger.info(f"Unloaded model: {model_key}")
    
    def get_loaded_models(self):
        """Get list of currently loaded models"""
        return list(self.models.keys())
    
    def get_available_models(self):
        """Check which models are available on disk"""
        available = {}
        for key, config in self.model_configs.items():
            model_path = os.path.join(self.base_path, config['path'])
            available[key] = {
                'name': config['name'],
                'available': os.path.exists(model_path),
                'path': config['path'],
                'loaded': key in self.models
            }
        return available

# Global instance
model_loader = LocalModelLoader()
