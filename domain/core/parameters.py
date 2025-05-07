# domain/parameters.py
from typing import Dict, Optional
from utils.registry import RegisteredModel
from pydantic import Field


class Parameter(RegisteredModel):
    """A parameter with a value and optional unit.

    This is the fundamental building block for storing numerical values
    in the domain model. Units are stored as strings and conversion is
    handled at the boundary layers.
    """
    value: float = Field(description="Numerical value")
    unit: Optional[str] = Field(default=None, description="Unit string (e.g., 'kPa', 'm', 'degrees')")


class ModelParameters(RegisteredModel):
    """Container for model parameters.

    Each parameter can have its own unit. Parameters are accessed by name
    and can be retrieved as raw values for later unit conversion by upper layers.
    """
    parameters: Dict[str, Parameter] = Field(description="Named parameters")

    def get_value(self, key: str) -> Optional[float]:
        """Get raw parameter value."""
        param = self.parameters.get(key)
        return param.value if param else None

    def get_parameter(self, key: str) -> Optional[Parameter]:
        """Get the full Parameter object."""
        return self.parameters.get(key)

    def has_parameter(self, key: str) -> bool:
        """Check if a parameter exists."""
        return key in self.parameters

    @classmethod
    def from_values(cls,
                    values: Dict[str, float],
                    units: Optional[Dict[str, str]] = None) -> 'ModelParameters':
        """Create from separate value and unit dictionaries.

        This is a convenience method for backward compatibility and simple use cases.
        """
        parameters = {}
        for key, value in values.items():
            unit = units.get(key) if units else None
            parameters[key] = Parameter(value=value, unit=unit)
        return cls(parameters=parameters)
