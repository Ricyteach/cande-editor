"""Human-readable summaries of a problem, shared by the CLI and the web UI."""

from __future__ import annotations

from collections.abc import Iterator

from candejar.io import Record, Verbatim
from candejar.model import ElementKind, MaterialModel, Problem
from candejar.validate import Finding, Severity

__all__ = ["describe", "outline", "summary_rows", "uncatalogued"]

_KIND_LABELS = {
    ElementKind.BEAM: "beam",
    ElementKind.TRIANGLE: "triangle",
    ElementKind.QUAD: "quadrilateral",
    ElementKind.INTERFACE: "interface",
    ElementKind.LINK_FIXED: "link (fixed)",
    ElementKind.LINK_PINNED: "link (pinned)",
    ElementKind.COMPOSITE_LINK: "composite link",
    ElementKind.UNKNOWN: "unrecognised",
}

_SCALING = {
    0: "off",
    1: "Continuous Load Scaling (EBM)",
    2: "Continuous Load Scaling (AAMP-theta*)",
}


def summary_rows(problem: Problem) -> list[tuple[str, str]]:
    """Key facts about the problem, in the order an engineer would want them."""
    rows: list[tuple[str, str]] = [
        ("Title", problem.title),
        ("Mode", problem.mode or "unknown"),
        ("Level", str(problem.level) if problem.level else "unknown"),
    ]
    if problem.load_steps:
        rows.append(("Load steps", str(problem.load_steps)))
    if problem.pipe_groups:
        types = {group.pipe_type for group in problem.pipe_groups if group.pipe_type}
        listed = ", ".join(sorted(t.title() for t in types)) or "unspecified"
        rows.append(("Pipe groups", f"{len(problem.pipe_groups)} ({listed})"))
    if problem.has_mesh:
        rows.append(("Nodes", f"{len(problem.nodes):,}"))
        rows.append(("Elements", f"{len(problem.elements):,}"))
        rows.append(("Boundary conditions", f"{len(problem.boundaries):,}"))
    if problem.load_scaling:
        rows.append(("Live-load method", _SCALING.get(problem.load_scaling, "unknown")))
    extents = problem.extents
    if extents is not None:
        rows.append(
            (
                "Extents",
                f"{extents.width:,.1f} wide x {extents.height:,.1f} high "
                f"(x {extents.min_x:,.1f} to {extents.max_x:,.1f}, "
                f"y {extents.min_y:,.1f} to {extents.max_y:,.1f})",
            )
        )
    return rows


def describe(problem: Problem) -> Iterator[str]:
    """A plain-language account of what is in the file."""
    for label, value in summary_rows(problem):
        yield f"{label + ':':<22}{value}"

    counts = problem.by_kind()
    if counts:
        yield ""
        yield "Elements by type"
        for kind, count in sorted(counts.items(), key=lambda item: -item[1]):
            yield f"  {count:>6,}  {_KIND_LABELS[kind]}"

    steps = problem.steps()
    if steps:
        by_step = {step: 0 for step in steps}
        for element in problem.elements.values():
            by_step[element.birth] += 1
        yield ""
        yield "Construction sequence"
        for step in steps:
            yield f"  step {step:>3}  {by_step[step]:>6,} elements enter"

    soil = problem.soil_materials()
    interface = problem.interface_materials()
    if soil:
        yield ""
        yield "Soil materials"
        for material in soil:
            model = material.kind.label if material.kind else f"model {material.model}"
            density = f", density {material.density:g}" if material.density else ""
            yield f"  {material.number:>3}  {material.name or '(unnamed)':<24} {model}{density}"
    if interface:
        yield ""
        angles = _interface_angles(problem)
        yield f"Interface materials ({len(interface)})"
        if angles:
            yield f"  angles from {min(angles):.1f} to {max(angles):.1f} degrees"
        frictions = _interface_frictions(problem)
        if frictions:
            listed = ", ".join(f"{value:g}" for value in sorted(frictions))
            yield f"  friction coefficients: {listed}"

    unknown = uncatalogued(problem)
    if unknown:
        yield ""
        yield "Line types not yet catalogued (preserved verbatim)"
        for name, count in sorted(unknown.items()):
            yield f"  {count:>6,}  {name}"


def _interface_angles(problem: Problem) -> list[float]:
    return [
        value
        for _, record in problem.document.records("D-2.Interface")
        if (value := record.float_at("angle")) is not None
    ]


def _interface_frictions(problem: Problem) -> set[float]:
    return {
        value
        for _, record in problem.document.records("D-2.Interface")
        if (value := record.float_at("friction")) is not None
    }


def uncatalogued(problem: Problem) -> dict[str, int]:
    """Command names present in the file that have no field spec yet."""
    counts: dict[str, int] = {}
    for line in problem.document:
        if isinstance(line, Verbatim) and "!!" in line.text:
            name = line.text[:25].strip()
            counts[name] = counts.get(name, 0) + 1
    return counts


def outline(problem: Problem) -> Iterator[str]:
    """One line per run of consecutive same-named lines, in file order."""
    previous: str | None = None
    run = 0
    for line in problem.document:
        name = line.name if isinstance(line, Record) else line.text[:25].strip() or "(blank)"
        if name == previous:
            run += 1
            continue
        if previous is not None:
            yield f"  {run:>6,}  {previous}"
        previous, run = name, 1
    if previous is not None:
        yield f"  {run:>6,}  {previous}"


def model_label(model: int) -> str:
    try:
        return MaterialModel(model).label
    except ValueError:
        return f"model {model}"


def finding_prefix(finding: Finding) -> str:
    return {
        Severity.ERROR: "error",
        Severity.WARNING: "warning",
        Severity.NOTE: "note",
    }[finding.severity]
