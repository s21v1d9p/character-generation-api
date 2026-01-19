import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


class TestCharacterSchemas:
    def test_character_create(self):
        """Test CharacterCreate schema validation."""
        from src.schemas.character import CharacterCreate

        char = CharacterCreate(name="Test Character")
        assert char.name == "Test Character"
        assert char.description is None
        assert char.trigger_word is None

    def test_character_create_with_all_fields(self):
        """Test CharacterCreate with all fields."""
        from src.schemas.character import CharacterCreate

        char = CharacterCreate(
            name="Test Character",
            description="A test character",
            trigger_word="sks_test",
        )
        assert char.name == "Test Character"
        assert char.description == "A test character"
        assert char.trigger_word == "sks_test"

    def test_character_status_enum(self):
        """Test CharacterStatus enum values."""
        from src.schemas.character import CharacterStatus

        assert CharacterStatus.PENDING.value == "pending"
        assert CharacterStatus.TRAINING.value == "training"
        assert CharacterStatus.READY.value == "ready"
        assert CharacterStatus.FAILED.value == "failed"


class TestTriggerWordGeneration:
    def test_generate_trigger_word(self):
        """Test trigger word generation from name."""
        from src.api.routes.characters import generate_trigger_word

        assert generate_trigger_word("John Doe") == "sks_johndoe"
        assert generate_trigger_word("Test-Character") == "sks_testcharacter"
        assert generate_trigger_word("Name With Spaces") == "sks_namewithspaces"

    def test_generate_trigger_word_special_chars(self):
        """Test trigger word with special characters."""
        from src.api.routes.characters import generate_trigger_word

        assert generate_trigger_word("Café!") == "sks_caf"
        assert generate_trigger_word("Test@#$123") == "sks_test123"
