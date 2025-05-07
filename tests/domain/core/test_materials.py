# tests/domain/core/test_materials.py
import pytest
from domain.core.materials import SoilMaterial, StructuralMaterial
from domain.core.resistance_factors import ResistanceFactors
from utils.constants import WATER_UNIT_WEIGHT


class TestSoilMaterial:
    """Tests for the SoilMaterial class."""

    def test_create_soil_material(self):
        """Test that a valid soil material can be created."""
        material = SoilMaterial(
            name="Test Clay",
            wet_unit_weight=18.0,
            saturated_unit_weight=20.0
        )

        assert material.name == "Test Clay"
        assert material.wet_unit_weight == 18.0
        assert material.saturated_unit_weight == 20.0

    def test_create_soil_material_without_name(self):
        """Test that a soil material can be created without a name."""
        material = SoilMaterial(
            wet_unit_weight=18.0,
            saturated_unit_weight=20.0
        )

        assert material.name is None
        assert material.wet_unit_weight == 18.0
        assert material.saturated_unit_weight == 20.0

    def test_invalid_wet_unit_weight(self):
        """Test that negative wet unit weight raises an error."""
        with pytest.raises(ValueError, match="Unit weight must be positive"):
            SoilMaterial(
                wet_unit_weight=-5.0,
                saturated_unit_weight=20.0
            )

    def test_infinite_unit_weight(self):
        """Test that infinite unit weights are rejected."""
        with pytest.raises(ValueError, match="Unit weight must be.*finite"):
            SoilMaterial(
                wet_unit_weight=float('inf'),
                saturated_unit_weight=20.0
            )

    def test_invalid_saturated_weight_relation(self):
        """Test that saturated weight must be >= wet weight."""
        with pytest.raises(ValueError, match="Saturated unit weight.*must be greater than or equal to wet unit weight"):
            SoilMaterial(
                wet_unit_weight=20.0,
                saturated_unit_weight=18.0
            )

    def test_empty_name_validation(self):
        """Test that empty names are rejected."""
        with pytest.raises(ValueError, match="Name cannot be empty"):
            SoilMaterial(
                name="",
                wet_unit_weight=18.0,
                saturated_unit_weight=20.0
            )

        with pytest.raises(ValueError, match="Name cannot be empty"):
            SoilMaterial(
                name="   ",  # Only whitespace
                wet_unit_weight=18.0,
                saturated_unit_weight=20.0
            )

    def test_buoyant_unit_weight_calculation(self):
        """Test calculation of buoyant unit weight."""
        material = SoilMaterial(
            wet_unit_weight=18.0,
            saturated_unit_weight=20.0
        )

        expected = 20.0 - WATER_UNIT_WEIGHT
        assert material.buoyant_unit_weight == pytest.approx(expected)

    def test_serialization(self):
        """Test serialization to dict and back."""
        original = SoilMaterial(
            name="Test Clay",
            wet_unit_weight=18.0,
            saturated_unit_weight=20.0
        )

        # Serialize to dict
        data = original.model_dump()

        # Check dict contents
        assert data["name"] == "Test Clay"
        assert data["wet_unit_weight"] == 18.0
        assert data["saturated_unit_weight"] == 20.0

        # Deserialize back to object
        reconstructed = SoilMaterial.model_validate(data)

        # Check equality
        assert reconstructed.name == original.name
        assert reconstructed.wet_unit_weight == original.wet_unit_weight
        assert reconstructed.saturated_unit_weight == original.saturated_unit_weight


class TestStructuralMaterial:
    """Test suite for the StructuralMaterial class."""

    def test_create_basic_material(self):
        """Test creating a basic structural material with minimal properties."""
        material = StructuralMaterial(name="Basic Material")

        assert material.name == "Basic Material"
        assert material.description is None
        assert material.unit_weight is None
        assert material.resistance_factors is None

    def test_create_complete_material(self):
        """Test creating a structural material with all properties."""
        # Create resistance factors
        factors = ResistanceFactors.from_values({
            "compression": 0.9,
            "flexure": 0.85,
            "shear": 0.75
        })

        material = StructuralMaterial(
            name="Complete Material",
            description="A fully specified material",
            unit_weight=78.5,
            resistance_factors=factors
        )

        assert material.name == "Complete Material"
        assert material.description == "A fully specified material"
        assert material.unit_weight == 78.5
        assert material.resistance_factors is factors
        assert material.resistance_factors.get_value("compression") == 0.9
        assert material.resistance_factors.get_value("flexure") == 0.85
        assert material.resistance_factors.get_value("shear") == 0.75

    def test_material_with_resistance_factors(self):
        """Test structural material with resistance factors."""
        # Create resistance factors
        factors = ResistanceFactors.from_values({
            "compression": 0.9,
            "flexure": 0.85,
            "shear": 0.75
        })

        # Create material with factors
        material = StructuralMaterial(
            name="Steel Material",
            resistance_factors=factors
        )

        assert material.name == "Steel Material"
        assert material.resistance_factors is factors
        assert material.resistance_factors.get_value("compression") == 0.9
        assert material.resistance_factors.get_value("flexure") == 0.85
