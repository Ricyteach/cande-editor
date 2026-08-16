"""Tests for the validation rules.

Each rule is exercised against a deliberately broken model, and the whole suite
is run against the real fixtures to check it does not cry wolf: a file CANDE
accepted should produce no errors.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from candejar.io import loads
from candejar.model import Problem
from candejar.validate import Severity, run_rules


def build(
    *,
    nodes: list[tuple[int, float, float]] | None = None,
    elements: list[tuple[int, int, int, int, int, int, int, int]] | None = None,
    materials: list[tuple[int, int, str]] | None = None,
    boundaries: list[tuple[int, int, float, int, float, int]] | None = None,
    control: str = "   2    3    0    3    1    4    1  200    1    0    1    0",
    terminator: bool = True,
) -> Problem:
    """Assemble a small Level 3 problem from field values."""
    lines = [
        f"{'A-1':>25}!!ANALYS   3 0  1Test problem",
        f"{'C-2.L3':>25}!!{control}",
    ]
    for number, x, y in nodes or []:
        lines.append(f"{'C-3.L3':>25}!! {number:4d}  0 {x:9.2f}{y:10.2f}"[: 27 + 30])
    for number, i, j, k, ll, material, birth, code in elements or []:
        lines.append(
            f"{'C-4.L3':>25}!! {number:4d}{i:5d}{j:5d}{k:5d}{ll:5d}{material:5d}{birth:5d}{code:5d}"
        )
    for node, x_code, x_value, y_code, y_value, step in boundaries or []:
        lines.append(
            f"{'C-5.L3':>25}!! {node:4d}{x_code:5d}{x_value:10.2f}"
            f"{y_code:5d}{y_value:10.2f}{0.0:10.2f}{step:5d}"
        )
    for number, model, name in materials or []:
        lines.append(f"{'D-1':>25}!! {number:4d}{model:5d}{120:10d}{name:<20s}")
    if terminator:
        lines.append("STOP")
    return Problem(loads("\r\n".join(lines) + "\r\n"))


SQUARE_NODES = [(1, 0.0, 0.0), (2, 10.0, 0.0), (3, 10.0, 10.0), (4, 0.0, 10.0)]
SQUARE = (1, 1, 2, 3, 4, 1, 1, 0)
RESTRAINTS = [(1, 1, 0.0, 1, 0.0, 1), (2, 1, 0.0, 1, 0.0, 1)]
SOIL = [(1, 1, "Fill")]


def rules_fired(problem: Problem) -> set[str]:
    return {finding.rule for finding in run_rules(problem)}


def messages_for(problem: Problem, rule: str) -> list[str]:
    return [f.message for f in run_rules(problem) if f.rule == rule]


class TestCleanModel:
    def test_a_sound_model_produces_no_errors(self) -> None:
        problem = build(
            nodes=SQUARE_NODES, elements=[SQUARE], materials=SOIL, boundaries=RESTRAINTS
        )
        assert [f for f in run_rules(problem) if f.severity is Severity.ERROR] == []

    def test_real_files_produce_no_errors(self, cid_path: Path) -> None:
        """A file CANDE accepted must not be reported as broken."""
        findings = run_rules(Problem.read(str(cid_path)))
        errors = [f for f in findings if f.severity is Severity.ERROR]
        assert errors == [], "\n".join(str(f) for f in errors)


class TestStructure:
    def test_missing_terminator(self) -> None:
        problem = build(nodes=SQUARE_NODES, elements=[SQUARE], terminator=False)
        assert "terminator" in rules_fired(problem)

    def test_duplicate_elements(self) -> None:
        """The failure mode the previous editor produced on every interface run."""
        duplicate = (2, 1, 2, 3, 4, 1, 1, 0)
        problem = build(
            nodes=SQUARE_NODES,
            elements=[SQUARE, duplicate],
            materials=SOIL,
            boundaries=RESTRAINTS,
            control="   2    3    0    3    1    4    2  200    1    0    1    0",
        )
        assert "duplicate-element" in rules_fired(problem)
        assert "Elements 1, 2" in messages_for(problem, "duplicate-element")[0]

    def test_orphan_node(self) -> None:
        problem = build(
            nodes=[*SQUARE_NODES, (5, 50.0, 50.0)],
            elements=[SQUARE],
            materials=SOIL,
            boundaries=RESTRAINTS,
            control="   2    3    0    3    1    5    1  200    1    0    1    0",
        )
        assert "Node 5 is defined but no element uses it." in messages_for(problem, "orphan-node")

    def test_undefined_node_is_only_a_note(self) -> None:
        """CANDE fills these in by Laplace generation, so it is not an error."""
        problem = build(
            nodes=SQUARE_NODES[:3],
            elements=[SQUARE],
            materials=SOIL,
            boundaries=RESTRAINTS,
        )
        undefined = [f for f in run_rules(problem) if f.rule == "undefined-node"]
        assert undefined and all(f.severity is Severity.NOTE for f in undefined)


class TestControls:
    def test_element_count_mismatch(self) -> None:
        problem = build(
            nodes=SQUARE_NODES,
            elements=[SQUARE],
            materials=SOIL,
            boundaries=RESTRAINTS,
            control="   2    3    0    3    1    4    9  200    1    0    1    0",
        )
        assert "C-2 declares NELEM = 9" in messages_for(problem, "element-count")[0]

    def test_npt_below_the_highest_node_number(self) -> None:
        """NPT is the highest node number, not a count -- the bug in the old editor."""
        problem = build(
            nodes=[(1, 0.0, 0.0), (2, 10.0, 0.0), (3, 10.0, 10.0), (40, 0.0, 10.0)],
            elements=[(1, 1, 2, 3, 40, 1, 1, 0)],
            materials=SOIL,
            boundaries=RESTRAINTS,
            control="   2    3    0    3    1    4    1  200    1    0    1    0",
        )
        message = messages_for(problem, "highest-node")[0]
        assert "NPT = 4" in message and "node 40 is defined" in message

    def test_boundary_count_too_small(self) -> None:
        problem = build(
            nodes=SQUARE_NODES,
            elements=[SQUARE],
            materials=SOIL,
            boundaries=RESTRAINTS,
            control="   2    3    0    3    1    4    1    1    1    0    1    0",
        )
        assert "boundary-count" in rules_fired(problem)

    def test_element_born_beyond_the_declared_steps(self) -> None:
        problem = build(
            nodes=SQUARE_NODES,
            elements=[(1, 1, 2, 3, 4, 1, 7, 0)],
            materials=SOIL,
            boundaries=RESTRAINTS,
        )
        assert "load-step-range" in rules_fired(problem)


class TestMaterials:
    def test_undefined_soil_material(self) -> None:
        problem = build(
            nodes=SQUARE_NODES,
            elements=[(1, 1, 2, 3, 4, 9, 1, 0)],
            materials=SOIL,
            boundaries=RESTRAINTS,
        )
        assert "references soil material 9" in messages_for(problem, "undefined-material")[0]

    def test_unused_material(self) -> None:
        problem = build(
            nodes=SQUARE_NODES,
            elements=[SQUARE],
            materials=[*SOIL, (2, 1, "Spare")],
            boundaries=RESTRAINTS,
        )
        assert "Soil material 2 (Spare) is defined but no element uses it." in messages_for(
            problem, "unused-material"
        )

    def test_unknown_material_model(self) -> None:
        problem = build(
            nodes=SQUARE_NODES,
            elements=[SQUARE],
            materials=[(1, 99, "Bogus")],
            boundaries=RESTRAINTS,
        )
        assert "material-model" in rules_fired(problem)

    def test_interface_pointing_at_a_soil_material(self) -> None:
        problem = build(
            nodes=[*SQUARE_NODES, (5, 0.0, 0.0), (6, 0.0, 0.0)],
            elements=[SQUARE, (2, 1, 5, 6, 0, 1, 1, 1)],
            materials=SOIL,
            boundaries=RESTRAINTS,
            control="   2    3    0    3    1    6    2  200    1    0    1    0",
        )
        assert "is a Isotropic material, not an interface" in " ".join(
            messages_for(problem, "interface-material-model")
        )


class TestGeometry:
    def test_zero_area_element(self) -> None:
        problem = build(
            nodes=[(1, 0.0, 0.0), (2, 5.0, 0.0), (3, 10.0, 0.0), (4, 15.0, 0.0)],
            elements=[SQUARE],
            materials=SOIL,
            boundaries=RESTRAINTS,
        )
        assert "has zero area" in messages_for(problem, "element-geometry")[0]

    def test_clockwise_element(self) -> None:
        problem = build(
            nodes=[(1, 0.0, 0.0), (2, 0.0, 10.0), (3, 10.0, 10.0), (4, 10.0, 0.0)],
            elements=[SQUARE],
            materials=SOIL,
            boundaries=RESTRAINTS,
        )
        assert "numbered clockwise" in messages_for(problem, "element-geometry")[0]

    def test_extreme_aspect_ratio(self) -> None:
        problem = build(
            nodes=[(1, 0.0, 0.0), (2, 400.0, 0.0), (3, 400.0, 1.0), (4, 0.0, 1.0)],
            elements=[SQUARE],
            materials=SOIL,
            boundaries=RESTRAINTS,
        )
        assert "aspect ratio of 400:1" in messages_for(problem, "element-aspect")[0]

    def test_interface_k_node_must_exceed_i_and_j(self) -> None:
        problem = build(
            nodes=[*SQUARE_NODES, (5, 0.0, 0.0), (6, 0.0, 0.0)],
            elements=[SQUARE, (2, 6, 5, 1, 0, 1, 1, 1)],
            materials=[(1, 1, "Fill"), (1, 6, "Interface")],
            boundaries=RESTRAINTS,
            control="   2    3    0    3    1    6    2  200    1    0    1    0",
        )
        assert "does not exceed its I and J nodes" in " ".join(
            messages_for(problem, "interface-connectivity")
        )

    def test_link_element_is_not_mistaken_for_a_beam(self) -> None:
        """IX(7) = 9 is a pinned link; node count alone would call it a beam."""
        problem = build(
            nodes=[*SQUARE_NODES, (5, 0.0, 0.0), (6, 0.0, 0.0)],
            elements=[SQUARE, (2, 1, 5, 6, 0, 1, 1, 9)],
            materials=SOIL,
            boundaries=RESTRAINTS,
            control="   2    3    0    3    1    6    2  200    1    0    1    0",
        )
        assert problem.elements[2].kind.value == "link-pinned"
        assert "undefined-material" not in rules_fired(problem)


class TestRestraint:
    def test_no_boundary_conditions(self) -> None:
        problem = build(nodes=SQUARE_NODES, elements=[SQUARE], materials=SOIL)
        assert "singular" in messages_for(problem, "restraint")[0]

    def test_unrestrained_in_x(self) -> None:
        problem = build(
            nodes=SQUARE_NODES,
            elements=[SQUARE],
            materials=SOIL,
            boundaries=[(1, 0, 0.0, 1, 0.0, 1)],
        )
        assert "restrains displacement in X" in " ".join(messages_for(problem, "restraint"))


class TestOrdering:
    def test_errors_come_first(self) -> None:
        problem = build(
            nodes=[*SQUARE_NODES, (5, 90.0, 90.0)],
            elements=[SQUARE],
            materials=SOIL,
            boundaries=RESTRAINTS,
            control="   2    3    0    3    1    5    9  200    1    0    1    0",
        )
        ranks = [f.severity.rank for f in run_rules(problem)]
        assert ranks == sorted(ranks)


class TestMalformedInput:
    """Nothing may crash the reader. A bad file must produce findings."""

    @pytest.mark.parametrize(
        "content",
        [
            b"",
            b"not a cande file at all\r\n",
            b"STOP\r\n",
            b"\xff\xfe\x00\x01binary\x00",
            b"                   C-3.L3!!    1  000       xyz       abc\r\nSTOP\r\n",
        ],
        ids=["empty", "prose", "only-stop", "binary", "junk-in-numeric-fields"],
    )
    def test_reads_without_raising(self, tmp_path: Path, content: bytes) -> None:
        path = tmp_path / "rough.cid"
        path.write_bytes(content)
        run_rules(Problem.read(str(path)))  # must not raise

    def test_a_malformed_field_is_reported_by_name(self, tmp_path: Path) -> None:
        path = tmp_path / "rough.cid"
        record = "    1  000       xyz     56.81"
        path.write_bytes(f"{'C-3.L3':>25}!!{record}\r\nSTOP\r\n".encode("latin-1"))
        findings = [f for f in run_rules(Problem.read(str(path))) if f.rule == "field-decoding"]
        assert findings
        assert "'x'" in findings[0].message
        assert "not a number" in findings[0].message
        assert findings[0].index == 0

    def test_a_malformed_field_does_not_poison_its_neighbours(self, tmp_path: Path) -> None:
        """Only the bad field is lost; the rest of the record still reads."""
        path = tmp_path / "rough.cid"
        record = "    7  000       xyz     56.81"
        path.write_bytes(f"{'C-3.L3':>25}!!{record}\r\nSTOP\r\n".encode("latin-1"))
        node = Problem.read(str(path)).nodes[7]
        assert node.y == 56.81
        assert node.x == 0.0  # the unusable field falls back, and is reported

    def test_a_truncated_file_still_round_trips(self, tmp_path: Path, cid_path: Path) -> None:
        from candejar.io import dumps, read_cid

        truncated = cid_path.read_bytes()[:4000]
        path = tmp_path / "truncated.cid"
        path.write_bytes(truncated)
        assert dumps(read_cid(path)).encode("latin-1") == truncated
