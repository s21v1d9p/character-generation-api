from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class CharacterStatus(str, Enum):
    PENDING = "pending"
    TRAINING = "training"
    READY = "ready"
    FAILED = "failed"


class CharacterCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Character name")
    description: str | None = Field(None, max_length=500, description="Character description")
    trigger_word: str | None = Field(
        None,
        max_length=50,
        description="Trigger word for LoRA activation (auto-generated if not provided)",
    )


class CharacterResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    trigger_word: str
    status: CharacterStatus
    lora_path: str | None
    thumbnail_url: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CharacterListResponse(BaseModel):
    characters: list[CharacterResponse]
    total: int
