from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class GenerationStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ImageGenerationRequest(BaseModel):
    character_id: UUID = Field(..., description="Character ID to use for generation")
    prompt: str = Field(..., min_length=1, max_length=1000, description="Generation prompt")
    negative_prompt: str = Field(
        default="blurry, low quality, distorted, deformed",
        max_length=500,
        description="Negative prompt",
    )
    width: int = Field(default=1024, ge=512, le=2048, description="Image width")
    height: int = Field(default=1024, ge=512, le=2048, description="Image height")
    num_inference_steps: int = Field(default=30, ge=10, le=100, description="Number of steps")
    guidance_scale: float = Field(default=7.5, ge=1.0, le=20.0, description="CFG scale")
    lora_strength: float = Field(default=0.8, ge=0.0, le=1.5, description="LoRA strength")
    seed: int | None = Field(default=None, description="Random seed (None for random)")


class ImageGenerationResponse(BaseModel):
    id: UUID
    character_id: UUID
    status: GenerationStatus
    image_url: str | None = None
    prompt: str
    created_at: datetime

    model_config = {"from_attributes": True}


class VideoGenerationRequest(BaseModel):
    character_id: UUID = Field(..., description="Character ID to use for generation")
    prompt: str = Field(..., min_length=1, max_length=1000, description="Generation prompt")
    source_image_url: str | None = Field(
        default=None,
        description="Source image URL (if None, generates image first)",
    )
    width: int = Field(default=1024, ge=512, le=1024, description="Video width")
    height: int = Field(default=576, ge=320, le=576, description="Video height")
    num_frames: int = Field(default=25, ge=14, le=50, description="Number of frames")
    fps: int = Field(default=6, ge=4, le=30, description="Frames per second")
    motion_bucket_id: int = Field(default=127, ge=1, le=255, description="Motion intensity")
    seed: int | None = Field(default=None, description="Random seed (None for random)")


class VideoGenerationResponse(BaseModel):
    id: UUID
    character_id: UUID
    status: GenerationStatus
    video_url: str | None = None
    thumbnail_url: str | None = None
    prompt: str
    created_at: datetime

    model_config = {"from_attributes": True}
