from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = False
    api_key: str = ""  # Required for production
    allowed_origins: str = ""  # Comma-separated list of allowed origins

    # Database
    database_url: str

    # RunPod
    runpod_api_key: str = ""
    runpod_endpoint_id: str = ""

    # ComfyUI
    comfyui_url: str = "ws://localhost:8188/ws"
    comfyui_http_url: str = "http://localhost:8188"

    # Storage
    storage_provider: Literal["s3", "supabase"] = "s3"

    # S3
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"
    s3_bucket: str = "character-gen-assets"

    # Supabase
    supabase_url: str = ""
    supabase_key: str = ""
    supabase_bucket: str = "character-gen-assets"

    # LoRA
    lora_output_dir: str = "/models/loras"
    lora_training_steps: int = 1500
    lora_learning_rate: float = 1e-4

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Models
    sdxl_model_path: str = "/models/checkpoints/sd_xl_base_1.0.safetensors"
    svd_model_path: str = "/models/checkpoints/svd_xt_1_1.safetensors"


@lru_cache
def get_settings() -> Settings:
    return Settings()
