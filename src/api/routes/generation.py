from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException
from sqlalchemy import select

from src.core.dependencies import DBSession
from src.models.character import Character
from src.models.generation import ImageGeneration, VideoGeneration
from src.schemas.character import CharacterStatus
from src.schemas.generation import (
    GenerationStatus,
    ImageGenerationRequest,
    ImageGenerationResponse,
    VideoGenerationRequest,
    VideoGenerationResponse,
)
from src.services.comfyui.image_generator import generate_image_task
from src.services.comfyui.video_generator import generate_video_task

router = APIRouter()


async def get_ready_character(db: DBSession, character_id: UUID) -> Character:
    """Get a character that is ready for generation."""
    result = await db.execute(select(Character).where(Character.id == character_id))
    character = result.scalar_one_or_none()

    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    if character.status != CharacterStatus.READY.value:
        raise HTTPException(
            status_code=400,
            detail=f"Character not ready for generation. Current status: {character.status}"
        )

    if not character.lora_path:
        raise HTTPException(
            status_code=400,
            detail="Character LoRA training not complete. Please wait for training to finish."
        )

    return character


@router.post("/generate-image", response_model=ImageGenerationResponse, status_code=202)
async def generate_image(
    request: ImageGenerationRequest,
    background_tasks: BackgroundTasks,
    db: DBSession,
):
    """
    Generate an image with a character.

    The image is generated asynchronously. Poll the returned ID for status updates.
    """
    character = await get_ready_character(db, request.character_id)

    # Create generation record
    generation = ImageGeneration(
        character_id=character.id,
        status=GenerationStatus.PENDING.value,
        prompt=request.prompt,
        negative_prompt=request.negative_prompt,
        width=request.width,
        height=request.height,
        num_inference_steps=request.num_inference_steps,
        guidance_scale=request.guidance_scale,
        lora_strength=request.lora_strength,
        seed=request.seed,
    )

    db.add(generation)
    await db.flush()
    await db.refresh(generation)

    # Start generation in background
    background_tasks.add_task(
        generate_image_task,
        generation_id=generation.id,
        character=character,
        request=request,
    )

    return generation


@router.get("/generate-image/{generation_id}", response_model=ImageGenerationResponse)
async def get_image_generation_status(generation_id: UUID, db: DBSession):
    """Get the status of an image generation."""
    result = await db.execute(
        select(ImageGeneration).where(ImageGeneration.id == generation_id)
    )
    generation = result.scalar_one_or_none()

    if not generation:
        raise HTTPException(status_code=404, detail="Generation not found")

    return generation


@router.post("/generate-video", response_model=VideoGenerationResponse, status_code=202)
async def generate_video(
    request: VideoGenerationRequest,
    background_tasks: BackgroundTasks,
    db: DBSession,
):
    """
    Generate a video with a character.

    The video is generated asynchronously. Poll the returned ID for status updates.
    If no source_image_url is provided, an image will be generated first.
    """
    character = await get_ready_character(db, request.character_id)

    # Create generation record
    generation = VideoGeneration(
        character_id=character.id,
        status=GenerationStatus.PENDING.value,
        prompt=request.prompt,
        source_image_url=request.source_image_url,
        width=request.width,
        height=request.height,
        num_frames=request.num_frames,
        fps=request.fps,
        motion_bucket_id=request.motion_bucket_id,
        seed=request.seed,
    )

    db.add(generation)
    await db.flush()
    await db.refresh(generation)

    # Start generation in background
    background_tasks.add_task(
        generate_video_task,
        generation_id=generation.id,
        character=character,
        request=request,
    )

    return generation


@router.get("/generate-video/{generation_id}", response_model=VideoGenerationResponse)
async def get_video_generation_status(generation_id: UUID, db: DBSession):
    """Get the status of a video generation."""
    result = await db.execute(
        select(VideoGeneration).where(VideoGeneration.id == generation_id)
    )
    generation = result.scalar_one_or_none()

    if not generation:
        raise HTTPException(status_code=404, detail="Generation not found")

    return generation
