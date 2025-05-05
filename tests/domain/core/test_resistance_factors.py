import pytest
from domain.core.resistance_factors import ResistanceFactor, ResistanceFactors
from domain.core.materials import StructuralMaterial

class TestResistanceFactor:
    def test_create_resistance_factor(self):
        """Test creating a resistance factor."""
        factor = ResistanceFactor(value=0.9, description="Compression resistance")
        assert factor.value == 0.9
        assert factor.description == "Compression resistance"

    def test_validate_resistance_factor(self):
        """Test resistance factor validation."""
        # Valid values
        ResistanceFactor(value=0.0)
        ResistanceFactor(value=0.5)
        ResistanceFactor(value=1.0)

        # Invalid values
        with pytest.raises(ValueError):
            ResistanceFactor(value=-0.1)

        with pytest.raises(ValueError):
            ResistanceFactor(value=1.1)

    def test_immutability(self):
        """Test that resistance factors are immutable."""
        factor = ResistanceFactor(value=0.9)

        with pytest.raises(Exception):
            factor.value = 0.8


class TestResistanceFactors:
    def test_create_resistance_factors(self):
        """Test creating a container of resistance factors."""
        factors = ResistanceFactors(factors={
            "compression": ResistanceFactor(value=0.9),
            "flexure": ResistanceFactor(value=0.85),
            "shear": ResistanceFactor(value=0.75)
        })

        assert factors.get_value("compression") == 0.9
        assert factors.get_value("flexure") == 0.85
        assert factors.get_value("shear") == 0.75

    def test_from_values(self):
        """Test creating factors from simple values."""
        factors = ResistanceFactors.from_values({
            "compression": 0.9,
            "flexure": 0.85
        }, {
            "compression": "Axial compression",
            "flexure": "Bending"
        })

        assert factors.get_value("compression") == 0.9
        assert factors.get_value("flexure") == 0.85

        compression_factor = factors.get_factor("compression")
        assert compression_factor is not None
        assert compression_factor.description == "Axial compression"

    def test_missing_factor(self):
        """Test handling of missing factors."""
        factors = ResistanceFactors.from_values({"compression": 0.9})

        assert factors.get_value("compression") == 0.9
        assert factors.get_value("nonexistent") is None
        assert factors.get_factor("nonexistent") is None
        assert factors.has_factor("compression")
        assert not factors.has_factor("nonexistent")


# In test_structural_materials.py, add this:
def test_material_with_resistance_factors():
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
