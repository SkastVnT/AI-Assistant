"""
Model Offloading Module
=======================

Memory optimization through model offloading strategies.
Enables running large models on limited VRAM devices.

Features:
- Sequential CPU offload
- Model CPU offload  
- Attention slicing
- VAE slicing/tiling
- FP8/INT8 quantization
"""

import logging
import gc
from pathlib import Path
from typing import Optional, Dict, Any, List, Union, Literal
from dataclasses import dataclass
from enum import Enum

import torch
from PIL import Image

logger = logging.getLogger(__name__)


class OffloadStrategy(str, Enum):
    """Offloading strategies"""
    NONE = "none"                        # No offloading
    ATTENTION_SLICING = "attention"      # Slice attention (minimal impact)
    VAE_SLICING = "vae"                  # Slice VAE operations
    MODEL_CPU = "model_cpu"              # Offload to CPU between steps
    SEQUENTIAL_CPU = "sequential_cpu"   # Sequential layer offloading
    FULL_CPU = "full_cpu"                # Full CPU inference


class QuantizationType(str, Enum):
    """Quantization types"""
    NONE = "none"
    FP16 = "fp16"
    BF16 = "bf16"
    FP8 = "fp8"
    INT8 = "int8"
    INT4 = "int4"


@dataclass
class OffloadConfig:
    """Offloading configuration"""
    # Primary strategy
    strategy: OffloadStrategy = OffloadStrategy.ATTENTION_SLICING
    
    # Memory thresholds
    vram_threshold_gb: float = 8.0  # Apply offloading below this
    target_vram_usage_gb: float = 6.0  # Target VRAM usage
    
    # Optimization settings
    enable_attention_slicing: bool = True
    attention_slice_size: Optional[int] = None  # "auto" if None
    
    enable_vae_slicing: bool = True
    enable_vae_tiling: bool = False
    
    enable_xformers: bool = True
    enable_torch_compile: bool = False
    
    # Quantization
    quantization: QuantizationType = QuantizationType.FP16
    
    # CPU offload settings
    cpu_offload_layers: List[str] = None  # Which layers to offload
    offload_buffers: bool = False
    
    # Torch settings
    enable_tf32: bool = True  # Faster on Ampere+ GPUs
    channels_last: bool = True  # Memory format optimization


@dataclass
class MemoryStats:
    """Memory statistics"""
    gpu_allocated: float  # GB
    gpu_reserved: float   # GB
    gpu_free: float       # GB
    gpu_total: float      # GB
    cpu_used: float       # GB (if applicable)
    
    def to_dict(self) -> Dict[str, float]:
        return {
            "gpu_allocated_gb": round(self.gpu_allocated, 2),
            "gpu_reserved_gb": round(self.gpu_reserved, 2),
            "gpu_free_gb": round(self.gpu_free, 2),
            "gpu_total_gb": round(self.gpu_total, 2),
            "cpu_used_gb": round(self.cpu_used, 2),
        }


