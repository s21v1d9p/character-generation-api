import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.schemas.character import CharacterStatus
from src.services.training.lora_trainer import (
    generate_captions,
    build_training_config,
    TrainingDependencyError,
)


class TestGenerateCaptions:
    def test_generates_caption_files(self, tmp_path):
        """Test that caption files are created for each image."""
        # Create test images
        (tmp_path / "image1.png").write_bytes(b"fake image data")
        (tmp_path / "image2.jpg").write_bytes(b"fake image data")
        (tmp_path / "image3.webp").write_bytes(b"fake image data")

        trigger_word = "sks_testchar"
        generate_captions(tmp_path, trigger_word)

        # Check caption files exist
        assert (tmp_path / "image1.txt").exists()
        assert (tmp_path / "image2.txt").exists()
        assert (tmp_path / "image3.txt").exists()

        # Check caption content
        caption = (tmp_path / "image1.txt").read_text()
        assert trigger_word in caption

    def test_ignores_non_image_files(self, tmp_path):
        """Test that non-image files are ignored."""
        (tmp_path / "readme.md").write_text("readme")
        (tmp_path / "config.json").write_text("{}")

        generate_captions(tmp_path, "sks_test")

        assert not (tmp_path / "readme.txt").exists()
        assert not (tmp_path / "config.txt").exists()


class TestBuildTrainingConfig:
    def test_returns_valid_config(self, tmp_path):
        """Test that training config has all required fields."""
        image_dir = tmp_path / "images"
        output_dir = tmp_path / "output"
        image_dir.mkdir()
        output_dir.mkdir()

        config = build_training_config(
            image_dir=image_dir,
            output_dir=output_dir,
            trigger_word="sks_test",
            character_name="test_character",
        )

        assert "pretrained_model_name_or_path" in config
        assert "train_data_dir" in config
        assert "output_dir" in config
        assert "output_name" in config
        assert config["output_name"] == "lora_test_character"
        assert config["network_dim"] == 32
        assert config["network_alpha"] == 16

    def test_config_uses_settings(self, tmp_path):
        """Test that config uses values from settings."""
        image_dir = tmp_path / "images"
        output_dir = tmp_path / "output"
        image_dir.mkdir()
        output_dir.mkdir()

        config = build_training_config(
            image_dir=image_dir,
            output_dir=output_dir,
            trigger_word="sks_test",
            character_name="test",
        )

        # These come from settings
        assert "learning_rate" in config
        assert "max_train_steps" in config
