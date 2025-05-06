from abc import abstractmethod
from typing import Optional, List, Any, Dict

from pydantic import Field, model_validator

from domain.core.constitutive.structural import StructuralModel
from domain.core.materials import StructuralMaterial
from utils.base_model import ImmutableModel
from utils.identifiable import Identifiable


class StructuralSegment(ImmutableModel, Identifiable):
    """Base class for all structural segments."""
    name: Optional[str] = Field(default=None, description="Human-readable name")
    material: StructuralMaterial = Field(description="Physical structural material")
    model: StructuralModel = Field(description="Structural behavior model")

    # Store material_id and model_id as computed fields
    material_id: Optional[str] = Field(default=None, description="ID of associated material")
    model_id: Optional[str] = Field(default=None, description="ID of associated model")

    @model_validator(mode='after')
    def extract_ids(self) -> 'StructuralSegment':
        """Extract IDs from material and model objects."""
        if self.material_id is None and hasattr(self.material, 'id'):
            object.__setattr__(self, 'material_id', self.material.id)

        if self.model_id is None and hasattr(self.model, 'id'):
            object.__setattr__(self, 'model_id', self.model.id)

        return self

    @abstractmethod
    def get_geometry_definition(self) -> Any:
        """Return the geometry definition for this segment."""
        pass


class MeshedSegment(StructuralSegment):
    """A segment already decomposed into line segments."""
    line_ids: List[str]  # References to existing Line objects

    def get_geometry_definition(self) -> List[str]:
        """Return the line IDs that make up this segment."""
        return self.line_ids


class UnmeshedSegment(StructuralSegment):
    """A segment with continuous geometry that requires discretization."""

    # Could be a continuous curve, a parametric definition, etc.
    # Specific subclasses would define appropriate geometry fields

    @abstractmethod
    def get_geometry_definition(self) -> Any:
        """Return the continuous geometry definition."""
        pass


class LinearUnmeshedSegment(UnmeshedSegment):
    """A straight segment defined by start and end points."""
    start_point_id: str  # Reference to start Point
    end_point_id: str  # Reference to end Point

    def get_geometry_definition(self) -> Dict[str, str]:
        """Return the points defining this segment."""
        return {
            "type": "linear",
            "start": self.start_point_id,
            "end": self.end_point_id
        }


class ArcUnmeshedSegment(UnmeshedSegment):
    """A curved segment defined as an arc."""
    start_point_id: str
    end_point_id: str
    center_point_id: str  # Or radius and angle, depending on parameterization

    def get_geometry_definition(self) -> Dict[str, str]:
        """Return the arc definition."""
        return {
            "type": "arc",
            "start": self.start_point_id,
            "end": self.end_point_id,
            "center": self.center_point_id
        }
