"""
Multi-GPU Support Module
========================

Load balancing and distributed inference across multiple GPUs.
Supports: RTX 5070 (12GB), RTX 3060 Ti (8GB), RTX 3060 Laptop (6GB)

Features:
- Automatic GPU detection
- Load balancing based on VRAM/compute
- Model placement optimization
- Cross-GPU pipeline execution
"""

import logging
import threading
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
import time

import torch

logger = logging.getLogger(__name__)


class GPUTier(str, Enum):
    """GPU capability tiers"""
    HIGH = "high"      # RTX 5070, 4090, etc. (12GB+)
    MEDIUM = "medium"  # RTX 3060 Ti, 4060, etc. (8GB)
    LOW = "low"        # RTX 3060 Laptop, etc. (6GB)
    CPU = "cpu"        # CPU fallback


class LoadBalanceStrategy(str, Enum):
    """Load balancing strategies"""
    ROUND_ROBIN = "round_robin"
    LEAST_LOADED = "least_loaded"
    VRAM_BASED = "vram_based"
    COMPUTE_BASED = "compute_based"


@dataclass
class GPUInfo:
    """Information about a GPU"""
    id: int
    name: str
    total_memory: int  # bytes
    compute_capability: Tuple[int, int]
    tier: GPUTier
    
    # Dynamic stats
    used_memory: int = 0
    free_memory: int = 0
    utilization: float = 0.0
    temperature: int = 0
    
    # Model placement
    loaded_models: List[str] = field(default_factory=list)
    is_available: bool = True
    current_task: Optional[str] = None
    
    @property
    def memory_gb(self) -> float:
        return self.total_memory / (1024 ** 3)
    
    @property
    def free_memory_gb(self) -> float:
        return self.free_memory / (1024 ** 3)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "total_memory_gb": round(self.memory_gb, 2),
            "free_memory_gb": round(self.free_memory_gb, 2),
            "tier": self.tier.value,
            "utilization": self.utilization,
            "loaded_models": self.loaded_models,
            "is_available": self.is_available,
        }


@dataclass 
class MultiGPUConfig:
    """Multi-GPU configuration"""
    # Strategy
    strategy: LoadBalanceStrategy = LoadBalanceStrategy.LEAST_LOADED
    
    # Memory management
    max_memory_percent: float = 0.9  # Don't use more than 90% VRAM
    reserve_memory_gb: float = 1.0   # Reserve 1GB per GPU
    
    # Model placement
    auto_place_models: bool = True
    prefer_high_tier: bool = True
    
    # Fallback
    enable_cpu_fallback: bool = False
    
    # Thresholds for tier assignment
    high_tier_threshold_gb: float = 10.0   # 10GB+ = high
    medium_tier_threshold_gb: float = 7.0  # 7GB+ = medium


