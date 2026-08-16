"""Tests for structural edits: interface insertion and document housekeeping.

The interface tests are written against the specific ways the previous editor
got this wrong, because those are the failure modes with real files behind them.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from candejar.io import Record, dumps, loads
from candejar.model import ElementKind, Problem
from candejar.ops import (
    insert_interfaces,
    renumber_elements,
    sync_control_counts,
    sync_limit_flags,
)
from candejar.validate import Severity, run_rules


def line(name: str, record: str) -> str:
    return f"{name:>25}!!{record}"


def arch_on_soil(
    nodes: dict[int, tuple[float, float]] | None = None,
    *,
    control: str = "   2    3    0    3    1    6    8  200    1    0    1    0",
) -> Problem:
    """A four-beam arch sharing its nodes with four soil triangles.

    Node 3 is the crown, so the outward normal there must come out at 90
    degrees, and the two flanks must be symmetric about it.
    """
    nodes = nodes or {1: (0, 0), 2: (1, 1), 3: (2, 1.5), 4: (3, 1), 5: (4, 0), 6: (2, -2)}
    lines = [line("A-1", "ANALYS   3 0  1Arch on soil"), line("C-2.L3", control)]
    for number, (x, y) in nodes.items():
        lines.append(line("C-3.L3", f" {number:4d}  0 0{x:9.2f}{y:10.2f}"))
    elements = [
        (1, 1, 2, 0, 0, 1, 1, 0),
        (2, 2, 3, 0, 0, 1, 1, 0),
        (3, 3, 4, 0, 0, 1, 1, 0),
        (4, 4, 5, 0, 0, 1, 1, 0),
        (5, 1, 2, 6, 0, 1, 1, 0),
        (6, 2, 3, 6, 0, 1, 1, 0),
        (7, 3, 4, 6, 0, 1, 1, 0),
        (8, 4, 5, 6, 0, 1, 1, 0),
    ]
    for number, i, j, k, ll, material, birth, code in elements:
        lines.append(
            line(
                "C-4.L3",
                f" {number:4d}{i:5d}{j:5d}{k:5d}{ll:5d}{material:5d}{birth:5d}{code:5d}",
            )
        )
    for node in (1, 5):
        lines.append(
            line("C-5.L3", f" {node:4d}{1:5d}{0.0:10.2f}{1:5d}{0.0:10.2f}{0.0:10.2f}{1:5d}")
        )
    lines.append(line("D-1", f" {1:4d}{1:5d}{120:10d}Fill"))
    lines.append(line("D-2.Isotropic", f"{3000:10d}{0.35:10.2f}"))
    lines.append("STOP")
    return Problem(loads("\r\n".join(lines) + "\r\n"))


BEAMS = [1, 2, 3, 4]


class TestInterfaceInsertion:
    def test_creates_exactly_one_element_per_shared_node(self) -> None:
        """The previous editor emitted two identical elements at every node."""
        result = insert_interfaces(arch_on_soil(), BEAMS)
        after = Problem(result.document)
        interfaces = [e for e in after.elements.values() if e.kind is ElementKind.INTERFACE]
        assert result.created == 3  # nodes 2, 3 and 4 are shared; 1 and 5 are ends
        assert len(interfaces) == 3
        assert len({tuple(sorted(e.nodes)) for e in interfaces}) == 3

    def test_k_node_exceeds_i_and_j(self) -> None:
        after = Problem(insert_interfaces(arch_on_soil(), BEAMS).document)
        for element in after.elements.values():
            if element.kind is ElementKind.INTERFACE:
                i, j, k = element.nodes
                assert k > max(i, j)

    def test_k_node_belongs_to_nothing_else(self) -> None:
        after = Problem(insert_interfaces(arch_on_soil(), BEAMS).document)
        for element in after.elements.values():
            if element.kind is ElementKind.INTERFACE:
                users = list(after.elements_using(element.nodes[2]))
                assert users == [element]

    def test_new_nodes_sit_on_top_of_the_originals(self) -> None:
        after = Problem(insert_interfaces(arch_on_soil(), BEAMS).document)
        for element in after.elements.values():
            if element.kind is ElementKind.INTERFACE:
                inside, outside, _ = element.nodes
                assert (after.nodes[inside].x, after.nodes[inside].y) == (
                    after.nodes[outside].x,
                    after.nodes[outside].y,
                )

    def test_beams_are_rewired_to_the_inside_nodes(self) -> None:
        after = Problem(insert_interfaces(arch_on_soil(), BEAMS).document)
        beams = {e.number: e.nodes for e in after.elements.values() if e.kind is ElementKind.BEAM}
        # The chain must still be connected end to end, but no longer through
        # the original nodes 2, 3 and 4, which now belong to the soil side.
        assert beams[1][0] == 1 and beams[4][1] == 5
        assert beams[1][1] == beams[2][0]
        assert beams[2][1] == beams[3][0]
        assert beams[3][1] == beams[4][0]
        assert not ({2, 3, 4} & {node for nodes in beams.values() for node in nodes})

    def test_crown_normal_points_straight_up(self) -> None:
        result = insert_interfaces(arch_on_soil(), BEAMS)
        angles = sorted(
            record.float_at("angle") or 0.0
            for _, record in result.document.records("D-2.Interface")
        )
        assert 90.0 in angles
        # A symmetric arch must give angles symmetric about the crown.
        assert pytest.approx(angles[0] + angles[-1]) == 180.0

    def test_properties_are_written_including_the_tensile_field(self) -> None:
        """The field the previous editor dropped."""
        result = insert_interfaces(arch_on_soil(), BEAMS, friction=0.45, tensile=12.0, gap=0.1)
        for _, record in result.document.records("D-2.Interface"):
            assert record.float_at("friction") == 0.45
            assert record.float_at("tensile") == 12.0
            assert record.float_at("gap") == 0.1

    def test_one_material_per_distinct_angle(self) -> None:
        result = insert_interfaces(arch_on_soil(), BEAMS)
        assert result.materials_added == 3  # a curved surface needs one each
        after = Problem(result.document)
        assert len(after.interface_materials()) == 3

    def test_repeated_angles_share_a_material(self) -> None:
        """Two peaks of the same shape must not each get their own material."""
        zigzag = {1: (0, 0), 2: (1, 1), 3: (2, 0), 4: (3, 1), 5: (4, 0), 6: (2, -2)}
        result = insert_interfaces(arch_on_soil(zigzag), BEAMS)
        assert result.created == 3
        assert result.materials_added == 2  # the two peaks share one
        assert result.materials_reused == 1

    def test_existing_materials_are_reused_not_duplicated(self) -> None:
        """Inserting twice must not append a second copy of the same materials."""
        first = insert_interfaces(arch_on_soil(), BEAMS)
        problem = Problem(first.document)
        beams = [e.number for e in problem.elements.values() if e.kind is ElementKind.BEAM]
        second = insert_interfaces(problem, beams)
        # Everything is already interfaced, so there is nothing left to do.
        assert second.created == 0
        assert Problem(second.document).interface_materials() == problem.interface_materials()

    def test_collinear_beams_are_skipped_and_explained(self) -> None:
        """The previous editor silently used a horizontal normal here."""
        straight = {1: (0, 0), 2: (1, 0), 3: (2, 0), 4: (3, 0), 5: (4, 0), 6: (2, -2)}
        result = insert_interfaces(arch_on_soil(straight), BEAMS)
        assert result.created == 0
        assert {s.node for s in result.skipped} == {2, 3, 4}
        assert "collinear" in result.skipped[0].reason

    def test_nodes_with_no_soil_are_not_candidates(self) -> None:
        """An interface needs something on the other side of it."""
        problem = arch_on_soil()
        # Drop the soil triangles; the beams still share nodes with each other.
        document = problem.document.removed(
            *[e.index for e in problem.elements.values() if e.kind.is_continuum]
        )
        assert insert_interfaces(Problem(document), BEAMS).created == 0

    def test_birth_step_follows_the_surrounding_soil(self) -> None:
        problem = arch_on_soil()
        document = problem.document
        changes = {
            e.index: document.lines[e.index].set("birth", 4)  # type: ignore[union-attr]
            for e in problem.elements.values()
            if e.kind.is_continuum
        }
        result = insert_interfaces(Problem(document.with_changes(changes)), BEAMS)
        after = Problem(result.document)
        births = {e.birth for e in after.elements.values() if e.kind is ElementKind.INTERFACE}
        assert births == {4}

    def test_result_is_valid_and_round_trips(self) -> None:
        result = insert_interfaces(arch_on_soil(), BEAMS)
        after = Problem(result.document)
        errors = [f for f in run_rules(after) if f.severity is Severity.ERROR]
        assert errors == [], "\n".join(str(f) for f in errors)
        assert dumps(loads(dumps(result.document))) == dumps(result.document)

    def test_control_counts_are_brought_up_to_date(self) -> None:
        result = insert_interfaces(arch_on_soil(), BEAMS)
        control = result.document.first("C-2.L3")
        assert control is not None
        after = Problem(result.document)
        assert control.int_at("element_count") == len(after.elements)
        assert control.int_at("highest_node") == max(after.nodes)


class TestHousekeeping:
    def test_limit_flag_moves_to_the_new_last_line(self) -> None:
        problem = arch_on_soil()
        document = sync_limit_flags(problem.document)
        rows = [r for _, r in document.records("C-3.L3")]
        assert [r.str_at("limit") for r in rows] == [None] * (len(rows) - 1) + ["L"]

    def test_a_stale_flag_in_the_middle_is_cleared(self) -> None:
        problem = arch_on_soil()
        index, record = next(problem.document.records("C-3.L3"))
        document = sync_limit_flags(problem.document.replaced(index, record.set("limit", "L")))
        rows = [r.str_at("limit") for _, r in document.records("C-3.L3")]
        assert rows[0] is None
        assert rows[-1] == "L"

    def test_nelem_is_made_exact_and_nbptc_only_grows(self) -> None:
        problem = arch_on_soil(
            control="   2    3    0    3    1    6   99    1    1    0    1    0"
        )
        control = sync_control_counts(problem.document).first("C-2.L3")
        assert control is not None
        assert control.int_at("element_count") == 8  # corrected down to the truth
        assert control.int_at("boundary_count") == 2  # raised to cover the C-5 lines

    def test_npt_is_the_highest_number_not_the_count(self) -> None:
        sparse = {1: (0, 0), 2: (1, 1), 3: (2, 1.5), 4: (3, 1), 5: (4, 0), 60: (2, -2)}
        problem = arch_on_soil(sparse)
        # Element 5 onwards references node 6, which no longer exists; that is a
        # separate finding. What matters here is what NPT gets set to.
        control = sync_control_counts(problem.document).first("C-2.L3")
        assert control is not None
        assert control.int_at("highest_node") == 60

    def test_renumbering_makes_elements_ascend_from_one(self) -> None:
        problem = arch_on_soil()
        document = problem.document
        index, record = next(document.records("C-4.L3"))
        document = renumber_elements(document.replaced(index, record.set("element", 77)))
        numbers = [r.int_at("element") for _, r in document.records("C-4.L3")]
        assert numbers == list(range(1, len(numbers) + 1))


class TestAgainstTheEngineersFile:
    """Reproduce the interfaces in a real production model.

    The Level 3 fixture was interfaced by hand in the CANDE GUI by a practising
    engineer. Stripping those interfaces out, re-inserting them, and comparing
    is the strongest check available: it tests the candidate-node rule, the node
    splitting, the beam rewiring and the angle calculation all at once, against
    an answer nobody involved in writing this code chose.
    """

    @staticmethod
    def _without_interfaces(problem: Problem) -> Problem:
        """Undo the interfaces: drop them and merge each split node pair back."""
        document = problem.document
        merge: dict[int, int] = {}
        drop: list[int] = []
        for element in problem.elements.values():
            if element.kind is not ElementKind.INTERFACE:
                continue
            inside, outside, reference = element.nodes
            merge[inside] = outside
            drop += [element.index, problem.nodes[inside].index, problem.nodes[reference].index]
        for material in problem.interface_materials():
            drop.append(material.index)
            if material.property_index is not None:
                drop.append(material.property_index)

        changes = {}
        for element in problem.elements.values():
            if element.kind is ElementKind.INTERFACE or not any(n in merge for n in element.nodes):
                continue
            line = document.lines[element.index]
            assert isinstance(line, Record)
            for slot in ("i", "j", "k", "l"):
                value = line.int_at(slot)
                if value in merge:
                    line = line.set(slot, merge[value])
            changes[element.index] = line

        rebuilt = document.with_changes(changes).removed(*drop)
        return Problem(sync_limit_flags(sync_control_counts(renumber_elements(rebuilt))))

    @staticmethod
    def _angles_by_position(problem: Problem) -> dict[tuple[float, float], float]:
        by_material = {}
        for material in problem.interface_materials():
            if material.property_index is None:
                continue
            line = problem.document.lines[material.property_index]
            assert isinstance(line, Record)
            by_material[material.number] = line.float_at("angle")
        found = {}
        for element in problem.elements.values():
            if element.kind is ElementKind.INTERFACE:
                node = problem.nodes[element.nodes[1]]
                found[(round(node.x, 2), round(node.y, 2))] = by_material[element.material]
        return found

    def test_reinsertion_matches_the_original(self, level3_document_path: Path) -> None:
        original = Problem.read(str(level3_document_path))
        stripped = self._without_interfaces(original)
        assert not [e for e in stripped.elements.values() if e.kind is ElementKind.INTERFACE]

        beams = [e.number for e in stripped.elements.values() if e.kind is ElementKind.BEAM]
        result = insert_interfaces(stripped, beams, friction=0.3, tensile=10.0)
        rebuilt = Problem(result.document)

        assert result.created == 57  # exactly what the engineer placed
        assert len(rebuilt.elements) == len(original.elements)
        assert max(rebuilt.nodes) == max(original.nodes)

        theirs = self._angles_by_position(original)
        ours = self._angles_by_position(rebuilt)
        assert ours.keys() == theirs.keys(), "interfaces landed in different places"
        worst = max(abs((ours[k] - theirs[k] + 180) % 360 - 180) for k in theirs)
        assert worst < 0.1, f"angles differ from the engineer's by up to {worst:.2f} degrees"

    def test_reinsertion_is_valid(self, level3_document_path: Path) -> None:
        stripped = self._without_interfaces(Problem.read(str(level3_document_path)))
        beams = [e.number for e in stripped.elements.values() if e.kind is ElementKind.BEAM]
        rebuilt = Problem(insert_interfaces(stripped, beams).document)
        errors = [f for f in run_rules(rebuilt) if f.severity is Severity.ERROR]
        assert errors == [], "\n".join(str(f) for f in errors)
