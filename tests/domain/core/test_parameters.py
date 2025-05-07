# tests/domain/test_parameters.py
import pytest
from domain.core.parameters import Parameter, ModelParameters


class TestParameter:
    """Test cases for Parameter class."""

    def test_create_parameter(self):
        """Test basic parameter creation."""
        param = Parameter(value=100.0, unit="kPa")
        assert param.value == 100.0
        assert param.unit == "kPa"

    def test_parameter_without_unit(self):
        """Test parameter without unit specification."""
        param = Parameter(value=0.3)
        assert param.value == 0.3
        assert param.unit is None

    def test_parameter_serialization(self):
        """Test Parameter serialization."""
        param = Parameter(value=100.0, unit="kPa")
        serialized = param.model_dump()

        assert serialized == {"value": 100.0, "unit": "kPa"}

        # Test deserialization
        deserialized = Parameter.model_validate(serialized)
        assert deserialized.value == param.value
        assert deserialized.unit == param.unit


class TestModelParameters:
    """Test cases for ModelParameters class."""

    def test_create_model_parameters(self):
        """Test basic ModelParameters creation."""
        params = ModelParameters(parameters={
            "young_modulus": Parameter(value=200e6, unit="Pa"),
            "poisson_ratio": Parameter(value=0.3),
            "friction_angle": Parameter(value=30, unit="degree")
        })

        assert len(params.parameters) == 3
        assert params.get_value("young_modulus") == 200e6
        assert params.get_value("poisson_ratio") == 0.3
        assert params.get_value("friction_angle") == 30

    def test_get_parameter(self):
        """Test getting full Parameter objects."""
        param = Parameter(value=100, unit="kPa")
        params = ModelParameters(parameters={"cohesion": param})

        retrieved = params.get_parameter("cohesion")
        assert retrieved is not None
        assert retrieved.value == 100
        assert retrieved.unit == "kPa"

    def test_get_missing_parameter(self):
        """Test accessing non-existent parameters."""
        params = ModelParameters(parameters={})

        assert params.get_value("nonexistent") is None
        assert params.get_parameter("nonexistent") is None
        assert not params.has_parameter("nonexistent")

    def test_has_parameter(self):
        """Test parameter existence check."""
        params = ModelParameters(parameters={
            "existing": Parameter(value=1.0)
        })

        assert params.has_parameter("existing")
        assert not params.has_parameter("missing")

    def test_from_values_method(self):
        """Test creating ModelParameters from value dictionaries."""
        values = {"K": 1000, "n": 0.5, "phi": 30}
        units = {"K": "psi", "phi": "degree"}

        params = ModelParameters.from_values(values, units)

        assert params.get_value("K") == 1000
        assert params.get_parameter("K").unit == "psi"
        assert params.get_value("n") == 0.5
        assert params.get_parameter("n").unit is None
        assert params.get_value("phi") == 30
        assert params.get_parameter("phi").unit == "degree"

    def test_from_values_without_units(self):
        """Test from_values method without unit specification."""
        values = {"K": 1000, "n": 0.5}
        params = ModelParameters.from_values(values)

        assert params.get_value("K") == 1000
        assert params.get_parameter("K").unit is None

    def test_model_parameters_serialization(self):
        """Test ModelParameters serialization."""
        params = ModelParameters(parameters={
            "K": Parameter(value=1000, unit="psi"),
            "n": Parameter(value=0.5)
        })

        serialized = params.model_dump()
        assert "parameters" in serialized
        assert "K" in serialized["parameters"]
        assert serialized["parameters"]["K"]["value"] == 1000
        assert serialized["parameters"]["K"]["unit"] == "psi"
        assert serialized["parameters"]["n"]["value"] == 0.5
        assert serialized["parameters"]["n"]["unit"] is None

        # Test deserialization
        deserialized = ModelParameters.model_validate(serialized)
        assert deserialized.get_value("K") == 1000
        assert deserialized.get_parameter("K").unit == "psi"
        assert deserialized.get_value("n") == 0.5
        assert deserialized.get_parameter("n").unit is None


class TestParameterIntegration:
    """Integration tests for Parameter and ModelParameters."""

    def test_nested_parameter_access(self):
        """Test accessing parameters through ModelParameters."""
        params = ModelParameters(parameters={
            "young_modulus": Parameter(value=200e9, unit="Pa"),
            "cohesion": Parameter(value=0.01, unit="MPa"),
            "friction_angle": Parameter(value=35, unit="degree")
        })

        # Test value access
        assert params.get_value("young_modulus") == 200e9
        assert params.get_value("cohesion") == 0.01
        assert params.get_value("friction_angle") == 35

        # Test unit access
        assert params.get_parameter("young_modulus").unit == "Pa"
        assert params.get_parameter("cohesion").unit == "MPa"
        assert params.get_parameter("friction_angle").unit == "degree"
