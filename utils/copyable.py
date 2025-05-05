"""
# Usage in models:
class SomeModel(BaseModel, ImmutableCopyable['SomeModel']):
# Model definition...
"""

# domain/utility.py
from typing import TypeVar, Generic
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)


class ImmutableCopyable(Generic[T]):
    """Utility for creating immutable models with copy capability."""

    def with_changes(self: T, **changes) -> T:
        """Create a new instance with specified changes."""
        # Get current data
        current_data = self.model_dump()

        # Apply changes
        for key, value in changes.items():
            if key not in current_data:
                raise ValueError(f"Invalid field: {key}")
            current_data[key] = value

        # Create new instance
        return self.__class__.model_validate(current_data)


# Alternative: Mixin approach
class ImmutableCopyableMixin:
    """Mixin for immutable models that can create copies with changes."""

    def with_changes(self, **changes):
        """Create a new instance with specified changes."""
        current_data = self.model_dump()
        for key, value in changes.items():
            if key not in current_data:
                raise ValueError(f"Invalid field: {key}")
            current_data[key] = value
        return self.__class__.model_validate(current_data)
