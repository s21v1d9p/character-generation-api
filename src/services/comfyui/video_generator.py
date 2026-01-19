import json
import random
from pathlib import Path
from uuid import UUID

from src.core.config import get_settings
from src.core.database import async_session_maker
from src.models.character import Character
from src.models.generation import VideoGeneration
from src.schemas.generation import GenerationStatus, VideoGenerationRequest
from src.services.comfyui.client import comfyui_client
from src.services.comfyui.image_generator import build_image_workflow, ImageGenerationRequest
from src.services.storage.manager import storage_manager

settings = get_settings()

WORKFLOW_PATH = Path(__file__).parent.parent.parent.parent / "workflows" / "svd_video.json"


def load_video_workflow() -> dict:
    """Load the SVD video generation workflow template."""
    with open(WORKFLOW_PATH) as f:
        return json.load(f)


def build_video_workflow(
    source_image_path: str,
    request: VideoGenerationRequest,
) -> dict:
    """
    Build the SVD workflow with source image and parameters.

    SVD (Stable Video Diffusion) generates video from a single image.
    """
    workflow = load_video_workflow()

    seed = request.seed if request.seed is not None else random.randint(0, 2**32 - 1)

    # Load Image node - source image for video
    if "1" in workflow:
        workflow["1"]["inputs"]["image"] = source_image_path

    # SVD_img2vid_Conditioning node
    if "2" in workflow:
        workflow["2"]["inputs"]["width"] = request.width
        workflow["2"]["inputs"]["height"] = request.height
        workflow["2"]["inputs"]["video_frames"] = request.num_frames
        workflow["2"]["inputs"]["motion_bucket_id"] = request.motion_bucket_id
        workflow["2"]["inputs"]["fps"] = request.fps

    # KSampler node
    if "3" in workflow:
        workflow["3"]["inputs"]["seed"] = seed

    return workflow


async def update_generation_status(
    generation_id: UUID,
    status: GenerationStatus,
    video_url: str | None = None,
    thumbnail_url: str | None = None,
    error: str | None = None,
) -> None:
    """Update generation status in database."""
    async with async_session_maker() as session:
        from sqlalchemy import select
        result = await session.execute(
            select(VideoGeneration).where(VideoGeneration.id == generation_id)
        )
        generation = result.scalar_one_or_none()
        if generation:
            generation.status = status.value
            if video_url:
                generation.video_url = video_url
            if thumbnail_url:
                generation.thumbnail_url = thumbnail_url
            if error:
                generation.error = error
            await session.commit()


async def generate_video_task(
    generation_id: UUID,
    character: Character,
    request: VideoGenerationRequest,
) -> None:
    """
    Background task to generate a video.

    1. If no source image, generate one first
    2. Build SVD workflow with source image
    3. Execute via ComfyUI
    4. Upload result to cloud storage
    5. Update database with result URL
    """
    try:
        await update_generation_status(generation_id, GenerationStatus.PROCESSING)

        source_image_path = None

        # If no source image provided, generate one first
        if not request.source_image_url:
            # Generate a character image first
            image_request = ImageGenerationRequest(
                character_id=request.character_id,
                prompt=request.prompt,
                width=request.width,
                height=request.height,
            )
            image_workflow = build_image_workflow(character, image_request)
            image_outputs = await comfyui_client.execute_workflow(image_workflow)

            # Get the generated image
            for node_id, node_output in image_outputs.items():
                if "images" in node_output:
                    for img in node_output["images"]:
                        filename = img.get("filename")
                        if filename:
                            source_image_path = filename
                            break
                    if source_image_path:
                        break

            if not source_image_path:
                raise RuntimeError("Failed to generate source image for video")
        else:
            # Download source image and upload to ComfyUI
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(request.source_image_url)
                response.raise_for_status()
                image_data = response.content

            upload_result = await comfyui_client.upload_image(
                image_data,
                f"source_{generation_id}.png"
            )
            source_image_path = upload_result.get("name")

        # Build and execute video workflow
        workflow = build_video_workflow(source_image_path, request)
        outputs = await comfyui_client.execute_workflow(workflow, timeout=600.0)

        # Find the output video
        video_data = None
        for node_id, node_output in outputs.items():
            if "gifs" in node_output:
                for vid in node_output["gifs"]:
                    filename = vid.get("filename")
                    subfolder = vid.get("subfolder", "")
                    if filename:
                        video_data = await comfyui_client.get_image(filename, subfolder)
                        break
                if video_data:
                    break

        if not video_data:
            raise RuntimeError("No output video found in workflow results")

        # Upload to cloud storage
        storage_path = f"characters/{character.id}/videos/{generation_id}.mp4"
        video_url = await storage_manager.upload(
            data=video_data,
            path=storage_path,
            content_type="video/mp4",
        )

        await update_generation_status(
            generation_id,
            GenerationStatus.COMPLETED,
            video_url=video_url,
        )

    except Exception as e:
        await update_generation_status(
            generation_id,
            GenerationStatus.FAILED,
            error=str(e),
        )
        raise
