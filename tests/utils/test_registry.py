import pytest
from typing import List, Dict, Optional
from utils.registry import RegisteredModel


class SimpleModel(RegisteredModel):
    """Simple test model with basic attributes."""
    name: str
    value: int


class NestedModel(RegisteredModel):
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
