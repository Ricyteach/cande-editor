"""Semantic comparison of two CANDE problems.

A line diff of fixed-column text tells you almost nothing: a changed material
number looks the same as a changed load step, and moving one node rewrites a
line that says nothing about what moved.  This compares meaning instead.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from candejar.model import Problem
from candejar.report import summary_rows

__all__ = ["Change", "diff_problems", "render_diff"]


@dataclass(frozen=True, slots=True)
class Change:
    section: str
    detail: str


def _control_changes(left: Problem, right: Problem) -> Iterator[Change]:
    before = dict(summary_rows(left))
    after = dict(summary_rows(right))
    for key in dict.fromkeys([*before, *after]):
        was, now = before.get(key), after.get(key)
        if was != now:
            yield Change("control", f"{key}: {was or '(absent)'} -> {now or '(absent)'}")


def _material_changes(left: Problem, right: Problem) -> Iterator[Change]:
    def index(problem: Problem) -> dict[tuple[bool, int], tuple[int, float | None, str | None]]:
        return {(m.is_interface, m.number): (m.model, m.density, m.name) for m in problem.materials}

    before, after = index(left), index(right)
    for key in sorted(before.keys() | after.keys()):
        is_interface, number = key
        label = f"{'interface' if is_interface else 'soil'} material {number}"
        was, now = before.get(key), after.get(key)
        if was is None:
            yield Change("materials", f"+ {label} ({now[2] or 'unnamed'})")  # type: ignore[index]
        elif now is None:
            yield Change("materials", f"- {label} ({was[2] or 'unnamed'})")
        elif was != now:
            parts = []
            if was[0] != now[0]:
                parts.append(f"model {was[0]} -> {now[0]}")
            if was[1] != now[1]:
                parts.append(f"density {was[1]} -> {now[1]}")
            if was[2] != now[2]:
                parts.append(f"name {was[2]!r} -> {now[2]!r}")
            yield Change("materials", f"{label}: {', '.join(parts)}")


def _element_changes(left: Problem, right: Problem) -> Iterator[Change]:
    before, after = left.elements, right.elements
    added = sorted(after.keys() - before.keys())
    removed = sorted(before.keys() - after.keys())
    if added:
        kinds: dict[str, int] = {}
        for number in added:
            kind = after[number].kind.value
            kinds[kind] = kinds.get(kind, 0) + 1
        listed = ", ".join(f"{count} {kind}" for kind, count in sorted(kinds.items()))
        yield Change("elements", f"+{len(added)} elements ({listed})")
    if removed:
        yield Change("elements", f"-{len(removed)} elements")

    material_moves: dict[tuple[int, int], int] = {}
    step_moves: dict[tuple[int, int], int] = {}
    reconnected = 0
    for number in sorted(before.keys() & after.keys()):
        was, now = before[number], after[number]
        if was.material != now.material:
            key = (was.material, now.material)
            material_moves[key] = material_moves.get(key, 0) + 1
        if was.birth != now.birth:
            key = (was.birth, now.birth)
            step_moves[key] = step_moves.get(key, 0) + 1
        if was.nodes != now.nodes:
            reconnected += 1
    for (was_material, now_material), count in sorted(material_moves.items()):
        yield Change(
            "elements", f"{count} elements moved from material {was_material} to {now_material}"
        )
    for (was_step, now_step), count in sorted(step_moves.items()):
        yield Change("elements", f"{count} elements moved from step {was_step} to {now_step}")
    if reconnected:
        yield Change("elements", f"{reconnected} elements reconnected to different nodes")


def _node_changes(left: Problem, right: Problem) -> Iterator[Change]:
    before, after = left.nodes, right.nodes
    added = after.keys() - before.keys()
    removed = before.keys() - after.keys()
    if added:
        yield Change("nodes", f"+{len(added)} nodes")
    if removed:
        yield Change("nodes", f"-{len(removed)} nodes")
    moved = [
        number
        for number in before.keys() & after.keys()
        if (before[number].x, before[number].y) != (after[number].x, after[number].y)
    ]
    if moved:
        listed = ", ".join(str(n) for n in sorted(moved)[:5])
        more = f" and {len(moved) - 5} more" if len(moved) > 5 else ""
        yield Change("nodes", f"{len(moved)} nodes moved ({listed}{more})")


def _boundary_changes(left: Problem, right: Problem) -> Iterator[Change]:
    def index(problem: Problem) -> dict[tuple[int, int | None], tuple[object, ...]]:
        return {
            (b.node, b.step): (b.x_code, b.x_value, b.y_code, b.y_value, b.angle)
            for b in problem.boundaries
        }

    before, after = index(left), index(right)
    for key in sorted(before.keys() | after.keys(), key=lambda k: (k[0], k[1] or 0)):
        node, step = key
        was, now = before.get(key), after.get(key)
        where = f"node {node}" + (f" at step {step}" if step else "")
        if was is None:
            yield Change("boundary conditions", f"+ condition on {where}")
        elif now is None:
            yield Change("boundary conditions", f"- condition on {where}")
        elif was != now:
            yield Change("boundary conditions", f"{where} changed")


def diff_problems(left: Problem, right: Problem) -> list[Change]:
    """Every semantic difference between two problems, grouped by section."""
    return [
        change
        for producer in (
            _control_changes,
            _node_changes,
            _element_changes,
            _material_changes,
            _boundary_changes,
        )
        for change in producer(left, right)
    ]


def render_diff(changes: list[Change]) -> Iterator[str]:
    """Format changes for a terminal, grouped under their section."""
    section: str | None = None
    for change in changes:
        if change.section != section:
            section = change.section
            yield section
        yield f"  {change.detail}"
