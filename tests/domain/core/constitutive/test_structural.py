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

    def test_immutability(self):
        """Test that models are immutable."""
        model = StructuralModel(name="Test Model")

        with pytest.raises(Exception):
            model.name = "Changed"

        with pytest.raises(Exception):
            model.parameters = ModelParameters(parameters={})

    def test_with_changes(self):
        """Test the with_changes method."""
        original_params = ModelParameters(parameters={
            "E": Parameter(value=200000, unit="MPa")
        })

        new_params = ModelParameters(parameters={
            "E": Parameter(value=210000, unit="MPa"),
            "poisson_ratio": Parameter(value=0.3)
        })

        model = StructuralModel(
            name="Original Model",
            parameters=original_params
        )

        # Create a modified copy
        modified = model.with_changes(
            name="Modified Model",
            parameters=new_params
        )

        # Original should be unchanged
        assert model.name == "Original Model"
        assert model.parameters is original_params

        # New copy should have changes
        assert modified.name == "Modified Model"
        assert modified.parameters is new_params
