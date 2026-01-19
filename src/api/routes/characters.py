import re
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, File, Form
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError

from src.core.dependencies import DBSession
from src.models.character import Character
from src.schemas.character import (
    CharacterListResponse,
    CharacterResponse,
    CharacterStatus,
)
from src.services.training.lora_trainer import start_lora_training

router = APIRouter()


def generate_trigger_word(name: str) -> str:
    """Generate a unique trigger word from character name."""
    clean_name = re.sub(r"[^a-zA-Z0-9]", "", name.lower())
    return f"sks_{clean_name}"


@router.get("", response_model=CharacterListResponse)
async def list_characters(db: DBSession, skip: int = 0, limit: int = 100):
    """List all characters."""
    result = await db.execute(
        select(Character).order_by(Character.created_at.desc()).offset(skip).limit(limit)
    )
    characters = result.scalars().all()

    # Efficient count query
    total = await db.scalar(select(func.count()).select_from(Character)) or 0

    return CharacterListResponse(characters=list(characters), total=total)


@router.get("/{character_id}", response_model=CharacterResponse)
async def get_character(character_id: UUID, db: DBSession):
    """Get a character by ID."""
    result = await db.execute(select(Character).where(Character.id == character_id))
    character = result.scalar_one_or_none()

    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    return character


@router.post("", response_model=CharacterResponse, status_code=201)
async def create_character(
    background_tasks: BackgroundTasks,
    db: DBSession,
    name: str = Form(...),
    description: str | None = Form(None),
    trigger_word: str | None = Form(None),
    images: list[UploadFile] = File(..., description="Reference images for LoRA training (10-20 recommended)"),
):
    """
    Create a new character and start LoRA training.

    Upload 10-20 reference images of the character. The system will:
    1. Process and caption the images
    2. Train a LoRA for the character
    3. Register the character for immediate use
    """
    if len(images) < 5:
        raise HTTPException(
            status_code=400,
            detail="At least 5 reference images required (10-20 recommended)"
        )

    if len(images) > 50:
        raise HTTPException(
            status_code=400,
            detail="Maximum 50 images allowed"
        )

    # Generate trigger word if not provided
    final_trigger_word = trigger_word or generate_trigger_word(name)

    # Create character record
    character = Character(
        name=name,
        description=description,
        trigger_word=final_trigger_word,
        status=CharacterStatus.PENDING.value,
    )

    try:
        db.add(character)
        await db.flush()
        await db.refresh(character)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Character with trigger word '{final_trigger_word}' already exists"
        )

    # Start LoRA training in background
    background_tasks.add_task(
        start_lora_training,
        character_id=character.id,
        images=images,
    )

    return character


@router.delete("/{character_id}", status_code=204)
async def delete_character(character_id: UUID, db: DBSession):
    """Delete a character."""
    result = await db.execute(select(Character).where(Character.id == character_id))
    character = result.scalar_one_or_none()

    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    await db.delete(character)
    return None
