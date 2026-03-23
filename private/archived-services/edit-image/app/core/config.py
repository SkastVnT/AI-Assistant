"""
Configuration module for Edit Image Service.
Loads settings from YAML file and provides typed access.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional, List
from functools import lru_cache

import yaml
from pydantic import BaseModel, Field


class ServerSettings(BaseModel):
    """Server configuration."""
    host: str = "0.0.0.0"
    port: int = 8100
    workers: int = 1
    reload: bool = True
    log_level: str = "info"


class ModelConfig(BaseModel):
    """Individual model configuration."""
    name: str
    type: str = "sdxl"
    vram: int = 8
    enabled: bool = True


class ModelsSettings(BaseModel):
    """Models configuration."""
    default: str = "sdxl"
    cache_dir: str = "./models"
    base_models: Dict[str, ModelConfig] = {}
    edit_models: Dict[str, ModelConfig] = {}


class ControlNetModel(BaseModel):
    """ControlNet model configuration."""
    name: str
    enabled: bool = True


class ControlNetSettings(BaseModel):
    """ControlNet configuration."""
    enabled: bool = True
    models: Dict[str, ControlNetModel] = {}
    sdxl: Dict[str, ControlNetModel] = {}


class IPAdapterModel(BaseModel):
    """IP-Adapter model configuration."""
    name: str
    type: str = "base"
    enabled: bool = True


class IPAdapterSettings(BaseModel):
    """IP-Adapter configuration."""
    enabled: bool = True
    models: Dict[str, IPAdapterModel] = {}


class IdentityModelConfig(BaseModel):
    """Identity preservation model configuration."""
    enabled: bool = False
    model: str = ""


class IdentitySettings(BaseModel):
    """Identity preservation configuration."""
    instant_id: IdentityModelConfig = IdentityModelConfig()
    pulid: IdentityModelConfig = IdentityModelConfig()
    ecom_id: IdentityModelConfig = IdentityModelConfig()


class InferenceDefaults(BaseModel):
    """Default inference parameters."""
    num_inference_steps: int = 30
    guidance_scale: float = 7.5
    strength: float = 0.75
    width: int = 1024
    height: int = 1024


class OptimizationSettings(BaseModel):
    """Memory optimization settings."""
    enable_xformers: bool = True
    enable_attention_slicing: bool = True
    enable_vae_slicing: bool = True
    enable_model_cpu_offload: bool = False
    enable_sequential_cpu_offload: bool = False


class InferenceSettings(BaseModel):
    """Inference configuration."""
    device: str = "cuda"
    dtype: str = "float16"
    batch_size: int = 1
    default: InferenceDefaults = InferenceDefaults()
    optimization: OptimizationSettings = OptimizationSettings()


class UpscalerModel(BaseModel):
    """Upscaler model configuration."""
    name: str
    scale: int = 4


class UpscalerSettings(BaseModel):
    """Upscaler configuration."""
    enabled: bool = True
    default: str = "realesrgan"
    models: Dict[str, UpscalerModel] = {}


class FaceRestoreModel(BaseModel):
    """Face restoration model configuration."""
    name: str
    enabled: bool = True


class FaceRestoreSettings(BaseModel):
    """Face restoration configuration."""
    enabled: bool = True
    default: str = "gfpgan"
    models: Dict[str, FaceRestoreModel] = {}


class SearchProvider(BaseModel):
    """Search provider configuration."""
    enabled: bool = False
    api_key: str = ""


class CharacterDBSettings(BaseModel):
    """Character database configuration."""
    danbooru: bool = True
    gelbooru: bool = True
    myanimelist: bool = True


class WebSearchSettings(BaseModel):
    """Web search configuration."""
    enabled: bool = True
    providers: Dict[str, SearchProvider] = {}
    character_db: CharacterDBSettings = CharacterDBSettings()


class OutputSettings(BaseModel):
    """Output configuration."""
    directory: str = "./outputs"
    format: str = "png"
    quality: int = 95
    save_metadata: bool = True


class LoggingSettings(BaseModel):
    """Logging configuration."""
    level: str = "INFO"
    file: str = "./logs/edit-image.log"
    rotation: str = "1 day"
    retention: str = "7 days"


class Settings(BaseModel):
    """Main settings container."""
    server: ServerSettings = ServerSettings()
    models: ModelsSettings = ModelsSettings()
    controlnet: ControlNetSettings = ControlNetSettings()
    ip_adapter: IPAdapterSettings = IPAdapterSettings()
    identity: IdentitySettings = IdentitySettings()
    inference: InferenceSettings = InferenceSettings()
    upscaler: UpscalerSettings = UpscalerSettings()
    face_restore: FaceRestoreSettings = FaceRestoreSettings()
    web_search: WebSearchSettings = WebSearchSettings()
    output: OutputSettings = OutputSettings()
    logging: LoggingSettings = LoggingSettings()
    
    @classmethod
    def from_yaml(cls, path: str) -> "Settings":
        """Load settings from YAML file."""
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls(**data)
    
    def get_enabled_base_models(self) -> List[str]:
        """Get list of enabled base models."""
        return [
            name for name, config in self.models.base_models.items()
            if config.enabled
        ]
    
    def get_enabled_controlnets(self, sdxl: bool = False) -> List[str]:
        """Get list of enabled ControlNet models."""
        models = self.controlnet.sdxl if sdxl else self.controlnet.models
        return [
            name for name, config in models.items()
            if config.enabled
        ]
    
    def get_model_config(self, model_name: str) -> Optional[ModelConfig]:
        """Get configuration for a specific model."""
        if model_name in self.models.base_models:
            return self.models.base_models[model_name]
        if model_name in self.models.edit_models:
            return self.models.edit_models[model_name]
        return None


# Global settings instance
_settings: Optional[Settings] = None


def load_settings(config_path: Optional[str] = None) -> Settings:
    """Load settings from configuration file."""
    global _settings
    
    if config_path is None:
        # Find config file relative to this file
        base_dir = Path(__file__).parent.parent.parent
        config_path = base_dir / "config" / "settings.yaml"
    else:
        config_path = Path(config_path)
    
    if config_path.exists():
        _settings = Settings.from_yaml(str(config_path))
    else:
        # Use default settings
        _settings = Settings()
    
    return _settings


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    global _settings
    if _settings is None:
        _settings = load_settings()
    return _settings


def reload_settings(config_path: Optional[str] = None) -> Settings:
    """Reload settings from configuration file."""
    get_settings.cache_clear()
    return load_settings(config_path)
