import asyncio
import json
import logging
import os
import shutil
import tempfile
from pathlib import Path
from uuid import UUID

import aiofiles
from fastapi import UploadFile

from src.core.config import get_settings
from src.core.database import async_session_maker
from src.models.character import Character
from src.schemas.character import CharacterStatus
from src.services.storage.manager import storage_manager

settings = get_settings()
logger = logging.getLogger(__name__)


class TrainingDependencyError(Exception):
    """Raised when training dependencies are not available."""

    pass


async def verify_training_dependencies() -> None:
    """
    Verify that training dependencies are available.

    Raises TrainingDependencyError if requirements not met.
    """
    training_script = os.environ.get("LORA_TRAINING_SCRIPT", "")

    if training_script:
        # Custom script path provided - verify it exists
        script_path = Path(training_script.split()[0])  # Get first part of command
        if not script_path.exists() and not shutil.which(script_path.name):
            raise TrainingDependencyError(
                f"Training script not found: {training_script}. "
                "Please set LORA_TRAINING_SCRIPT to a valid path or ensure kohya_ss is installed."
            )
    else:
        # Check for kohya_ss installation
        try:
            process = await asyncio.create_subprocess_shell(
                "python -c 'import kohya_ss'",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await process.communicate()
            if process.returncode != 0:
                raise TrainingDependencyError(
                    "kohya_ss not installed. Please install it or set LORA_TRAINING_SCRIPT "
                    "environment variable to your training script path."
                )
        except Exception as e:
            logger.warning(f"Could not verify kohya_ss installation: {e}")
            # Don't fail here - will fail at training time with better error


async def update_character_status(
    character_id: UUID,
    status: CharacterStatus,
    lora_path: str | None = None,
    thumbnail_url: str | None = None,
    error: str | None = None,
) -> None:
    """Update character training status in database."""
    async with async_session_maker() as session:
        from sqlalchemy import select
        result = await session.execute(
            select(Character).where(Character.id == character_id)
        )
        character = result.scalar_one_or_none()
        if character:
            character.status = status.value
            if lora_path:
                character.lora_path = lora_path
            if thumbnail_url:
                character.thumbnail_url = thumbnail_url
            if error:
                character.training_error = error
            await session.commit()


async def save_uploaded_images(
    images: list[UploadFile],
    output_dir: Path,
) -> list[Path]:
    """Save uploaded images to a directory."""
    saved_paths = []

    for i, image in enumerate(images):
        ext = Path(image.filename or "image.png").suffix or ".png"
        filename = f"{i:04d}{ext}"
        output_path = output_dir / filename

        async with aiofiles.open(output_path, "wb") as f:
            content = await image.read()
            await f.write(content)

        saved_paths.append(output_path)

    return saved_paths


def generate_captions(image_dir: Path, trigger_word: str) -> None:
    """
    Generate caption files for training images.

    For LoRA training, each image needs a corresponding .txt file with the caption.
    We use a simple pattern: trigger_word, description of the character
    """
    for image_path in image_dir.iterdir():
        if image_path.suffix.lower() in [".png", ".jpg", ".jpeg", ".webp"]:
            caption_path = image_path.with_suffix(".txt")
            # Simple caption with trigger word
            caption = f"{trigger_word}, a photo of a person"
            caption_path.write_text(caption)


def build_training_config(
    image_dir: Path,
    output_dir: Path,
    trigger_word: str,
    character_name: str,
) -> dict:
    """
    Build training configuration for kohya_ss or similar trainer.

    This configuration follows the kohya_ss LoRA training format.
    """
    return {
        "pretrained_model_name_or_path": settings.sdxl_model_path,
        "train_data_dir": str(image_dir),
        "output_dir": str(output_dir),
        "output_name": f"lora_{character_name}",
        "resolution": "1024,1024",
        "train_batch_size": 1,
        "learning_rate": settings.lora_learning_rate,
        "max_train_steps": settings.lora_training_steps,
        "save_every_n_steps": 500,
        "mixed_precision": "bf16",
        "save_precision": "bf16",
        "network_module": "networks.lora",
        "network_dim": 32,
        "network_alpha": 16,
        "optimizer_type": "AdamW8bit",
        "lr_scheduler": "cosine",
        "lr_warmup_steps": 100,
        "caption_extension": ".txt",
        "shuffle_caption": True,
        "keep_tokens": 1,
        "seed": 42,
        "xformers": True,
        "cache_latents": True,
        "cache_latents_to_disk": True,
    }


async def run_training_subprocess(config: dict, work_dir: Path) -> Path:
    """
    Run the LoRA training process.

    This calls the training script (kohya_ss or similar) as a subprocess.
    In production on RunPod, this would be the actual training command.
    """
    config_path = work_dir / "training_config.json"

    import json
    config_path.write_text(json.dumps(config, indent=2))

    # The actual training command depends on your setup
    # This is a placeholder for the kohya_ss training command
    training_script = os.environ.get(
        "LORA_TRAINING_SCRIPT",
        "python -m kohya_ss.train_network"
    )

    cmd = f"{training_script} --config_file {config_path}"

    process = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=str(work_dir),
    )

    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        error_msg = stderr.decode() if stderr else "Unknown training error"
        raise RuntimeError(f"Training failed: {error_msg}")

    # Find the output LoRA file
    output_dir = Path(config["output_dir"])
    lora_files = list(output_dir.glob("*.safetensors"))

    if not lora_files:
        raise RuntimeError("No LoRA file found after training")

    return lora_files[0]


