from typing import Optional
from pydantic import Field
from domain.core.parameters import ModelParameters
from utils.base_model import ImmutableModel


class StructuralModel(ImmutableModel):
    """
    Base class for structural behavior models.

    Similar to SoilModel, this is a simple container for a name and parameters,
    with the actual parameter specifications and validation handled in the CANDE layer.
    """
    name: str = Field(description="Model name/identifier")
    parameters: Optional[ModelParameters] = Field(
        default=None, description="Model parameters"
    )
