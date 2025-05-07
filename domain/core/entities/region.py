from typing import Optional
from pydantic import Field, model_validator
from domain.geometry.polygon import Polygon
from utils.registry import RegisteredModel
from domain.core.materials import SoilMaterial
from domain.core.constitutive.soil import SoilModel


class Region(RegisteredModel):
    """Represents a soil region."""
    name: Optional[str] = Field(default=None, description="Human-readable name")
    geometry: Polygon = Field(description="Shape of the region")
    material: SoilMaterial = Field(description="Physical soil material")
    model: SoilModel = Field(description="Soil behavior model")

    # Store material_id and model_id as computed fields
    material_id: Optional[str] = Field(default=None, description="ID of associated material")
    model_id: Optional[str] = Field(default=None, description="ID of associated model")

    @model_validator(mode='after')
    def extract_ids(self) -> 'Region':
        """Extract IDs from material and model objects."""
        if self.material_id is None and hasattr(self.material, 'id'):
            object.__setattr__(self, 'material_id', self.material.id)

        if self.model_id is None and hasattr(self.model, 'id'):
            object.__setattr__(self, 'model_id', self.model.id)

        return self
