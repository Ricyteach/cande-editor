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
