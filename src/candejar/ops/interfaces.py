"""Inserting interface elements between a structure and the soil around it.

This is the operation the previous editor existed for, and the one it got most
wrong: it created every interface element twice, appended a duplicate set of
material definitions on every save, silently used a horizontal normal wherever
it could not work the angle out, and dropped the tensile-force field entirely.

The rules CANDE actually imposes, from User Manual 5.5.6.4 and 5.6.7:

- An interface element has three nodes.  I and J are coincident and sit either
  side of the interface; K is a reference node belonging to no other element,
  and its number must exceed both I and J.
- Its material number indexes the *interface* material sequence, which is
  separate from the soil one.
- Interfaces on a curved surface have a different angle at every element, so
  each distinct angle needs its own material.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass, field

from candejar.io import Document, Record, make_record
from candejar.model import ElementKind, Problem
from candejar.ops.mutate import sync_control_counts, sync_limit_flags

__all__ = ["InterfaceResult", "Skipped", "insert_interfaces"]

_COINCIDENT = 1e-8


@dataclass(frozen=True, slots=True)
class Skipped:
    """A candidate node no interface could be built at, and why."""

    node: int
    reason: str


@dataclass
class InterfaceResult:
    """What an insertion did, and what it declined to do."""

    document: Document
    created: int = 0
    materials_added: int = 0
    materials_reused: int = 0
    skipped: list[Skipped] = field(default_factory=list)

    @property
    def summary(self) -> str:
        parts = [f"{self.created} interface element{'s' * (self.created != 1)}"]
        if self.materials_added:
            parts.append(f"{self.materials_added} new interface material(s)")
        if self.materials_reused:
            parts.append(f"{self.materials_reused} reused")
        if self.skipped:
            parts.append(f"{len(self.skipped)} node(s) skipped")
        return ", ".join(parts)


def _interface_angle(problem: Problem, shared: int, neighbours: tuple[int, int]) -> float | None:
    """The outward normal angle at ``shared``, in degrees, or ``None``.

    Taken as the perpendicular to the chord joining the two neighbouring beam
    endpoints, oriented away from that chord towards the shared node -- which
    for a culvert wall points out into the soil.

    Returns ``None`` when the three points are collinear, because then the
    outward side is genuinely undetermined.  Reporting that is the point: the
    previous editor defaulted to zero here and produced horizontal normals on
    vertical walls without saying so.
    """
    if shared not in problem.nodes:
        return None
    if any(n not in problem.nodes for n in neighbours):
        return None
    point = problem.nodes[shared]
    first, second = (problem.nodes[n] for n in neighbours)

    chord = (second.x - first.x, second.y - first.y)
    length = math.hypot(*chord)
    if length < _COINCIDENT:
        return None

    midpoint = ((first.x + second.x) / 2.0, (first.y + second.y) / 2.0)
    outward = (point.x - midpoint[0], point.y - midpoint[1])
    if math.hypot(*outward) < _COINCIDENT:
        return None  # collinear: which side is "out" is undefined

    normal = (-chord[1] / length, chord[0] / length)
    if normal[0] * outward[0] + normal[1] * outward[1] < 0:
        normal = (-normal[0], -normal[1])
    return math.degrees(math.atan2(normal[1], normal[0])) % 360.0


def _candidates(problem: Problem, beams: Iterable[int]) -> dict[int, tuple[int, int]]:
    """Nodes where two chosen beams meet, mapped to their far endpoints.

    Only nodes that also touch a continuum element qualify -- an interface needs
    soil on the other side of it -- and nodes already carrying an interface or
    link are left alone.
    """
    chosen = [
        problem.elements[n]
        for n in beams
        if n in problem.elements and problem.elements[n].kind is ElementKind.BEAM
    ]
    attached: set[int] = {
        node
        for element in problem.elements.values()
        if element.kind is ElementKind.INTERFACE or element.kind.is_link
        for node in element.nodes
    }
    continuum: set[int] = {
        node
        for element in problem.elements.values()
        if element.kind.is_continuum
        for node in element.nodes
    }

    meeting: dict[int, list[int]] = {}
    for element in chosen:
        for position, node in enumerate(element.nodes[:2]):
            far = element.nodes[1 - position]
            meeting.setdefault(node, []).append(far)

    return {
        node: (far[0], far[1])
        for node, far in meeting.items()
        if len(far) == 2 and node in continuum and node not in attached
    }


def _existing_interface_materials(problem: Problem) -> dict[tuple[float, ...], int]:
    """Interface materials already defined, keyed by their property values."""
    found: dict[tuple[float, ...], int] = {}
    for material in problem.interface_materials():
        if material.property_index is None:
            continue
        line = problem.document.lines[material.property_index]
        if not isinstance(line, Record) or line.name != "D-2.Interface":
            continue
        key = tuple(
            round(line.float_at(name) or 0.0, 6) for name in ("angle", "friction", "tensile", "gap")
        )
        found.setdefault(key, material.number)
    return found


def insert_interfaces(
    problem: Problem,
    beams: Iterable[int],
    *,
    friction: float = 0.3,
    tensile: float = 0.0,
    gap: float = 0.0,
) -> InterfaceResult:
    """Insert one interface element at each qualifying node of ``beams``.

    Exactly one per node -- the previous editor's habit of emitting two
    identical elements doubled the stiffness contributed at every joint.
    """
    document = problem.document
    candidates = _candidates(problem, beams)
    if not candidates:
        return InterfaceResult(document)

    next_node = max(problem.nodes, default=0)
    next_element = max(problem.elements, default=0)
    known = _existing_interface_materials(problem)
    next_material = max((m.number for m in problem.interface_materials()), default=0)

    new_nodes: list[Record] = []
    new_elements: list[Record] = []
    new_materials: list[Record] = []
    rewires: dict[int, dict[int, int]] = {}
    skipped: list[Skipped] = []
    created = added = reused = 0

    for outside in sorted(candidates):
        angle = _interface_angle(problem, outside, candidates[outside])
        if angle is None:
            skipped.append(
                Skipped(
                    outside,
                    "the two beams meeting here are collinear, so which side faces "
                    "the soil is undetermined; set the angle by hand",
                )
            )
            continue

        inside = next_node + 1
        reference = next_node + 2  # must exceed both I and J
        next_node += 2
        source = problem.nodes[outside]
        for number in (inside, reference):
            new_nodes.append(
                make_record("C-3.L3", node=number, reference=0, generate=0, x=source.x, y=source.y)
            )

        key = (round(angle, 6), round(friction, 6), round(tensile, 6), round(gap, 6))
        if key in known:
            material = known[key]
            reused += 1
        else:
            next_material += 1
            material = known[key] = next_material
            added += 1
            new_materials.append(
                make_record(
                    "D-1",
                    material=material,
                    model=6,
                    density=0,
                    name=f"Interface {material}",
                )
            )
            new_materials.append(
                make_record(
                    "D-2.Interface",
                    angle=angle,
                    friction=friction,
                    tensile=tensile,
                    gap=gap,
                )
            )

        next_element += 1
        created += 1
        new_elements.append(
            make_record(
                "C-4.L3",
                element=next_element,
                i=inside,
                j=outside,
                k=reference,
                l=0,
                material=material,
                birth=_birth_for(problem, outside),
                code=1,
            )
        )
        for beam in beams:
            if beam in problem.elements and outside in problem.elements[beam].nodes:
                rewires.setdefault(beam, {})[outside] = inside

    if not new_elements:
        return InterfaceResult(document, skipped=skipped)

    document = _rewire_beams(document, problem, rewires)
    document = document.inserted(document.after_last("C-3.L3"), *new_nodes)
    document = document.inserted(document.after_last("C-4.L3"), *new_elements)
    if new_materials:
        document = document.inserted(
            document.after_last(
                "D-1", "D-2.Interface", "D-2.Isotropic", "D-2.Duncan", "D-3.Duncan", "D-4.Duncan"
            ),
            *new_materials,
        )
    document = sync_limit_flags(sync_control_counts(document))
    return InterfaceResult(document, created, added, reused, skipped)


def _birth_for(problem: Problem, node: int) -> int:
    """The step an interface at ``node`` should enter: the earliest of its soil."""
    steps = [element.birth for element in problem.elements_using(node) if element.kind.is_continuum]
    return min(steps, default=1)


def _rewire_beams(
    document: Document, problem: Problem, rewires: dict[int, dict[int, int]]
) -> Document:
    """Point the chosen beams at their new inside nodes."""
    changes: dict[int, Record] = {}
    for beam, mapping in rewires.items():
        element = problem.elements[beam]
        line = document.lines[element.index]
        if not isinstance(line, Record):
            continue
        for slot in ("i", "j"):
            current = line.int_at(slot)
            if current in mapping:
                line = line.set(slot, mapping[current])
        changes[element.index] = line
    return document.with_changes(changes)
