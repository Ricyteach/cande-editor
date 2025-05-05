import pytest
from typing import List, Dict, Optional
from utils.base_model import ImmutableModel


class SimpleModel(ImmutableModel):
    """Simple test model with basic attributes."""
    name: str
    value: int


class NestedModel(ImmutableModel):
    """More complex model with nested attributes."""
    title: str
    data: Dict[str, float]
    tags: List[str]
    simple: Optional[SimpleModel] = None


class TestImmutableModel:
    """Test suite for ImmutableModel base class."""

    def test_basic_creation(self):
        """Test creating a simple immutable model."""
        model = SimpleModel(name="test", value=42)
        assert model.name == "test"
        assert model.value == 42

    def test_immutability(self):
        """Test that models are immutable after creation."""
        model = SimpleModel(name="test", value=42)

        # Attempt to modify should raise an exception
        with pytest.raises(Exception):
            model.name = "changed"

        with pytest.raises(Exception):
            model.value = 100

    def test_with_changes_basic(self):
        """Test creating modified copies with with_changes() method."""
        original = SimpleModel(name="test", value=42)

        # Create modified copy
        modified = original.with_changes(name="updated")

        # Original should be unchanged
        assert original.name == "test"
        assert original.value == 42

        # Modified should have updated values
        assert modified.name == "updated"
        assert modified.value == 42

        # They should be different objects
        assert original is not modified

    def test_with_changes_multiple_fields(self):
        """Test changing multiple fields at once."""
        original = SimpleModel(name="test", value=42)

        # Change multiple fields
        modified = original.with_changes(name="updated", value=100)

        assert modified.name == "updated"
        assert modified.value == 100

    def test_with_changes_invalid_field(self):
        """Test that with_changes() raises error for invalid field names."""
        model = SimpleModel(name="test", value=42)

        with pytest.raises(ValueError) as exc_info:
            model.with_changes(nonexistent="value")

        assert "Invalid field: nonexistent" in str(exc_info.value)

    def test_nested_model_creation(self):
        """Test creating a model with nested structures."""
        nested = NestedModel(
            title="Example",
            data={"a": 1.0, "b": 2.0},
            tags=["test", "example"],
            simple=SimpleModel(name="nested", value=10)
        )

        assert nested.title == "Example"
        assert nested.data["a"] == 1.0
        assert nested.tags[0] == "test"
        assert nested.simple.name == "nested"

    def test_nested_model_with_changes(self):
        """Test with_changes on models with nested structures."""
        original = NestedModel(
            title="Example",
            data={"a": 1.0, "b": 2.0},
            tags=["test", "example"],
            simple=SimpleModel(name="nested", value=10)
        )

        # Create a new version with changes to nested fields
        modified = original.with_changes(
            title="Updated",
            simple=SimpleModel(name="changed", value=20)
        )

        # Check that changes were applied correctly
        assert modified.title == "Updated"
        assert modified.simple.name == "changed"
        assert modified.simple.value == 20

        # Original should be unchanged
        assert original.title == "Example"
        assert original.simple.name == "nested"

    def test_with_changes_preserves_optional_none(self):
        """Test that with_changes preserves None for optional fields."""
        original = NestedModel(
            title="Example",
            data={"a": 1.0},
            tags=["test"],
            simple=None  # Optional field is None
        )

        # Change unrelated field
        modified = original.with_changes(title="Changed")

        # simple should still be None
        assert modified.simple is None

    def test_chained_with_changes(self):
        """Test that with_changes can be chained."""
        original = SimpleModel(name="test", value=1)

        # Chain multiple with_changes calls
        result = original.with_changes(name="step1") \
            .with_changes(value=2) \
            .with_changes(name="final")

        assert result.name == "final"
        assert result.value == 2

        # Original should be unchanged
        assert original.name == "test"
        assert original.value == 1
