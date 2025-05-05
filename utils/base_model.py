# utils/base_model.py
from typing import TypeVar, Any, cast
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)


class ImmutableModel(BaseModel):
    """
    Base class for all domain models providing immutability and copy functionality.

    All domain models should inherit from this class to ensure consistent behavior:
    - Immutability: All instances are frozen after creation
    - Copyability: Easy creation of modified copies via with_changes()
    """
    model_config = {
        "frozen": True,  # Make all instances immutable
    }

    def with_changes(self, **changes: Any) -> T:
        """
        Create a new instance with specified changes.

        Args:
            **changes: Keyword arguments with field values to change

        Returns:
            New instance with updated values

        Raises:
            ValueError: If an invalid field name is provided
        """
        # Get current data as dictionary
        current_data = self.model_dump()

        # Apply requested changes
        for key, value in changes.items():
            if key not in current_data:
                raise ValueError(f"Invalid field: {key}")
            current_data[key] = value

        # Get the concrete class of this instance
        cls = self.__class__

        # Create new instance with updated values (cast to help type checker)
        return cast(T, cls.model_validate(current_data))