async def start_lora_training(
    character_id: UUID,
    images: list[UploadFile],
) -> None:
    """
    Main LoRA training pipeline.

    1. Save uploaded images to temp directory
    2. Generate captions for each image
    3. Run training
    4. Upload trained LoRA to storage
    5. Update character with LoRA path
    """
    work_dir = None

    try:
        # Get character info
        async with async_session_maker() as session:
            from sqlalchemy import select
            result = await session.execute(
                select(Character).where(Character.id == character_id)
            )
            character = result.scalar_one_or_none()

            if not character:
                raise RuntimeError(f"Character {character_id} not found")

            trigger_word = character.trigger_word
            character_name = character.name.replace(" ", "_").lower()

        await update_character_status(character_id, CharacterStatus.TRAINING)

        # Create working directory
        work_dir = Path(tempfile.mkdtemp(prefix=f"lora_training_{character_id}_"))
        image_dir = work_dir / "images" / f"1_{trigger_word}"
        image_dir.mkdir(parents=True)
        output_dir = work_dir / "output"
        output_dir.mkdir()

        # Save images
        await save_uploaded_images(images, image_dir)

        # Generate captions
        generate_captions(image_dir, trigger_word)

        # Build config and run training
        config = build_training_config(
            image_dir=image_dir.parent,  # kohya expects parent dir
            output_dir=output_dir,
            trigger_word=trigger_word,
            character_name=character_name,
        )

        lora_path = await run_training_subprocess(config, work_dir)

        # Upload LoRA to storage
        async with aiofiles.open(lora_path, "rb") as f:
            lora_data = await f.read()

        storage_path = f"loras/{character_id}/{lora_path.name}"
        lora_url = await storage_manager.upload(
            data=lora_data,
            path=storage_path,
            content_type="application/octet-stream",
        )

        # Copy LoRA to local models directory for ComfyUI access
        local_lora_path = Path(settings.lora_output_dir) / lora_path.name
        local_lora_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(lora_path, local_lora_path)

        # Create thumbnail from first training image
        thumbnail_url = None
        first_image = next(image_dir.iterdir(), None)
        if first_image and first_image.suffix.lower() in [".png", ".jpg", ".jpeg"]:
            async with aiofiles.open(first_image, "rb") as f:
                thumb_data = await f.read()
            thumbnail_path = f"characters/{character_id}/thumbnail.png"
            thumbnail_url = await storage_manager.upload(
                data=thumb_data,
                path=thumbnail_path,
                content_type="image/png",
            )

        await update_character_status(
            character_id,
            CharacterStatus.READY,
            lora_path=str(local_lora_path),
            thumbnail_url=thumbnail_url,
        )

    except Exception as e:
        await update_character_status(
            character_id,
            CharacterStatus.FAILED,
            error=str(e),
        )
        raise

    finally:
        # Cleanup
        if work_dir and work_dir.exists():
            shutil.rmtree(work_dir, ignore_errors=True)
