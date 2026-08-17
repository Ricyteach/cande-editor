"""Tests for the typed model over a document.

Most of the model is exercised through the validation rules; this covers the
pipe-group view, which is what a section library or a viewer binds to.
"""

from __future__ import annotations

from pathlib import Path

from candejar.io import Document, make_record
from candejar.model import Problem


def problem_of(*records: object) -> Problem:
    """Assemble a Problem from records, in file order."""
    return Problem(
        Document(tuple(records), newline="\r\n", trailing_newline=True)  # type: ignore[arg-type]
    )


class TestPipeGroups:
    def test_level_2_canned_mesh_is_not_an_element_count(self, fixtures_dir: Path) -> None:
        """A-2.L12 columns 11-15 are NPCAN, not a beam count.

        Reading them as an element count reported a canned circular pipe mesh
        -- which has no C-4 lines at all, CANDE generates them -- as a group of
        one element. User Manual 5.3.2.
        """
        group = Problem.read(str(fixtures_dir / "level2_pipe_steel_wsd.cid")).pipe_groups[0]
        assert group.canned_mesh == 1  # 1 = circular pipe mesh
        assert group.elements is None

    def test_level_3_carries_a_beam_count(self, fixtures_dir: Path) -> None:
        """A-2.L3 columns 11-15 *are* NPMATX, the connected beam elements."""
        group = Problem.read(str(fixtures_dir / "level3_quad_steel.cid")).pipe_groups[0]
        assert group.elements == 2
        assert group.canned_mesh is None

    def test_a_steel_group_carries_its_material_and_section(self, fixtures_dir: Path) -> None:
        group = Problem.read(str(fixtures_dir / "level2_pipe_steel_wsd.cid")).pipe_groups[0]
        assert group.pipe_type == "STEEL"
        assert group.material is not None
        assert group.material.modulus == 29_000_000.0
        assert group.material.poisson == 0.3
        assert group.material.yield_stress == 80_000.0
        assert group.material.density == 0.284
        assert group.section is not None
        assert group.section.area == 0.04
        assert group.section.inertia == 0.00333
        assert group.section.section_modulus == 0.00668

    def test_aluminum_has_no_plastic_modulus(self) -> None:
        """PZ is steel's, for deep corrugations; aluminum has no counterpart."""
        problem = problem_of(
            make_record("A-2.L3", pipe_type="ALUMINUM", elements=5),
            make_record("B-2.Alum.A", area=0.1, inertia=0.2, section_modulus=0.3),
        )
        section = problem.pipe_groups[0].section
        assert section is not None
        assert (section.area, section.inertia, section.section_modulus) == (0.1, 0.2, 0.3)
        assert section.plastic_modulus is None

    def test_each_group_owns_the_part_b_lines_that_follow_it(self) -> None:
        """Nothing carries a group number -- file order is the only association.

        Part A/B repeats once per group, so an A-2 owns every Part B line until
        the next A-2.
        """
        problem = problem_of(
            make_record("A-2.L3", pipe_type="STEEL", elements=3),
            make_record("B-1.Steel", modulus=29_000_000, poisson=0.3, yield_stress=33_000),
            make_record("B-2.Steel.A", area=0.04, inertia=0.00333, section_modulus=0.00668),
            make_record("A-2.L3", pipe_type="ALUMINUM", elements=5),
            make_record("B-1.Alum", modulus=10_000_000, poisson=0.33, yield_stress=24_000),
            make_record("B-2.Alum.A", area=0.9, inertia=0.8, section_modulus=0.7),
        )
        steel, aluminum = problem.pipe_groups
        assert (steel.number, steel.pipe_type, steel.elements) == (1, "STEEL", 3)
        assert (aluminum.number, aluminum.pipe_type, aluminum.elements) == (2, "ALUMINUM", 5)

        assert steel.material is not None and aluminum.material is not None
        assert steel.material.modulus == 29_000_000.0
        assert aluminum.material.modulus == 10_000_000.0
        assert steel.section is not None and aluminum.section is not None
        assert steel.section.area == 0.04
        assert aluminum.section.area == 0.9

    def test_an_uncatalogued_pipe_type_has_no_material_rather_than_a_wrong_one(
        self, fixtures_dir: Path
    ) -> None:
        """Plastic's Part B lines have no spec yet, so they contribute nothing.

        The failure to avoid is guessing: reading plastic's B-1 with steel's
        column table would decode cleanly and be wrong.
        """
        groups = Problem.read(str(fixtures_dir / "level3_plastic_asd.cid")).pipe_groups
        assert len(groups) == 9
        assert all(g.pipe_type == "PLASTIC" for g in groups)
        assert all(g.material is None and g.section is None for g in groups)

    def test_part_b_before_any_group_is_ignored(self) -> None:
        """A malformed file must not attach Part B to a group that isn't there."""
        problem = problem_of(
            make_record("B-1.Steel", modulus=29_000_000),
            make_record("A-2.L3", pipe_type="STEEL", elements=1),
        )
        assert len(problem.pipe_groups) == 1
        assert problem.pipe_groups[0].material is None
