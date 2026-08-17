"""A semantic view of a CANDE problem, built over a :class:`~candejar.io.Document`.

The document stays authoritative: this layer indexes it and hands back typed
entities that remember where they came from, so an edit can be applied to the
exact line it belongs to and nothing else.  Nothing here copies the file into a
parallel representation that could drift out of step with it.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass, replace
from enum import Enum
from functools import cached_property

from candejar.io import Document, Record, read_cid

__all__ = [
    "Boundary",
    "ElementKind",
    "Extents",
    "Material",
    "MaterialModel",
    "Node",
    "PipeGroup",
    "PipeMaterial",
    "PipeSection",
    "Problem",
    "ProfileBand",
    "SoilElement",
]

#: Part B lines carrying pipe-wall material properties, by pipe type.
_PIPE_MATERIAL_LINES = frozenset({"B-1.Steel", "B-1.Alum"})

#: Part B lines carrying pipe-wall section properties, analysis form.
_PIPE_SECTION_LINES = frozenset({"B-2.Steel.A", "B-2.Alum.A"})


class ElementKind(Enum):
    """What an element actually is.

    CANDE distinguishes types by the *combination* of the class code ``IX(7)``
    and the number of nonzero nodes -- neither alone is enough.  A link element
    has two nonzero nodes and would look like a beam if the code were ignored.
    """

    BEAM = "beam"
    TRIANGLE = "triangle"
    QUAD = "quad"
    INTERFACE = "interface"
    LINK_FIXED = "link-fixed"
    LINK_PINNED = "link-pinned"
    COMPOSITE_LINK = "composite-link"
    UNKNOWN = "unknown"

    @property
    def is_continuum(self) -> bool:
        return self in (ElementKind.TRIANGLE, ElementKind.QUAD)

    @property
    def is_link(self) -> bool:
        return self in (
            ElementKind.LINK_FIXED,
            ElementKind.LINK_PINNED,
            ElementKind.COMPOSITE_LINK,
        )


class MaterialModel(Enum):
    """``D-1`` model numbers."""

    ISOTROPIC = 1
    ORTHOTROPIC = 2
    DUNCAN = 3
    OVERBURDEN = 4
    HARDIN = 5
    INTERFACE = 6
    COMPOSITE_LINK = 7
    MOHR_COULOMB = 8

    @property
    def label(self) -> str:
        return self.name.replace("_", "/").title()


def _kind_for(code: int, node_count: int) -> ElementKind:
    match code:
        case 1:
            return ElementKind.INTERFACE
        case 8:
            return ElementKind.LINK_FIXED
        case 9:
            return ElementKind.LINK_PINNED
        case 10 | 11:
            return ElementKind.COMPOSITE_LINK
        case 0:
            match node_count:
                case 2:
                    return ElementKind.BEAM
                case 3:
                    return ElementKind.TRIANGLE
                case 4:
                    return ElementKind.QUAD
    return ElementKind.UNKNOWN


@dataclass(frozen=True, slots=True)
class Node:
    number: int
    x: float
    y: float
    index: int
    """Position of the defining line in the document."""


@dataclass(frozen=True, slots=True)
class SoilElement:
    """Any element -- the name follows CANDE's ``C-4`` line, not the element type."""

    number: int
    nodes: tuple[int, ...]
    """Nonzero connectivity, in order."""
    material: int
    birth: int
    code: int
    index: int

    @property
    def kind(self) -> ElementKind:
        return _kind_for(self.code, len(self.nodes))


@dataclass(frozen=True, slots=True)
class Material:
    number: int
    model: int
    density: float | None
    name: str | None
    index: int
    property_index: int | None
    """Position of the following ``D-2`` line, when there is one."""

    @property
    def kind(self) -> MaterialModel | None:
        try:
            return MaterialModel(self.model)
        except ValueError:
            return None

    @property
    def is_interface(self) -> bool:
        return self.model == MaterialModel.INTERFACE.value


@dataclass(frozen=True, slots=True)
class Boundary:
    node: int
    x_code: int | None
    x_value: float | None
    y_code: int | None
    y_value: float | None
    angle: float | None
    step: int | None
    index: int

    @property
    def is_load(self) -> bool:
        """A force, rather than a prescribed displacement."""
        return (self.x_code == 0 and bool(self.x_value)) or (
            self.y_code == 0 and bool(self.y_value)
        )


@dataclass(frozen=True, slots=True)
class PipeMaterial:
    """The pipe wall's material properties, from the group's ``B-1``/``B-2`` line.

    ``modulus`` and ``strength`` are the short-term values.  Plastic creeps, so
    it is the one pipe type that also carries long-term values; for steel and
    aluminum those are ``None`` and the short-term pair is simply *the* pair.
    """

    modulus: float | None
    poisson: float | None
    yield_stress: float | None
    seam_strength: float | None
    density: float | None
    modulus_long_term: float | None = None
    strength_long_term: float | None = None


