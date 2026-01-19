import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.schemas.generation import (
    ImageGenerationRequest,
    VideoGenerationRequest,
    GenerationStatus,
)


class TestImageGenerationRequest:
    def test_valid_request(self):
        """Test creating a valid image generation request."""
        request = ImageGenerationRequest(
            character_id=uuid4(),
            prompt="a portrait photo",
        )
        assert request.prompt == "a portrait photo"
        assert request.width == 1024  # default
        assert request.height == 1024  # default
        assert request.lora_strength == 0.8  # default

    def test_custom_parameters(self):
        """Test custom generation parameters."""
        request = ImageGenerationRequest(
            character_id=uuid4(),
            prompt="test prompt",
            width=768,
            height=1024,
            num_inference_steps=50,
            guidance_scale=10.0,
            lora_strength=1.0,
            seed=12345,
        )
        assert request.width == 768
        assert request.height == 1024
        assert request.num_inference_steps == 50
        assert request.guidance_scale == 10.0
        assert request.lora_strength == 1.0
        assert request.seed == 12345

    def test_validation_width_bounds(self):
        """Test width validation."""
        with pytest.raises(ValueError):
            ImageGenerationRequest(
                character_id=uuid4(),
                prompt="test",
                width=256,  # too small
            )

        with pytest.raises(ValueError):
            ImageGenerationRequest(
                character_id=uuid4(),
                prompt="test",
                width=4096,  # too large
            )


class TestVideoGenerationRequest:
    def test_valid_request(self):
        """Test creating a valid video generation request."""
        request = VideoGenerationRequest(
            character_id=uuid4(),
            prompt="a person walking",
        )
        assert request.prompt == "a person walking"
        assert request.num_frames == 25  # default
        assert request.fps == 6  # default

    def test_source_image_optional(self):
        """Test that source_image_url is optional."""
        request = VideoGenerationRequest(
            character_id=uuid4(),
            prompt="test",
        )
        assert request.source_image_url is None

    def test_with_source_image(self):
        """Test request with source image."""
        request = VideoGenerationRequest(
            character_id=uuid4(),
            prompt="test",
            source_image_url="https://example.com/image.png",
        )
        assert request.source_image_url == "https://example.com/image.png"
