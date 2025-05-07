# domain/core/factors.py

from typing import Dict, Optional
from pydantic import Field, field_validator
from utils.registry import RegisteredModel


class ResistanceFactor(RegisteredModel):
    """
    Represents a resistance factor for LRFD design.

    Similar to Parameter but specialized for resistance factors
    which are always unitless values between 0 and 1.
    """
    value: float = Field(description="Resistance factor value (0-1)")
    description: Optional[str] = Field(default=None, description="Description of this factor")

    @field_validator("value")
    @classmethod
    def validate_value(cls, v: float) -> float:
        """Validate that resistance factor is between 0 and 1."""
        if not (0 <= v <= 1):
            raise ValueError("Resistance factor must be between 0 and 1")
        return v


class ResistanceFactors(RegisteredModel):
    """
    Container for resistance factors used in LRFD design.

    Similar to ModelParameters but specialized for resistance factors.
    """
    factors: Dict[str, ResistanceFactor] = Field(
        default_factory=dict,
        description="Named resistance factors"
    )

    def get_value(self, key: str) -> Optional[float]:
        """Get factor value by name."""
        factor = self.factors.get(key)
        return factor.value if factor else None

    def get_factor(self, key: str) -> Optional[ResistanceFactor]:
        """Get the full ResistanceFactor object."""
        return self.factors.get(key)

    def has_factor(self, key: str) -> bool:
        """Check if a factor exists."""
        return key in self.factors

    @classmethod
    def from_values(cls, values: Dict[str, float],
                    descriptions: Optional[Dict[str, str]] = None) -> 'ResistanceFactors':
        """
        Create from simple value dictionary.

        Args:
            values: Dictionary mapping factor names to values
            descriptions: Optional dictionary mapping factor names to descriptions

        Returns:
            New ResistanceFactors instance
        """
        factors = {}
        for key, value in values.items():
            description = None
            if descriptions and key in descriptions:
                description = descriptions[key]
            factors[key] = ResistanceFactor(value=value, description=description)
        return cls(factors=factors)