class GPUManager:
    """
    Multi-GPU Manager for load balancing and model placement
    
    Features:
    - Detect and monitor all GPUs
    - Load balance across GPUs
    - Optimal model placement
    - Memory management
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
        
        self.config = MultiGPUConfig()
        self.gpus: Dict[int, GPUInfo] = {}
        self.model_registry: Dict[str, int] = {}  # model_name -> gpu_id
        self._lock = threading.Lock()
        self._round_robin_counter = 0
        
        # Detect GPUs
        self._detect_gpus()
        
        self._initialized = True
    
    def _detect_gpus(self):
        """Detect all available GPUs"""
        if not torch.cuda.is_available():
            logger.warning("No CUDA GPUs available")
            return
        
        num_gpus = torch.cuda.device_count()
        logger.info(f"Detected {num_gpus} GPU(s)")
        
        for i in range(num_gpus):
            props = torch.cuda.get_device_properties(i)
            
            # Determine tier
            memory_gb = props.total_memory / (1024 ** 3)
            if memory_gb >= self.config.high_tier_threshold_gb:
                tier = GPUTier.HIGH
            elif memory_gb >= self.config.medium_tier_threshold_gb:
                tier = GPUTier.MEDIUM
            else:
                tier = GPUTier.LOW
            
            gpu_info = GPUInfo(
                id=i,
                name=props.name,
                total_memory=props.total_memory,
                compute_capability=(props.major, props.minor),
                tier=tier,
            )
            
            self._update_gpu_stats(gpu_info)
            self.gpus[i] = gpu_info
            
            logger.info(
                f"GPU {i}: {props.name} - {memory_gb:.1f}GB VRAM - Tier: {tier.value}"
            )
    
    def _update_gpu_stats(self, gpu: GPUInfo):
        """Update GPU memory stats"""
        try:
            torch.cuda.set_device(gpu.id)
            
            # Memory info
            gpu.free_memory = torch.cuda.mem_get_info(gpu.id)[0]
            gpu.used_memory = gpu.total_memory - gpu.free_memory
            
            # Try to get utilization (requires pynvml)
            try:
                import pynvml
                pynvml.nvmlInit()
                handle = pynvml.nvmlDeviceGetHandleByIndex(gpu.id)
                util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                gpu.utilization = util.gpu / 100.0
                gpu.temperature = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
            except ImportError:
                pass
            except Exception as e:
                logger.debug(f"Could not get GPU utilization: {e}")
                
        except Exception as e:
            logger.warning(f"Could not update GPU {gpu.id} stats: {e}")
    
    def refresh_stats(self):
        """Refresh all GPU stats"""
        for gpu in self.gpus.values():
            self._update_gpu_stats(gpu)
    
    def get_gpu(self, gpu_id: int) -> Optional[GPUInfo]:
        """Get GPU info by ID"""
        return self.gpus.get(gpu_id)
    
    def get_all_gpus(self) -> List[GPUInfo]:
        """Get all GPUs"""
        return list(self.gpus.values())
    
    def get_best_gpu(
        self,
        required_memory_gb: float = 0,
        prefer_tier: Optional[GPUTier] = None,
    ) -> Optional[GPUInfo]:
        """
        Get best available GPU based on strategy
        
        Args:
            required_memory_gb: Minimum required VRAM
            prefer_tier: Preferred GPU tier
        """
        self.refresh_stats()
        
        available = [
            gpu for gpu in self.gpus.values()
            if gpu.is_available and gpu.free_memory_gb >= required_memory_gb
        ]
        
        if not available:
            if self.config.enable_cpu_fallback:
                logger.warning("No GPU available, falling back to CPU")
                return None
            raise RuntimeError("No GPU with sufficient memory available")
        
        # Filter by tier if specified
        if prefer_tier:
            tier_gpus = [g for g in available if g.tier == prefer_tier]
            if tier_gpus:
                available = tier_gpus
        
        # Apply strategy
        if self.config.strategy == LoadBalanceStrategy.ROUND_ROBIN:
            with self._lock:
                idx = self._round_robin_counter % len(available)
                self._round_robin_counter += 1
            return available[idx]
        
        elif self.config.strategy == LoadBalanceStrategy.LEAST_LOADED:
            return min(available, key=lambda g: g.utilization)
        
        elif self.config.strategy == LoadBalanceStrategy.VRAM_BASED:
            return max(available, key=lambda g: g.free_memory)
        
        elif self.config.strategy == LoadBalanceStrategy.COMPUTE_BASED:
            return max(available, key=lambda g: g.compute_capability)
        
        return available[0]
    
    def get_gpu_for_model(
        self,
        model_name: str,
        model_size_gb: float,
    ) -> int:
        """
        Get best GPU for loading a model
        
        Args:
            model_name: Name of the model
            model_size_gb: Model size in GB
        """
        # Check if already loaded
        if model_name in self.model_registry:
            return self.model_registry[model_name]
        
        # Find best GPU
        required = model_size_gb + self.config.reserve_memory_gb
        
        # Prefer high tier for large models
        prefer_tier = None
        if self.config.prefer_high_tier and model_size_gb > 4:
            prefer_tier = GPUTier.HIGH
        
        gpu = self.get_best_gpu(
            required_memory_gb=required,
            prefer_tier=prefer_tier,
        )
        
        if gpu is None:
            if self.config.enable_cpu_fallback:
                return -1  # CPU
            raise RuntimeError(f"No GPU can fit model {model_name} ({model_size_gb}GB)")
        
        # Register model
        self.model_registry[model_name] = gpu.id
        gpu.loaded_models.append(model_name)
        
        logger.info(f"Assigned model '{model_name}' to GPU {gpu.id} ({gpu.name})")
        
        return gpu.id
    
    def release_model(self, model_name: str):
        """Release a model from GPU"""
        if model_name in self.model_registry:
            gpu_id = self.model_registry[model_name]
            del self.model_registry[model_name]
            
            if gpu_id in self.gpus:
                gpu = self.gpus[gpu_id]
                if model_name in gpu.loaded_models:
                    gpu.loaded_models.remove(model_name)
            
            logger.info(f"Released model '{model_name}' from GPU {gpu_id}")
    
    def set_gpu_available(self, gpu_id: int, available: bool):
        """Set GPU availability"""
        if gpu_id in self.gpus:
            self.gpus[gpu_id].is_available = available
    
    def get_device(self, gpu_id: Optional[int] = None) -> torch.device:
        """Get torch device for GPU"""
        if gpu_id is None:
            gpu = self.get_best_gpu()
            gpu_id = gpu.id if gpu else -1
        
        if gpu_id < 0:
            return torch.device("cpu")
        
        return torch.device(f"cuda:{gpu_id}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get multi-GPU statistics"""
        self.refresh_stats()
        
        total_memory = sum(g.total_memory for g in self.gpus.values())
        free_memory = sum(g.free_memory for g in self.gpus.values())
        
        return {
            "num_gpus": len(self.gpus),
            "total_memory_gb": round(total_memory / (1024**3), 2),
            "free_memory_gb": round(free_memory / (1024**3), 2),
            "strategy": self.config.strategy.value,
            "gpus": [gpu.to_dict() for gpu in self.gpus.values()],
            "model_placement": self.model_registry.copy(),
        }