class MemoryOptimizer:
    """
    Memory optimization and model offloading manager
    
    Features:
    - Automatic strategy selection
    - Dynamic offloading
    - Memory monitoring
    - Quantization support
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.config = OffloadConfig()
        self._original_configs: Dict[int, Dict] = {}
        
        # Apply global optimizations
        self._apply_global_optimizations()
        
        self._initialized = True
        logger.info("MemoryOptimizer initialized")
    
    def _apply_global_optimizations(self):
        """Apply global PyTorch optimizations"""
        # Enable TF32 for faster matmul on Ampere+
        if self.config.enable_tf32 and torch.cuda.is_available():
            torch.backends.cuda.matmul.allow_tf32 = True
            torch.backends.cudnn.allow_tf32 = True
        
        # Set memory format
        if self.config.channels_last:
            torch.backends.cudnn.benchmark = True
    
    def get_memory_stats(self, device_id: int = 0) -> MemoryStats:
        """Get current memory statistics"""
        if not torch.cuda.is_available():
            return MemoryStats(0, 0, 0, 0, 0)
        
        torch.cuda.set_device(device_id)
        
        allocated = torch.cuda.memory_allocated(device_id) / (1024 ** 3)
        reserved = torch.cuda.memory_reserved(device_id) / (1024 ** 3)
        total = torch.cuda.get_device_properties(device_id).total_memory / (1024 ** 3)
        free = total - reserved
        
        # CPU memory
        try:
            import psutil
            cpu_used = psutil.Process().memory_info().rss / (1024 ** 3)
        except ImportError:
            cpu_used = 0
        
        return MemoryStats(
            gpu_allocated=allocated,
            gpu_reserved=reserved,
            gpu_free=free,
            gpu_total=total,
            cpu_used=cpu_used,
        )
    
    def get_available_vram(self, device_id: int = 0) -> float:
        """Get available VRAM in GB"""
        stats = self.get_memory_stats(device_id)
        return stats.gpu_free
    
    def should_offload(self, device_id: int = 0) -> bool:
        """Check if offloading should be applied"""
        stats = self.get_memory_stats(device_id)
        return stats.gpu_total < self.config.vram_threshold_gb
    
    def get_recommended_strategy(self, device_id: int = 0) -> OffloadStrategy:
        """Get recommended offload strategy based on available VRAM"""
        vram = self.get_available_vram(device_id)
        
        if vram >= 12:
            return OffloadStrategy.NONE
        elif vram >= 8:
            return OffloadStrategy.ATTENTION_SLICING
        elif vram >= 6:
            return OffloadStrategy.VAE_SLICING
        elif vram >= 4:
            return OffloadStrategy.MODEL_CPU
        else:
            return OffloadStrategy.SEQUENTIAL_CPU
    
    def apply_optimizations(
        self,
        pipe: Any,
        strategy: Optional[OffloadStrategy] = None,
        device_id: int = 0,
    ) -> Any:
        """
        Apply memory optimizations to a diffusers pipeline
        
        Args:
            pipe: Diffusers pipeline
            strategy: Offload strategy (auto-detect if None)
            device_id: GPU device ID
        """
        if strategy is None:
            strategy = self.get_recommended_strategy(device_id)
        
        logger.info(f"Applying offload strategy: {strategy.value}")
        
        # Store original config
        pipe_id = id(pipe)
        self._original_configs[pipe_id] = {
            "device": next(pipe.unet.parameters()).device,
        }
        
        # Apply xformers if available
        if self.config.enable_xformers:
            try:
                pipe.enable_xformers_memory_efficient_attention()
                logger.debug("Enabled xformers attention")
            except Exception as e:
                logger.debug(f"xformers not available: {e}")
        
        # Apply strategy
        if strategy == OffloadStrategy.NONE:
            pass
        
        elif strategy == OffloadStrategy.ATTENTION_SLICING:
            pipe.enable_attention_slicing(self.config.attention_slice_size)
            logger.debug("Enabled attention slicing")
        
        elif strategy == OffloadStrategy.VAE_SLICING:
            pipe.enable_attention_slicing(self.config.attention_slice_size)
            if hasattr(pipe, 'enable_vae_slicing'):
                pipe.enable_vae_slicing()
                logger.debug("Enabled VAE slicing")
            if self.config.enable_vae_tiling and hasattr(pipe, 'enable_vae_tiling'):
                pipe.enable_vae_tiling()
                logger.debug("Enabled VAE tiling")
        
        elif strategy == OffloadStrategy.MODEL_CPU:
            pipe.enable_attention_slicing()
            if hasattr(pipe, 'enable_vae_slicing'):
                pipe.enable_vae_slicing()
            pipe.enable_model_cpu_offload(gpu_id=device_id)
            logger.debug("Enabled model CPU offload")
        
        elif strategy == OffloadStrategy.SEQUENTIAL_CPU:
            pipe.enable_attention_slicing()
            if hasattr(pipe, 'enable_vae_slicing'):
                pipe.enable_vae_slicing()
            pipe.enable_sequential_cpu_offload(gpu_id=device_id)
            logger.debug("Enabled sequential CPU offload")
        
        elif strategy == OffloadStrategy.FULL_CPU:
            pipe.to("cpu")
            logger.debug("Moved to CPU")
        
        return pipe
    
    def apply_quantization(
        self,
        pipe: Any,
        quantization: Optional[QuantizationType] = None,
    ) -> Any:
        """
        Apply quantization to a pipeline
        
        Args:
            pipe: Diffusers pipeline
            quantization: Quantization type
        """
        quantization = quantization or self.config.quantization
        
        if quantization == QuantizationType.NONE:
            return pipe
        
        logger.info(f"Applying quantization: {quantization.value}")
        
        if quantization == QuantizationType.FP16:
            pipe = pipe.to(torch.float16)
        
        elif quantization == QuantizationType.BF16:
            if torch.cuda.is_bf16_supported():
                pipe = pipe.to(torch.bfloat16)
            else:
                logger.warning("BF16 not supported, using FP16")
                pipe = pipe.to(torch.float16)
        
        elif quantization == QuantizationType.FP8:
            try:
                from transformers import BitsAndBytesConfig
                
                # FP8 quantization with bitsandbytes
                quantization_config = BitsAndBytesConfig(
                    load_in_8bit=True,
                    llm_int8_threshold=6.0,
                )
                logger.debug("Applied FP8 quantization")
            except ImportError:
                logger.warning("bitsandbytes not installed, using FP16")
                pipe = pipe.to(torch.float16)
        
        elif quantization == QuantizationType.INT8:
            try:
                from transformers import BitsAndBytesConfig
                
                quantization_config = BitsAndBytesConfig(
                    load_in_8bit=True,
                )
                logger.debug("Applied INT8 quantization")
            except ImportError:
                logger.warning("bitsandbytes not installed, using FP16")
                pipe = pipe.to(torch.float16)
        
        elif quantization == QuantizationType.INT4:
            try:
                from transformers import BitsAndBytesConfig
                
                quantization_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_use_double_quant=True,
                )
                logger.debug("Applied INT4 quantization")
            except ImportError:
                logger.warning("bitsandbytes not installed, using FP16")
                pipe = pipe.to(torch.float16)
        
        return pipe
    
    def cleanup(self, aggressive: bool = False):
        """
        Clean up memory
        
        Args:
            aggressive: If True, clear all CUDA cache
        """
        gc.collect()
        
        if torch.cuda.is_available():
            if aggressive:
                torch.cuda.empty_cache()
                torch.cuda.reset_peak_memory_stats()
            else:
                torch.cuda.empty_cache()
        
        logger.debug(f"Memory cleanup (aggressive={aggressive})")
    
    def optimize_for_vram(
        self,
        pipe: Any,
        target_vram_gb: Optional[float] = None,
        device_id: int = 0,
    ) -> Any:
        """
        Automatically optimize pipeline for target VRAM usage
        
        Args:
            pipe: Diffusers pipeline
            target_vram_gb: Target VRAM in GB
            device_id: GPU device ID
        """
        target = target_vram_gb or self.config.target_vram_usage_gb
        available = self.get_available_vram(device_id)
        
        logger.info(f"Optimizing for {target}GB target, {available:.1f}GB available")
        
        # Start with minimal optimizations
        strategy = OffloadStrategy.ATTENTION_SLICING
        
        if available < target + 2:
            strategy = OffloadStrategy.VAE_SLICING
        
        if available < target:
            strategy = OffloadStrategy.MODEL_CPU
        
        if available < target / 2:
            strategy = OffloadStrategy.SEQUENTIAL_CPU
        
        return self.apply_optimizations(pipe, strategy, device_id)
    
    def get_optimization_report(self, device_id: int = 0) -> Dict[str, Any]:
        """Get detailed optimization report"""
        stats = self.get_memory_stats(device_id)
        strategy = self.get_recommended_strategy(device_id)
        
        return {
            "memory": stats.to_dict(),
            "recommended_strategy": strategy.value,
            "current_config": {
                "attention_slicing": self.config.enable_attention_slicing,
                "vae_slicing": self.config.enable_vae_slicing,
                "xformers": self.config.enable_xformers,
                "quantization": self.config.quantization.value,
            },
            "recommendations": self._get_recommendations(stats),
        }
    
    def _get_recommendations(self, stats: MemoryStats) -> List[str]:
        """Get optimization recommendations"""
        recs = []
        
        if stats.gpu_total < 8:
            recs.append("Enable sequential CPU offload for large models")
            recs.append("Consider using SD 1.5 instead of SDXL")
        
        if stats.gpu_total < 12:
            recs.append("Use FP16 quantization")
            recs.append("Enable VAE slicing")
        
        if stats.gpu_free < 2:
            recs.append("Clear model cache to free VRAM")
            recs.append("Consider closing other GPU applications")
        
        if not recs:
            recs.append("System has sufficient VRAM for most operations")
        
        return recs


class OffloadedPipeline:
    """
    Wrapper for pipelines with automatic offloading
    
    Usage:
        with OffloadedPipeline(pipe, strategy="model_cpu") as optimized_pipe:
            result = optimized_pipe(prompt=...)
    """
    
    def __init__(
        self,
        pipe: Any,
        strategy: Optional[Union[str, OffloadStrategy]] = None,
        target_vram_gb: Optional[float] = None,
        device_id: int = 0,
    ):
        self.pipe = pipe
        self.optimizer = get_memory_optimizer()
        self.device_id = device_id
        
        if isinstance(strategy, str):
            strategy = OffloadStrategy(strategy)
        
        self.strategy = strategy
        self.target_vram = target_vram_gb
    
    def __enter__(self):
        if self.target_vram:
            self.pipe = self.optimizer.optimize_for_vram(
                self.pipe,
                self.target_vram,
                self.device_id
            )
        elif self.strategy:
            self.pipe = self.optimizer.apply_optimizations(
                self.pipe,
                self.strategy,
                self.device_id
            )
        
        return self.pipe
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.optimizer.cleanup()
        return False


# =============================================================================
# Specialized Loaders
# =============================================================================

def load_model_optimized(
    model_class: type,
    model_path: str,
    device_id: int = 0,
    strategy: Optional[OffloadStrategy] = None,
    quantization: Optional[QuantizationType] = None,
    **kwargs
) -> Any:
    """
    Load a model with automatic optimization
    
    Args:
        model_class: Model class (e.g., StableDiffusionXLPipeline)
        model_path: Model path or HF repo
        device_id: GPU device ID
        strategy: Offload strategy
        quantization: Quantization type
        **kwargs: Additional model arguments
    """
    optimizer = get_memory_optimizer()
    
    # Determine optimal dtype
    quant = quantization or optimizer.config.quantization
    if quant == QuantizationType.BF16 and torch.cuda.is_bf16_supported():
        dtype = torch.bfloat16
    else:
        dtype = torch.float16
    
    # Load model
    logger.info(f"Loading model from {model_path} with dtype {dtype}")
    
    model_kwargs = {
        "torch_dtype": dtype,
        "use_safetensors": True,
        **kwargs
    }
    
    # Check for local path
    local_path = Path(model_path)
    if local_path.exists():
        pipe = model_class.from_pretrained(str(local_path), **model_kwargs)
    else:
        pipe = model_class.from_pretrained(model_path, **model_kwargs)
    
    # Apply optimizations
    strategy = strategy or optimizer.get_recommended_strategy(device_id)
    pipe = optimizer.apply_optimizations(pipe, strategy, device_id)
    
    # Apply quantization if needed
    if quant not in [QuantizationType.NONE, QuantizationType.FP16, QuantizationType.BF16]:
        pipe = optimizer.apply_quantization(pipe, quant)
    
    return pipe


# Singleton
def get_memory_optimizer() -> MemoryOptimizer:
    """Get memory optimizer singleton"""
    return MemoryOptimizer()
