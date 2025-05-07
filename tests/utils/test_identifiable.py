# tests/utils/test_identifiable.py
from typing import Optional
import pytest
from pydantic import ValidationError
from utils.registry import RegisteredModel
from utils.identifiable import Identifiable


class SimpleIdentifiable(RegisteredModel, Identifiable):
    """Simple test class implementing Identifiable."""
    value: str


class NamedIdentifiable(RegisteredModel, Identifiable):
    """Test class with name field."""
    name: str
    description: str


class OptionalNameIdentifiable(RegisteredModel, Identifiable):
    """Test class with optional name field."""
    name: Optional[str] = None  # This makes it properly optional
    code: int


class TestIdentifiable:
    """Test suite for the Identifiable mixin."""

    def test_basic_id_required(self):
        """Test that ID is required when creating directly."""
        # Should raise validation error if ID not provided
        with pytest.raises(ValidationError):
            SimpleIdentifiable(value="test")

        # Should work with ID
        model = SimpleIdentifiable(id="test_id", value="test")
        assert model.id == "test_id"
        assert model.value == "test"

    def test_create_id_method(self):
        """Test the create_id method for generating IDs."""
        # Basic ID generation
        id1 = SimpleIdentifiable.create_id()
        assert id1.startswith("simpleidentifiable_")
        assert len(id1) > 20  # Should have class name + underscore + UUID

        # ID with prefix
        id2 = SimpleIdentifiable.create_id(prefix="test")
        assert id2.startswith("test_")

        # ID with name
        id3 = SimpleIdentifiable.create_id(name="Test Object")
        assert id3.startswith("test_object_")

        # ID with prefix and name
        id4 = SimpleIdentifiable.create_id(prefix="prefix", name="Test Object")
        assert id4.startswith("prefix_test_object_")

    def test_id_uniqueness(self):
        """Test that generated IDs are unique."""
        # Generate multiple IDs with same parameters
        ids = [SimpleIdentifiable.create_id(name="same") for _ in range(10)]

        # All should be unique
        assert len(set(ids)) == 10

    def test_create_factory_method(self):
        """Test the create factory method."""
        # Create with auto-generated ID
        model1 = SimpleIdentifiable.create(value="test")
        assert model1.id is not None
        assert model1.value == "test"

        # Create with explicit ID
        model2 = SimpleIdentifiable.create(id="custom_id", value="test2")
        assert model2.id == "custom_id"
        assert model2.value == "test2"

    def test_create_with_name(self):
        """Test create method with name field."""
        # Create with name that should be incorporated in ID
        model = NamedIdentifiable.create(name="Test Object", description="A test")
        assert "test_object" in model.id
        assert model.name == "Test Object"
        assert model.description == "A test"

    def test_create_without_name(self):
        """Test create method without including name."""
        # Create without name should still work
        model = NamedIdentifiable.create(id="test_id", name="Test", description="A test")
        assert model.id == "test_id"
        assert model.name == "Test"

    def test_create_with_optional_name(self):
        """Test create with optional name field."""
        # When name is not provided but class has name field
        model = OptionalNameIdentifiable.create(code=123)
        assert model.name is None
        assert model.code == 123
        assert model.id.startswith("optionalnameidentifiable_")

        # When name is provided
        model2 = OptionalNameIdentifiable.create(name="Named", code=456)
        assert "named" in model2.id
        assert model2.name == "Named"
        assert model2.code == 456

    def test_empty_id_validation(self):
        """Test validation for empty IDs."""
        # Empty string ID
        with pytest.raises(ValidationError):
            SimpleIdentifiable(id="", value="test")

        # Whitespace ID
        with pytest.raises(ValidationError):
            SimpleIdentifiable(id="   ", value="test")

    def test_special_character_handling(self):
        """Test handling of special characters in ID generation."""
        # Name with special characters
        id1 = SimpleIdentifiable.create_id(name="Test! @#$% Object")
        assert "test_object" in id1
        assert "!@#$%" not in id1