class ModelPlacer:
    """
    Optimal model placement across GPUs
    
    Assigns models to GPUs based on:
    - Model size
    - GPU memory
    - Inference frequency
    - Model dependencies
    """
    
    def __init__(self, gpu_manager: GPUManager):
        self.gpu_manager = gpu_manager
        self.model_sizes: Dict[str, float] = {
            # Base models
            "sdxl": 6.5,
            "sdxl_refiner": 6.2,
            "sd15": 4.3,
            "flux": 12.0,
            "animagine": 6.5,
            
            # ControlNet
            "controlnet_canny": 2.5,
            "controlnet_depth": 2.5,
            "controlnet_openpose": 2.5,
            
            # Identity
            "instantid": 2.0,
            "pulid": 2.0,
            "ecomid": 3.0,
            "ip_adapter": 0.5,
            
            # Edit
            "instruct_pix2pix": 5.0,
            "step1x": 7.0,
            "qwen_edit": 40.0,
            
            # Utilities
            "sam": 1.2,
            "lama": 0.2,
            "realesrgan": 0.1,
            "gfpgan": 0.4,
        }
    
    def plan_placement(
        self,
        models: List[str],
    ) -> Dict[str, int]:
        """
        Plan optimal placement for multiple models
        
        Args:
            models: List of model names to place
            
        Returns:
            Dict mapping model name to GPU ID
        """
        placement = {}
        
        # Sort by size (largest first)
        models_with_size = [
            (m, self.model_sizes.get(m, 5.0))
            for m in models
        ]
        models_with_size.sort(key=lambda x: -x[1])
        
        for model_name, size in models_with_size:
            try:
                gpu_id = self.gpu_manager.get_gpu_for_model(model_name, size)
                placement[model_name] = gpu_id
            except RuntimeError as e:
                logger.warning(f"Could not place model {model_name}: {e}")
                placement[model_name] = -1  # CPU fallback
        
        return placement
    
    def get_recommended_config(self) -> Dict[str, Any]:
        """Get recommended model configuration based on available GPUs"""
        gpus = self.gpu_manager.get_all_gpus()
        total_vram = sum(g.memory_gb for g in gpus)
        
        config = {
            "recommended_models": [],
            "warnings": [],
        }
        
        # Basic recommendations
        if total_vram >= 12:
            config["recommended_models"].extend([
                "sdxl", "animagine", "instruct_pix2pix",
                "controlnet_canny", "ip_adapter", "instantid",
                "sam", "realesrgan", "gfpgan"
            ])
        elif total_vram >= 8:
            config["recommended_models"].extend([
                "sd15", "instruct_pix2pix",
                "controlnet_canny", "ip_adapter",
                "sam", "realesrgan"
            ])
            config["warnings"].append("Limited VRAM - SDXL may need CPU offloading")
        else:
            config["recommended_models"].extend([
                "sd15", "realesrgan"
            ])
            config["warnings"].append("Low VRAM - Consider using CPU offloading")
        
        # Check for large models
        if total_vram < 24:
            config["warnings"].append("Qwen-Image-Edit (40GB) requires multi-GPU or quantization")
        
        if total_vram < 12:
            config["warnings"].append("Step1X-Edit (7GB) may be slow on this setup")
        
        return config


# =============================================================================
# GPU-aware Context Manager
# =============================================================================

class GPUContext:
    """Context manager for GPU-aware operations"""
    
    def __init__(
        self,
        gpu_manager: GPUManager,
        required_memory_gb: float = 0,
        model_name: Optional[str] = None,
    ):
        self.gpu_manager = gpu_manager
        self.required_memory = required_memory_gb
        self.model_name = model_name
        self.gpu: Optional[GPUInfo] = None
        self.device: Optional[torch.device] = None
    
    def __enter__(self) -> torch.device:
        if self.model_name:
            gpu_id = self.gpu_manager.get_gpu_for_model(
                self.model_name,
                self.required_memory
            )
            self.gpu = self.gpu_manager.get_gpu(gpu_id)
            self.device = torch.device(f"cuda:{gpu_id}" if gpu_id >= 0 else "cpu")
        else:
            self.gpu = self.gpu_manager.get_best_gpu(self.required_memory)
            if self.gpu:
                self.device = torch.device(f"cuda:{self.gpu.id}")
            else:
                self.device = torch.device("cpu")
        
        if self.gpu:
            self.gpu.current_task = self.model_name
        
        return self.device
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.gpu:
            self.gpu.current_task = None
        return False


# Singleton
def get_gpu_manager() -> GPUManager:
    """Get GPU manager singleton"""
    return GPUManager()


def get_model_placer() -> ModelPlacer:
    """Get model placer singleton"""
    return ModelPlacer(get_gpu_manager())