@dataclass(frozen=True, slots=True)
class PipeSection:
    """The pipe wall's section properties, from the group's ``B-2`` line.

    All **per unit length** of pipe, not totals -- these are the numbers a
    corrugation-and-gage table supplies.  ``plastic_modulus`` is steel's ``PZ``
    for deep corrugations; aluminum has no counterpart and leaves it ``None``.
    """

    area: float | None
    inertia: float | None
    section_modulus: float | None
    plastic_modulus: float | None


@dataclass(frozen=True, slots=True)
class ProfileBand:
    """One node range of a profile wall, from a ``B-3`` profile line.

    A profile wall is not uniform around the periphery, so its geometry is
    given per node range rather than as one section.  ``node_first`` and
    ``node_last`` say which nodes this band describes.
    """

    period: float | None
    height: float | None
    web_angle: float | None
    web_thickness: float | None
    node_first: int | None
    node_last: int | None
    index: int


@dataclass(frozen=True, slots=True)
class PipeGroup:
    number: int
    pipe_type: str | None
    index: int
    #: NPMATX, the connected beam element count.  Level 3 only.
    elements: int | None = None
    #: NPCAN, the canned-mesh code.  Level 2 only, and *not* an element count.
    canned_mesh: int | None = None
    material: PipeMaterial | None = None
    section: PipeSection | None = None
    #: WTYPE -- SMOOTH, GENERAL or PROFILE.  Plastic states this explicitly;
    #: for other pipe types it is not recorded and stays ``None``.
    wall_type: str | None = None
    #: Non-empty only for a profile wall, one entry per node range.
    profile: tuple[ProfileBand, ...] = ()


@dataclass(frozen=True, slots=True)
class Extents:
    min_x: float
    min_y: float
    max_x: float
    max_y: float

    @property
    def width(self) -> float:
        return self.max_x - self.min_x

    @property
    def height(self) -> float:
        return self.max_y - self.min_y


