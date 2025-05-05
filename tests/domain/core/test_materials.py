# tests/domain/core/test_materials.py
import pytest
from domain.core.materials import SoilMaterial
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

    def test_immutability(self):
        """Test that SoilMaterial is immutable."""
        material = SoilMaterial(
            name="Test Soil",
            wet_unit_weight=18.0,
            saturated_unit_weight=20.0
        )

        # Attempt to modify attributes
        with pytest.raises(Exception):
            material.name = "Modified Name"

        with pytest.raises(Exception):
            material.wet_unit_weight = 19.0

    def test_with_changes(self):
        """Test creating a modified copy using with_changes."""
        original = SoilMaterial(
            name="Original",
            wet_unit_weight=18.0,
            saturated_unit_weight=20.0
        )

        # Create modified copy
        modified = original.with_changes(name="Modified", wet_unit_weight=19.0)

        # Original should be unchanged
        assert original.name == "Original"
        assert original.wet_unit_weight == 18.0

        # Modified should have new values
        assert modified.name == "Modified"
        assert modified.wet_unit_weight == 19.0
        assert modified.saturated_unit_weight == 20.0  # Unchanged

    def test_with_changes_invalid_field(self):
        """Test that with_changes validates field names."""
        material = SoilMaterial(
            wet_unit_weight=18.0,
            saturated_unit_weight=20.0
        )

        with pytest.raises(ValueError, match="Invalid field"):
            material.with_changes(nonexistent_field="value")

    def test_with_changes_validates_new_values(self):
        """Test that with_changes validates the new values."""
        material = SoilMaterial(
            wet_unit_weight=18.0,
            saturated_unit_weight=20.0
        )

        # Should still enforce validation rules
        with pytest.raises(ValueError, match="Unit weight must be positive"):
            material.with_changes(wet_unit_weight=-5.0)

        with pytest.raises(ValueError, match="Saturated unit weight.*must be greater than or equal to wet unit weight"):
            material.with_changes(wet_unit_weight=21.0)  # Now wet > saturated

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
