"""Validation rules that run before CANDE does.

Each rule is a function from a :class:`~candejar.model.Problem` to findings.
Rules are deliberately small and independently readable: a rule that cannot be
explained in a sentence is usually two rules.

Every message names the offending entity and says what is wrong with it, because
a finding the engineer has to go and decode is barely better than no finding.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Callable, Iterator

from candejar.io import has_terminator
from candejar.model import ElementKind, MaterialModel, Problem
from candejar.validate.findings import Finding, Severity

__all__ = ["RULES", "Rule", "run_rules"]

Rule = Callable[[Problem], Iterator[Finding]]

# Aspect ratio beyond which a continuum element is likely to behave poorly.
_ASPECT_LIMIT = 10.0


def _error(rule: str, message: str, **kwargs: object) -> Finding:
    return Finding(rule=rule, severity=Severity.ERROR, message=message, **kwargs)  # type: ignore[arg-type]


def _warn(rule: str, message: str, **kwargs: object) -> Finding:
    return Finding(rule=rule, severity=Severity.WARNING, message=message, **kwargs)  # type: ignore[arg-type]


def _note(rule: str, message: str, **kwargs: object) -> Finding:
    return Finding(rule=rule, severity=Severity.NOTE, message=message, **kwargs)  # type: ignore[arg-type]


# --------------------------------------------------------------- structure


def rule_terminator(problem: Problem) -> Iterator[Finding]:
    """The file must end with a bare ``STOP``."""
    if not has_terminator(problem.document):
        yield _error(
            "terminator",
            "The file does not end with a STOP line, so CANDE will read past the end.",
            hint="Append a line containing exactly STOP.",
        )


def rule_undefined_nodes(problem: Problem) -> Iterator[Finding]:
    """Every node an element references must exist, or be Laplace-generated."""
    defined = problem.nodes.keys()
    missing: dict[int, list[int]] = defaultdict(list)
    for element in problem.elements.values():
        for node in element.nodes:
            if node not in defined:
                missing[node].append(element.number)
    for node, elements in sorted(missing.items()):
        listed = ", ".join(str(e) for e in elements[:4])
        more = f" and {len(elements) - 4} more" if len(elements) > 4 else ""
        yield _note(
            "undefined-node",
            f"Node {node} is used by element{'s' if len(elements) > 1 else ''} "
            f"{listed}{more} but has no C-3 line, so CANDE will place it by "
            f"Laplace generation.",
            entity=f"node {node}",
        )


def rule_orphan_nodes(problem: Problem) -> Iterator[Finding]:
    """A node no element uses is dead weight and often a leftover."""
    if not problem.has_mesh:
        return
    used = {node for element in problem.elements.values() for node in element.nodes}
    orphans = sorted(set(problem.nodes) - used)
    for node in orphans[:20]:
        yield _warn(
            "orphan-node",
            f"Node {node} is defined but no element uses it.",
            entity=f"node {node}",
            index=problem.nodes[node].index,
        )
    if len(orphans) > 20:
        yield _warn(
            "orphan-node",
            f"{len(orphans) - 20} further nodes are defined but unused.",
        )


def rule_coincident_nodes(problem: Problem) -> Iterator[Finding]:
    """Nodes at identical coordinates are legitimate at interfaces, suspect elsewhere."""
    interface_nodes = {
        node
        for element in problem.elements.values()
        if element.kind is ElementKind.INTERFACE or element.kind.is_link
        for node in element.nodes
    }
    by_position: dict[tuple[float, float], list[int]] = defaultdict(list)
    for node in problem.nodes.values():
        by_position[(node.x, node.y)].append(node.number)
    for position, numbers in sorted(by_position.items()):
        if len(numbers) < 2:
            continue
        unexplained = [n for n in numbers if n not in interface_nodes]
        if len(unexplained) < 2:
            continue  # an interface or link accounts for the duplication
        listed = ", ".join(str(n) for n in unexplained)
        yield _warn(
            "coincident-nodes",
            f"Nodes {listed} share the position ({position[0]:g}, {position[1]:g}) "
            f"but no interface or link element joins them.",
            entity=f"node {unexplained[0]}",
            index=problem.nodes[unexplained[0]].index,
        )


def rule_duplicate_elements(problem: Problem) -> Iterator[Finding]:
    """Two elements on the same nodes are almost always a mistake.

    The previous editor created interface elements in identical pairs, so this
    is a real failure mode with real files behind it.
    """
    by_nodes: dict[tuple[int, ...], list[int]] = defaultdict(list)
    for element in problem.elements.values():
        by_nodes[tuple(sorted(element.nodes))].append(element.number)
    for nodes, numbers in sorted(by_nodes.items()):
        if len(numbers) < 2 or not nodes:
            continue
        listed = ", ".join(str(n) for n in numbers)
        yield _error(
            "duplicate-element",
            f"Elements {listed} are all defined on nodes {list(nodes)}.",
            entity=f"element {numbers[0]}",
            index=problem.elements[numbers[0]].index,
            hint="Duplicated elements double the stiffness they contribute.",
        )


def rule_element_numbering(problem: Problem) -> Iterator[Finding]:
    """``C-4`` numbers must ascend from 1."""
    numbers = sorted(problem.elements)
    if not numbers:
        return
    if numbers[0] != 1:
        yield _error(
            "element-numbering",
            f"Element numbering starts at {numbers[0]}; CANDE requires it to start at 1.",
            entity=f"element {numbers[0]}",
            index=problem.elements[numbers[0]].index,
        )
    over = [n for n in numbers if n > 9999]
    if over:
        yield _error(
            "element-numbering",
            f"Element {over[0]} exceeds 9999, which does not fit the 4-column C-4 field.",
            entity=f"element {over[0]}",
            index=problem.elements[over[0]].index,
        )


def rule_node_numbering(problem: Problem) -> Iterator[Finding]:
    """``C-3`` node numbers occupy a 4-column field."""
    over = sorted(n for n in problem.nodes if n > 9999)
    if over:
        yield _error(
            "node-numbering",
            f"Node {over[0]} exceeds 9999, which does not fit the 4-column C-3 field.",
            entity=f"node {over[0]}",
            index=problem.nodes[over[0]].index,
        )


# ---------------------------------------------------------------- controls


def rule_element_count(problem: Problem) -> Iterator[Finding]:
    """``NELEM`` must match the element count exactly (User Manual 5.5.6.2)."""
    record = problem.document.first("C-2.L3")
    if record is None:
        return
    declared = record.int_at("element_count")
    actual = len(problem.elements)
    if declared is not None and declared != actual:
        yield _error(
            "element-count",
            f"C-2 declares NELEM = {declared} but the file defines {actual} elements; "
            f"CANDE requires these to match exactly.",
            entity="C-2.L3",
            index=next(i for i, _ in problem.document.records("C-2.L3")),
        )


def rule_highest_node(problem: Problem) -> Iterator[Finding]:
    """``NPT`` is the highest node *number*, not a count."""
    record = problem.document.first("C-2.L3")
    if record is None or not problem.nodes:
        return
    declared = record.int_at("highest_node")
    highest = max(problem.nodes)
    index = next(i for i, _ in problem.document.records("C-2.L3"))
    if declared is None:
        return
    if declared < highest:
        yield _error(
            "highest-node",
            f"C-2 declares NPT = {declared} but node {highest} is defined. NPT is the "
            f"highest node number used, not the node count.",
            entity="C-2.L3",
            index=index,
        )
    elif declared > highest:
        yield _note(
            "highest-node",
            f"C-2 declares NPT = {declared} but the highest node defined is {highest}.",
            entity="C-2.L3",
            index=index,
        )


def rule_boundary_count(problem: Problem) -> Iterator[Finding]:
    """``NBPTC`` may exceed the actual count, but never fall short."""
    record = problem.document.first("C-2.L3")
    if record is None:
        return
    declared = record.int_at("boundary_count")
    actual = len(problem.boundaries)
    if declared is not None and declared < actual:
        yield _error(
            "boundary-count",
            f"C-2 declares NBPTC = {declared} but the file has {actual} C-5 lines; "
            f"NBPTC may exceed the actual count but must not be smaller.",
            entity="C-2.L3",
            index=next(i for i, _ in problem.document.records("C-2.L3")),
        )


def rule_load_steps(problem: Problem) -> Iterator[Finding]:
    """Construction steps must be contiguous from 1 and within ``NINC``."""
    steps = problem.steps()
    if not steps:
        return
    declared = problem.load_steps
    if declared is not None:
        beyond = [s for s in steps if s > declared]
        if beyond:
            offenders = [e for e in problem.elements.values() if e.birth == beyond[0]]
            yield _error(
                "load-step-range",
                f"Elements are born at step {beyond[0]} but C-2 declares only "
                f"{declared} load steps.",
                entity=f"element {offenders[0].number}" if offenders else None,
                index=offenders[0].index if offenders else None,
            )
    missing = [s for s in range(1, max(steps) + 1) if s not in steps]
    if missing:
        listed = ", ".join(str(s) for s in missing[:6])
        yield _warn(
            "load-step-gap",
            f"No element is born at step{'s' if len(missing) > 1 else ''} {listed}; "
            f"construction steps are normally contiguous.",
        )


# --------------------------------------------------------------- materials


def rule_undefined_materials(problem: Problem) -> Iterator[Finding]:
    """Every material an element references must be defined in Part D.

    Soil and interface materials are independent ID sequences, so they are
    checked separately.  Beam materials are pipe *group* numbers from Parts A
    and B, not Part D materials at all.
    """
    if not problem.has_mesh:
        return
    soil_ids = {m.number for m in problem.soil_materials()}
    interface_ids = {m.number for m in problem.interface_materials()}
    groups = len(problem.pipe_groups)

    reported: set[tuple[str, int]] = set()
    for element in problem.elements.values():
        kind = element.kind
        if kind.is_continuum:
            if soil_ids and element.material not in soil_ids:
                key = ("soil", element.material)
                if key not in reported:
                    reported.add(key)
                    yield _error(
                        "undefined-material",
                        f"Element {element.number} references soil material "
                        f"{element.material}, which no D-1 line defines.",
                        entity=f"element {element.number}",
                        index=element.index,
                    )
        elif kind is ElementKind.INTERFACE:
            if interface_ids and element.material not in interface_ids:
                key = ("interface", element.material)
                if key not in reported:
                    reported.add(key)
                    yield _error(
                        "undefined-material",
                        f"Interface element {element.number} references interface "
                        f"material {element.material}, which no D-1 line defines.",
                        entity=f"element {element.number}",
                        index=element.index,
                    )
        elif kind is ElementKind.BEAM and groups and not 1 <= element.material <= groups:
            key = ("group", element.material)
            if key not in reported:
                reported.add(key)
                yield _error(
                    "undefined-material",
                    f"Beam element {element.number} references pipe group "
                    f"{element.material}, but the file defines {groups}.",
                    entity=f"element {element.number}",
                    index=element.index,
                )


def rule_unused_materials(problem: Problem) -> Iterator[Finding]:
    """A material nothing references is usually a leftover.

    Only meaningful for a user-defined mesh: at Levels 1 and 2 the mesh is
    generated by CANDE, so materials are referenced by elements the file never
    lists.
    """
    if not problem.has_mesh:
        return
    soil_used = {e.material for e in problem.elements.values() if e.kind.is_continuum}
    interface_used = {
        e.material for e in problem.elements.values() if e.kind is ElementKind.INTERFACE
    }
    for material in problem.materials:
        used = interface_used if material.is_interface else soil_used
        if material.number not in used:
            what = "Interface material" if material.is_interface else "Soil material"
            label = f" ({material.name})" if material.name else ""
            yield _warn(
                "unused-material",
                f"{what} {material.number}{label} is defined but no element uses it.",
                entity=f"material {material.number}",
                index=material.index,
            )


def rule_material_models(problem: Problem) -> Iterator[Finding]:
    """``D-1`` model numbers must be ones CANDE knows."""
    for material in problem.materials:
        if material.kind is None:
            yield _error(
                "material-model",
                f"Material {material.number} declares model {material.model}, which is "
                f"not one of the eight CANDE soil or interface models.",
                entity=f"material {material.number}",
                index=material.index,
            )


def rule_interface_material_model(problem: Problem) -> Iterator[Finding]:
    """An interface element must reference a material whose model is Interface."""
    by_number = {m.number: m for m in problem.interface_materials()}
    soil_by_number = {m.number: m for m in problem.soil_materials()}
    for element in problem.elements.values():
        if element.kind is not ElementKind.INTERFACE:
            continue
        if element.material in by_number:
            continue
        wrong = soil_by_number.get(element.material)
        if wrong is not None:
            model = MaterialModel(wrong.model).label if wrong.kind else wrong.model
            yield _error(
                "interface-material-model",
                f"Interface element {element.number} references material "
                f"{element.material}, which is a {model} material, not an interface.",
                entity=f"element {element.number}",
                index=element.index,
            )


# ---------------------------------------------------------------- geometry


def _signed_area(corners: list[tuple[float, float]]) -> float:
    total = 0.0
    for (x1, y1), (x2, y2) in zip(corners, corners[1:] + corners[:1], strict=True):
        total += x1 * y2 - x2 * y1
    return total / 2.0


def rule_element_geometry(problem: Problem) -> Iterator[Finding]:
    """Continuum elements must have real, positive, sanely-shaped area."""
    for element in problem.elements.values():
        if not element.kind.is_continuum:
            continue
        corners = problem.polygon(element)
        if len(corners) != len(element.nodes):
            continue  # nodes will be Laplace-generated; geometry unknown yet
        area = _signed_area(corners)
        if abs(area) < 1e-9:
            yield _error(
                "element-geometry",
                f"Element {element.number} has zero area; its nodes are collinear or coincident.",
                entity=f"element {element.number}",
                index=element.index,
            )
            continue
        if area < 0:
            yield _warn(
                "element-geometry",
                f"Element {element.number} is numbered clockwise (negative area); "
                f"CANDE expects counter-clockwise connectivity.",
                entity=f"element {element.number}",
                index=element.index,
            )
        xs = [x for x, _ in corners]
        ys = [y for _, y in corners]
        width, height = max(xs) - min(xs), max(ys) - min(ys)
        short, long_ = sorted((width, height))
        if short > 0 and long_ / short > _ASPECT_LIMIT:
            yield _warn(
                "element-aspect",
                f"Element {element.number} has an aspect ratio of {long_ / short:.0f}:1, "
                f"beyond the {_ASPECT_LIMIT:.0f}:1 guideline.",
                entity=f"element {element.number}",
                index=element.index,
            )


def rule_interface_connectivity(problem: Problem) -> Iterator[Finding]:
    """The interface and link K node must exceed I and J, and belong to nothing else."""
    shared: Counter[int] = Counter()
    for element in problem.elements.values():
        for node in element.nodes:
            shared[node] += 1

    for element in problem.elements.values():
        if element.kind is not ElementKind.INTERFACE and not element.kind.is_link:
            continue
        if len(element.nodes) < 3:
            yield _error(
                "interface-connectivity",
                f"{element.kind.value.title()} element {element.number} has "
                f"{len(element.nodes)} nodes; it needs three, the third being a "
                f"reference node.",
                entity=f"element {element.number}",
                index=element.index,
            )
            continue
        i, j, k = element.nodes[0], element.nodes[1], element.nodes[2]
        if k <= max(i, j):
            yield _error(
                "interface-connectivity",
                f"Element {element.number} has K node {k}, which does not exceed its "
                f"I and J nodes ({i}, {j}) as CANDE requires.",
                entity=f"element {element.number}",
                index=element.index,
            )
        if shared[k] > 1:
            yield _error(
                "interface-connectivity",
                f"Element {element.number} shares its K node {k} with another element; "
                f"the K node must belong to this element alone.",
                entity=f"element {element.number}",
                index=element.index,
            )


def rule_restraint(problem: Problem) -> Iterator[Finding]:
    """The mesh must be restrained against rigid-body translation."""
    if not problem.has_mesh:
        return
    if not problem.boundaries:
        if problem.elements:
            yield _error(
                "restraint",
                "The model has no boundary conditions, so it is free to translate and "
                "the stiffness matrix will be singular.",
            )
        return
    fixed_x = any(b.x_code == 1 for b in problem.boundaries)
    fixed_y = any(b.y_code == 1 for b in problem.boundaries)
    if not fixed_x:
        yield _error(
            "restraint",
            "No boundary condition restrains displacement in X; the model can "
            "translate horizontally.",
        )
    if not fixed_y:
        yield _error(
            "restraint",
            "No boundary condition restrains displacement in Y; the model can "
            "translate vertically.",
        )


def rule_boundary_nodes_exist(problem: Problem) -> Iterator[Finding]:
    """A boundary condition on a node that does not exist does nothing."""
    for boundary in problem.boundaries:
        if boundary.node and boundary.node not in problem.nodes:
            yield _warn(
                "boundary-node",
                f"A boundary condition is applied to node {boundary.node}, which has no C-3 line.",
                entity=f"node {boundary.node}",
                index=boundary.index,
            )


# ------------------------------------------------------------- load scaling


def rule_live_load_window(problem: Problem) -> Iterator[Finding]:
    """Under CLS, live loads must fall inside the declared step window."""
    control = problem.document.first("C-2b.L3")
    if control is None or not problem.uses_continuous_load_scaling:
        return
    start = control.int_at("live_load_start")
    end = control.int_at("live_load_end")
    if start is None:
        return
    end = end if end is not None else start
    for boundary in problem.boundaries:
        if not boundary.is_load or boundary.step is None:
            continue
        if not start <= boundary.step <= end:
            yield _warn(
                "live-load-window",
                f"A load on node {boundary.node} is applied at step {boundary.step}, "
                f"outside the CLS live-load window of steps {start} to {end}.",
                entity=f"node {boundary.node}",
                index=boundary.index,
                hint="Loads outside the window are not scaled for load spreading.",
            )


def rule_load_scaling_note(problem: Problem) -> Iterator[Finding]:
    """Tell the engineer how to read the load values they are looking at."""
    if not problem.uses_continuous_load_scaling:
        return
    method = "CLS-AAM-theta*" if problem.load_scaling == 2 else "CLS-EBM"
    yield _note(
        "load-scaling",
        f"This model uses Continuous Load Scaling ({method}), so the C-5 live loads "
        f"are full service loads, not RSL-reduced ones.",
        entity="C-2.L3",
    )


RULES: tuple[Rule, ...] = (
    rule_terminator,
    rule_undefined_nodes,
    rule_orphan_nodes,
    rule_coincident_nodes,
    rule_duplicate_elements,
    rule_element_numbering,
    rule_node_numbering,
    rule_element_count,
    rule_highest_node,
    rule_boundary_count,
    rule_load_steps,
    rule_undefined_materials,
    rule_unused_materials,
    rule_material_models,
    rule_interface_material_model,
    rule_element_geometry,
    rule_interface_connectivity,
    rule_restraint,
    rule_boundary_nodes_exist,
    rule_live_load_window,
    rule_load_scaling_note,
)


def run_rules(problem: Problem, rules: tuple[Rule, ...] = RULES) -> list[Finding]:
    """Run every rule, most severe first, then in document order."""
    findings = [finding for rule in rules for finding in rule(problem)]
    return sorted(
        findings,
        key=lambda f: (f.severity.rank, f.index if f.index is not None else 1 << 30),
    )
