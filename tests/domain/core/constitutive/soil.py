# tests/domain/core/test_soil_model.py
import pytest
from domain.core.constitutive.soil import SoilModel
from domain.core.parameters import Parameter, ModelParameters


class TestSoilModel:
    """Tests for the SoilModel class."""

    def test_create_soil_model(self):
        """Test that a soil model can be created with a name and parameters."""
        parameters = ModelParameters(parameters={
            "young_modulus": Parameter(value=20000, unit="kPa"),
            "poisson_ratio": Parameter(value=0.3)
        })

        model = SoilModel(
            name="Linear Elastic",
            parameters=parameters
        )

        assert model.name == "Linear Elastic"
        assert model.parameters is parameters

    def test_create_soil_model_without_parameters(self):
        """Test that a soil model can be created without parameters."""
        model = SoilModel(
            name="Standard Clay"
        )

        assert model.name == "Standard Clay"
        assert model.parameters is None

    def test_soil_model_immutability(self):
        """Test that SoilModel is immutable."""
        parameters = ModelParameters(parameters={
            "young_modulus": Parameter(value=20000, unit="kPa")
        })

        model = SoilModel(
            name="Test Model",
            parameters=parameters
        )

        # Attempt to modify attributes
        with pytest.raises(Exception):
            model.name = "Modified Name"

        with pytest.raises(Exception):
            model.parameters = None

    def test_with_changes(self):
        """Test creating a modified copy using with_changes."""
        original_params = ModelParameters(parameters={
            "young_modulus": Parameter(value=20000, unit="kPa")
        })

        new_params = ModelParameters(parameters={
            "cohesion": Parameter(value=10, unit="kPa"),
            "friction_angle": Parameter(value=30, unit="degrees")
        })

        original = SoilModel(
            name="Original Model",
            parameters=original_params
        )

        # Create modified copy
        modified = original.with_changes(name="Modified Model", parameters=new_params)

        # Original should be unchanged
        assert original.name == "Original Model"
        assert original.parameters is original_params

        # Modified should have new values
        assert modified.name == "Modified Model"
        assert modified.parameters is new_params

    def test_with_changes_invalid_field(self):
        """Test that with_changes validates field names."""
        model = SoilModel(
            name="Test Model"
        )

        with pytest.raises(ValueError, match="Invalid field"):
            model.with_changes(nonexistent_field="value")

    def test_serialization(self):
        """Test serialization to dict and back."""
        parameters = ModelParameters(parameters={
            "young_modulus": Parameter(value=20000, unit="kPa"),
            "poisson_ratio": Parameter(value=0.3)
        })

        original = SoilModel(
            name="Linear Elastic",
            parameters=parameters
        )

        # Serialize to dict
        data = original.model_dump()

        # Check dict contents
        assert data["name"] == "Linear Elastic"
        assert "parameters" in data

        # Check parameters included correctly
        assert data["parameters"]["parameters"]["young_modulus"]["value"] == 20000
        assert data["parameters"]["parameters"]["young_modulus"]["unit"] == "kPa"
        assert data["parameters"]["parameters"]["poisson_ratio"]["value"] == 0.3

        # Deserialize back to object
        reconstructed = SoilModel.model_validate(data)

        # Check equality of fields
        assert reconstructed.name == original.name
        assert reconstructed.parameters is not None

        # Check reconstructed parameters
        young_modulus_param = reconstructed.parameters.get_parameter("young_modulus")
        assert young_modulus_param is not None
        assert young_modulus_param.value == 20000
        assert young_modulus_param.unit == "kPa"
