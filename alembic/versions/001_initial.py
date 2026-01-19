"""Initial migration

Revision ID: 001
Revises:
Create Date: 2026-01-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create characters table
    op.create_table(
        "characters",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, index=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("trigger_word", sa.String(50), nullable=False, unique=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("lora_path", sa.String(500), nullable=True),
        sa.Column("thumbnail_url", sa.String(500), nullable=True),
        sa.Column("training_images_path", sa.String(500), nullable=True),
        sa.Column("training_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )

    # Create image_generations table
    op.create_table(
        "image_generations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "character_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("characters.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("negative_prompt", sa.Text(), nullable=True),
        sa.Column("width", sa.Integer(), nullable=False, server_default="1024"),
        sa.Column("height", sa.Integer(), nullable=False, server_default="1024"),
        sa.Column("num_inference_steps", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("guidance_scale", sa.Float(), nullable=False, server_default="7.5"),
        sa.Column("lora_strength", sa.Float(), nullable=False, server_default="0.8"),
        sa.Column("seed", sa.Integer(), nullable=True),
        sa.Column("image_url", sa.String(500), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # Create video_generations table
    op.create_table(
        "video_generations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "character_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("characters.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("source_image_url", sa.String(500), nullable=True),
        sa.Column("width", sa.Integer(), nullable=False, server_default="1024"),
        sa.Column("height", sa.Integer(), nullable=False, server_default="576"),
        sa.Column("num_frames", sa.Integer(), nullable=False, server_default="25"),
        sa.Column("fps", sa.Integer(), nullable=False, server_default="6"),
        sa.Column("motion_bucket_id", sa.Integer(), nullable=False, server_default="127"),
        sa.Column("seed", sa.Integer(), nullable=True),
        sa.Column("video_url", sa.String(500), nullable=True),
        sa.Column("thumbnail_url", sa.String(500), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("video_generations")
    op.drop_table("image_generations")
    op.drop_table("characters")
