import uuid
from typing import Optional, TypeVar, Type, cast
from pydantic import Field, BaseModel, model_validator

T = TypeVar('T', bound='Identifiable')


class Identifiable(BaseModel):
    """
    Mixin class that adds unique ID functionality to any Pydantic model.

    This mixin provides:
    1. A unique string ID field
    2. Helper methods for ID generation
    3. Factory methods for creating objects with auto-generated IDs

    Usage:
        class MyModel(ImmutableModel, Identifiable):
            name: str
            # ... other fields
    """
    id: str = Field(
        description="Unique identifier",
    )

    @classmethod
    def create_id(cls, prefix: str = "", name: Optional[str] = None) -> str:
        """
        Create a unique ID with optional prefix and name-based component.

        Args:
            prefix: Optional string prefix for the ID
            name: Optional name to incorporate into the ID

        Returns:
            A unique string ID
        """
        # Create base from name if provided, otherwise use class name
        if name:
            # Convert to lowercase, replace spaces with underscores
            base = name.lower().replace(' ', '_')
            # Remove any special characters
            base = ''.join(c for c in base if c.isalnum() or c == '_')
        else:
            base = cls.__name__.lower()

        # Add prefix if provided
        if prefix and prefix not in base:
            base = f"{prefix}_{base}" if base else prefix

        # Add unique suffix
        unique_suffix = uuid.uuid4().hex[:8]  # 8 chars from UUID

        return f"{base}_{unique_suffix}"

    @classmethod
    def create(cls: Type[T], *, id: Optional[str] = None, name: Optional[str] = None,
               prefix: str = "", **kwargs) -> T:
        """
        Factory method that creates an instance with an auto-generated ID.

        Args:
            id: Optional explicit ID (if not provided, one will be generated)
            name: Optional name to use in ID generation
            prefix: Optional prefix for generated ID
            **kwargs: Other fields for the model

        Returns:
            Instance of the model with a guaranteed ID
        """
        # If ID not provided, generate one
        if id is None:
            id = cls.create_id(prefix=prefix, name=name)

        # Create the instance
        return cls(id=id, name=name if "name" in cls.__annotations__ else None, **kwargs)

    @model_validator(mode='after')
    def validate_id(self) -> 'Identifiable':
        """Validate that ID is not empty."""
        if not self.id or not self.id.strip():
            raise ValueError("ID cannot be empty")
        return self
