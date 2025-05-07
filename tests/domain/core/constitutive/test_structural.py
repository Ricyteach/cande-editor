import pytest
from domain.core.constitutive.structural import StructuralModel
from domain.core.parameters import ModelParameters, Parameter


class TestStructuralModel:
    def test_create_structural_model(self):
        """Test structural model creation."""
        params = ModelParameters(parameters={
            "E": Parameter(value=200000, unit="MPa"),
            "poisson_ratio": Parameter(value=0.3)
        })

        model = StructuralModel(
            name="Linear Elastic",
            parameters=params
        )

        assert model.name == "Linear Elastic"
        assert model.parameters is params
        assert model.parameters.get_value("E") == 200000
        assert model.parameters.get_value("poisson_ratio") == 0.3

    def test_create_model_without_parameters(self):
        """Test model creation without parameters."""
        model = StructuralModel(name="Default Model")

        assert model.name == "Default Model"
        assert model.parameters is None
