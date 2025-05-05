from typing import Optional
from pydantic import Field, field_validator, model_validator
from utils.constants import WATER_UNIT_WEIGHT
from utils.base_model import ImmutableModel


class SoilMaterial(ImmutableModel):
    """
    Represents physical properties of soil material.

    This class contains only physical properties, not behavioral models.
    Unit weights are stored without unit conversion - interpretation
    of units is handled at higher layers.

    The name field is optional and provides a human-readable identifier
    for the physical material (e.g., "Clay", "Dense Sand").
    """
    name: Optional[str] = Field(
        default=None,
        description="Human-readable identifier for the physical material"
    )
    wet_unit_weight: float = Field(
        description="Unit weight in unsaturated conditions"
    )
    saturated_unit_weight: float = Field(
        description="Unit weight in saturated conditions"
    )

    @field_validator('wet_unit_weight', 'saturated_unit_weight')
    @classmethod
    def validate_unit_weight(cls, value: float) -> float:
        """Validate that unit weights are positive and finite."""
        if not (value > 0 and value < float('inf')):
            raise ValueError(f"Unit weight must be positive and finite, got {value}")
        return value

    @field_validator('name')
    @classmethod
    def validate_name(cls, value: Optional[str]) -> Optional[str]:
        """Validate material name if provided."""
        if value is not None and value.strip() == "":
            raise ValueError("Name cannot be empty if provided")
        return value

    @model_validator(mode='after')
    def validate_weights_relation(self) -> 'SoilMaterial':
        """Validate that saturated unit weight is at least equal to wet unit weight."""
        if self.saturated_unit_weight < self.wet_unit_weight:
            raise ValueError(
                f"Saturated unit weight ({self.saturated_unit_weight}) must be greater than "
                f"or equal to wet unit weight ({self.wet_unit_weight})"
            )
        return self

    @property
    def buoyant_unit_weight(self) -> float:
        """Calculate buoyant unit weight (derived property)."""
        return self.saturated_unit_weight - WATER_UNIT_WEIGHT
