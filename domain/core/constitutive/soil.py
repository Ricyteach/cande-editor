from typing import Optional
from pydantic import Field
from domain.core.parameters import ModelParameters
from utils.base_model import ImmutableModel


class SoilModel(ImmutableModel):
    """
    Represents a mathematical model of soil behavior.

    This class is a generic representation of soil behavior models in the domain.
    It stores the name of the model and its associated parameters.
    """
    name: str = Field(
        description="Identifier for the soil model"
    )
    parameters: Optional[ModelParameters] = Field(
        default=None,
        description="Parameters for the model"
    )
