import json
import random
from pathlib import Path
from uuid import UUID

from src.core.config import get_settings
from src.core.database import async_session_maker
from src.models.character import Character
from src.models.generation import ImageGeneration
from src.schemas.generation import GenerationStatus, ImageGenerationRequest
from src.services.comfyui.client import comfyui_client
from src.services.storage.manager import storage_manager

settings = get_settings()

WORKFLOW_PATH = Path(__file__).parent.parent.parent.parent / "workflows" / "sdxl_lora_image.json"


def load_image_workflow() -> dict:
    """Load the SDXL LoRA image generation workflow template."""
    with open(WORKFLOW_PATH) as f:
        return json.load(f)


def build_image_workflow(
    character: Character,
    request: ImageGenerationRequest,
) -> dict:
    """
    Build the workflow with character LoRA and generation parameters.

    The workflow template uses placeholder values that we replace here.
    This is the key to the "single workflow serves all characters" pattern.
    """
    workflow = load_image_workflow()

    seed = request.seed if request.seed is not None else random.randint(0, 2**32 - 1)

    # These node IDs match the workflow template structure
    # Adjust based on your actual ComfyUI workflow export

    # KSampler node
    if "3" in workflow:
        workflow["3"]["inputs"]["seed"] = seed
        workflow["3"]["inputs"]["steps"] = request.num_inference_steps
        workflow["3"]["inputs"]["cfg"] = request.guidance_scale

    # Empty Latent Image node
    if "5" in workflow:
        workflow["5"]["inputs"]["width"] = request.width
        workflow["5"]["inputs"]["height"] = request.height

    # CLIP Text Encode (positive prompt)
    if "6" in workflow:
        # Include trigger word in prompt
        full_prompt = f"{character.trigger_word}, {request.prompt}"
        workflow["6"]["inputs"]["text"] = full_prompt

    # CLIP Text Encode (negative prompt)
    if "7" in workflow:
        workflow["7"]["inputs"]["text"] = request.negative_prompt

    # LoRA Loader node
    if "10" in workflow:
        workflow["10"]["inputs"]["lora_name"] = Path(character.lora_path).name
        workflow["10"]["inputs"]["strength_model"] = request.lora_strength
        workflow["10"]["inputs"]["strength_clip"] = request.lora_strength

    return workflow


async def update_generation_status(
    generation_id: UUID,
    status: GenerationStatus,
    image_url: str | None = None,
    error: str | None = None,
) -> None:
    """Update generation status in database."""
    async with async_session_maker() as session:
        from sqlalchemy import select
        result = await session.execute(
            select(ImageGeneration).where(ImageGeneration.id == generation_id)
        )
        generation = result.scalar_one_or_none()
        if generation:
            generation.status = status.value
            if image_url:
                generation.image_url = image_url
            if error:
                generation.error = error
            await session.commit()


async def generate_image_task(
    generation_id: UUID,
    character: Character,
    request: ImageGenerationRequest,
) -> None:
    """
    Background task to generate an image.

    1. Build workflow with character LoRA
    2. Execute via ComfyUI
    3. Upload result to cloud storage
    4. Update database with result URL
    """
    try:
        await update_generation_status(generation_id, GenerationStatus.PROCESSING)

        # Build and execute workflow
        workflow = build_image_workflow(character, request)
        outputs = await comfyui_client.execute_workflow(workflow)

        # Find the output image
        image_data = None
        for node_id, node_output in outputs.items():
            if "images" in node_output:
                for img in node_output["images"]:
                    filename = img.get("filename")
                    subfolder = img.get("subfolder", "")
                    if filename:
                        image_data = await comfyui_client.get_image(filename, subfolder)
                        break
                if image_data:
                    break

        if not image_data:
            raise RuntimeError("No output image found in workflow results")

        # Upload to cloud storage
        storage_path = f"characters/{character.id}/images/{generation_id}.png"
        image_url = await storage_manager.upload(
            data=image_data,
            path=storage_path,
            content_type="image/png",
        )

        await update_generation_status(
            generation_id,
            GenerationStatus.COMPLETED,
            image_url=image_url,
        )

    except Exception as e:
        await update_generation_status(
            generation_id,
            GenerationStatus.FAILED,
            error=str(e),
        )
        raise