class Problem:
    """A CANDE problem, indexed from a document."""

    def __init__(self, document: Document) -> None:
        self.document = document

    @classmethod
    def read(cls, path: str) -> Problem:
        return cls(read_cid(path))

    # -------------------------------------------------------------- control
    @property
    def level(self) -> int | None:
        record = self.document.first("A-1")
        return record.int_at("level") if record else None

    @property
    def mode(self) -> str | None:
        record = self.document.first("A-1")
        return record.str_at("mode") if record else None

    @property
    def title(self) -> str:
        for name in ("A-1", "C-1.L3"):
            record = self.document.first(name)
            if record is not None and "title" in record.spec:
                title = record.str_at("title")
                if title:
                    return title
        return "(untitled)"

    @property
    def load_steps(self) -> int | None:
        record = self.document.first("C-2.L3")
        return record.int_at("load_steps") if record else None

    @property
    def load_scaling(self) -> int:
        """``Iscale``: 0 off, 1 CLS-EBM, 2 CLS-AAM-theta*."""
        record = self.document.first("C-2.L3")
        return (record.int_at("load_scaling") or 0) if record else 0

    @property
    def has_mesh(self) -> bool:
        """Whether the file defines its own mesh.

        Levels 1 and 2 let CANDE generate the mesh from a canned template, so
        there are no ``C-3``/``C-4`` lines to reason about and any rule that
        assumes explicit elements would only produce noise.
        """
        return bool(self.elements) or self.level == 3

    @property
    def uses_continuous_load_scaling(self) -> bool:
        """When true, ``C-5`` carries unreduced service loads, not RSL-reduced ones."""
        return self.load_scaling > 0

    # ------------------------------------------------------------- entities
    @cached_property
    def nodes(self) -> dict[int, Node]:
        found: dict[int, Node] = {}
        for index, record in self.document.records("C-3.L3"):
            number = record.int_at("node")
            if number is None:
                continue
            found[number] = Node(
                number=number,
                x=record.float_at("x") or 0.0,
                y=record.float_at("y") or 0.0,
                index=index,
            )
        return found

    @cached_property
    def elements(self) -> dict[int, SoilElement]:
        found: dict[int, SoilElement] = {}
        for index, record in self.document.records("C-4.L3"):
            number = record.int_at("element")
            if number is None:
                continue
            connectivity = tuple(
                value for value in (record.int_at(name) for name in ("i", "j", "k", "l")) if value
            )
            found[number] = SoilElement(
                number=number,
                nodes=connectivity,
                material=record.int_at("material") or 0,
                birth=record.int_at("birth") or 1,
                code=record.int_at("code") or 0,
                index=index,
            )
        return found

    @cached_property
    def materials(self) -> list[Material]:
        found: list[Material] = []
        lines = self.document.lines
        for index, record in self.document.records("D-1"):
            number = record.int_at("material")
            if number is None:
                continue
            following = index + 1
            has_properties = (
                following < len(lines)
                and isinstance(lines[following], Record)
                and lines[following].name.startswith("D-2")  # type: ignore[union-attr]
            )
            found.append(
                Material(
                    number=number,
                    model=record.int_at("model") or 0,
                    density=record.float_at("density"),
                    name=record.str_at("name"),
                    index=index,
                    property_index=following if has_properties else None,
                )
            )
        return found

    @cached_property
    def boundaries(self) -> list[Boundary]:
        return [
            Boundary(
                node=record.int_at("node") or 0,
                x_code=record.int_at("x_code"),
                x_value=record.float_at("x_value"),
                y_code=record.int_at("y_code"),
                y_value=record.float_at("y_value"),
                angle=record.float_at("angle"),
                step=record.int_at("step"),
                index=index,
            )
            for index, record in self.document.records("C-5.L3")
        ]

    @cached_property
    def pipe_groups(self) -> list[PipeGroup]:
        """One entry per pipe group, in file order.

        Part A/B repeats once per group, so an ``A-2`` line owns every Part B
        line that follows it until the next ``A-2``.  That ordering is the only
        thing tying a material to its group -- nothing carries a group number.

        Only catalogued Part B line types contribute.  A group whose pipe type
        has no spec yet (plastic, concrete, CONRIB, CONTUBE) simply has no
        material or section, rather than a wrong one.
        """
        groups: list[PipeGroup] = []
        for index, record in self.document.records():
            if record.name in ("A-2.L3", "A-2.L12"):
                level_3 = record.name == "A-2.L3"
                groups.append(
                    PipeGroup(
                        number=len(groups) + 1,
                        pipe_type=record.str_at("pipe_type"),
                        index=index,
                        elements=record.int_at("elements") if level_3 else None,
                        canned_mesh=None if level_3 else record.int_at("canned_mesh"),
                    )
                )
            elif not groups:
                continue
            elif record.name in _PIPE_MATERIAL_LINES:
                groups[-1] = replace(
                    groups[-1],
                    material=PipeMaterial(
                        modulus=record.float_at("modulus"),
                        poisson=record.float_at("poisson"),
                        yield_stress=record.float_at("yield_stress"),
                        seam_strength=record.float_at("seam_strength"),
                        density=record.float_at("density"),
                    ),
                )
            elif record.name == "B-1.Plastic":
                # Plastic splits across two lines: B-1 names the wall type and
                # the polymer, B-2 carries the numbers.
                groups[-1] = replace(groups[-1], wall_type=record.str_at("wall_type"))
            elif record.name == "B-2.Plastic":
                groups[-1] = replace(
                    groups[-1],
                    material=PipeMaterial(
                        modulus=record.float_at("modulus_short"),
                        poisson=record.float_at("poisson"),
                        yield_stress=record.float_at("strength_short"),
                        seam_strength=None,  # plastic has no seam
                        density=record.float_at("density"),
                        modulus_long_term=record.float_at("modulus_long"),
                        strength_long_term=record.float_at("strength_long"),
                    ),
                )
            elif record.name == "B-3.Plastic.A.Profile":
                groups[-1] = replace(
                    groups[-1],
                    profile=(
                        *groups[-1].profile,
                        ProfileBand(
                            period=record.float_at("period"),
                            height=record.float_at("height"),
                            web_angle=record.float_at("web_angle"),
                            web_thickness=record.float_at("web_thickness"),
                            node_first=record.int_at("node_first"),
                            node_last=record.int_at("node_last"),
                            index=index,
                        ),
                    ),
                )
            elif record.name in _PIPE_SECTION_LINES:
                groups[-1] = replace(
                    groups[-1],
                    section=PipeSection(
                        area=record.float_at("area"),
                        inertia=record.float_at("inertia"),
                        section_modulus=record.float_at("section_modulus"),
                        # Steel only; the aluminum spec has no such column.
                        plastic_modulus=(
                            record.float_at("deep_modulus")
                            if record.name == "B-2.Steel.A"
                            else None
                        ),
                    ),
                )
        return groups

    # ------------------------------------------------------------- geometry
    @cached_property
    def extents(self) -> Extents | None:
        if not self.nodes:
            return None
        xs = [node.x for node in self.nodes.values()]
        ys = [node.y for node in self.nodes.values()]
        return Extents(min(xs), min(ys), max(xs), max(ys))

    def polygon(self, element: SoilElement) -> list[tuple[float, float]]:
        """Corner coordinates, skipping any node the file never defined."""
        return [(self.nodes[n].x, self.nodes[n].y) for n in element.nodes if n in self.nodes]

    def centroid(self, element: SoilElement) -> tuple[float, float] | None:
        corners = self.polygon(element)
        if not corners:
            return None
        return (
            sum(x for x, _ in corners) / len(corners),
            sum(y for _, y in corners) / len(corners),
        )

    # -------------------------------------------------------------- summary
    def by_kind(self) -> dict[ElementKind, int]:
        counts: dict[ElementKind, int] = {}
        for element in self.elements.values():
            counts[element.kind] = counts.get(element.kind, 0) + 1
        return counts

    def soil_materials(self) -> list[Material]:
        return [m for m in self.materials if not m.is_interface]

    def interface_materials(self) -> list[Material]:
        return [m for m in self.materials if m.is_interface]

    def steps(self) -> Sequence[int]:
        return sorted({element.birth for element in self.elements.values()})

    def elements_using(self, node: int) -> Iterator[SoilElement]:
        for element in self.elements.values():
            if node in element.nodes:
                yield element
