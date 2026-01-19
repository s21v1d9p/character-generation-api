import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base


class ImageGeneration(Base):
    __tablename__ = "image_generations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    character_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("characters.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    negative_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    width: Mapped[int] = mapped_column(Integer, nullable=False, default=1024)
    height: Mapped[int] = mapped_column(Integer, nullable=False, default=1024)
    num_inference_steps: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    guidance_scale: Mapped[float] = mapped_column(Float, nullable=False, default=7.5)
    lora_strength: Mapped[float] = mapped_column(Float, nullable=False, default=0.8)
    seed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    character = relationship("Character", backref="image_generations")


class VideoGeneration(Base):
    __tablename__ = "video_generations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    character_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("characters.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    source_image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    width: Mapped[int] = mapped_column(Integer, nullable=False, default=1024)
    height: Mapped[int] = mapped_column(Integer, nullable=False, default=576)
    num_frames: Mapped[int] = mapped_column(Integer, nullable=False, default=25)
    fps: Mapped[int] = mapped_column(Integer, nullable=False, default=6)
    motion_bucket_id: Mapped[int] = mapped_column(Integer, nullable=False, default=127)
    seed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    video_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    thumbnail_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    character = relationship("Character", backref="video_generations")
