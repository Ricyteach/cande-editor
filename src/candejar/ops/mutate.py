"""Document housekeeping that every structural edit has to get right.

Adding or removing nodes and elements is not just a matter of writing lines.
The group-terminator flags have to move, and the ``C-2`` control counts have to
be brought back into agreement with reality -- each according to its own rule,
which is not the same rule for all of them.  Getting either wrong produces a
file CANDE rejects, or worse, one it accepts and misreads.
"""

from __future__ import annotations

from candejar.io import Document, Record

__all__ = ["renumber_elements", "sync_control_counts", "sync_limit_flags"]

#: Line types whose group ends are marked by an ``L`` in the first column.
_LIMITED = ("C-3.L3", "C-4.L3", "C-5.L3", "D-1")


def sync_limit_flags(document: Document) -> Document:
    """Put the ``L`` terminator on the last line of each group and nowhere else.

    CANDE reads a group until it sees ``L`` in column 1, so a stale flag in the
    middle truncates the group silently and a missing one runs it into whatever
    follows.
    """
    changes: dict[int, Record] = {}
    for name in _LIMITED:
        indexed = [(index, record) for index, record in document.records(name)]
        if not indexed:
            continue
        last_index = indexed[-1][0]
        for index, record in indexed:
            if "limit" not in record.spec:
                continue
            wanted = "L" if index == last_index else None
            if (record.str_at("limit") or None) != wanted:
                changes[index] = record.set("limit", wanted)
    return document.with_changes(changes)


def sync_control_counts(document: Document) -> Document:
    """Bring the ``C-2`` control fields back into agreement with the mesh.

    Each field follows its own rule, per User Manual 5.5.6.2:

    - ``NELEM`` must equal the element count exactly.
    - ``NPT`` is the highest node *number* used, not how many nodes there are.
    - ``NBPTC`` may exceed the actual count, so it is only raised, never lowered.
    - ``NSMAT`` and ``NXMAT`` are read only by the GUI, so they are kept at least
      as large as the highest material number rather than pinned to a count.
    - ``NINC`` must cover the latest birth step.
    """
    control = None
    control_index = -1
    for index, record in document.records("C-2.L3"):
        control, control_index = record, index
        break
    if control is None:
        return document

    nodes = [
        number
        for _, record in document.records("C-3.L3")
        if (number := record.int_at("node")) is not None
    ]
    elements = [record for _, record in document.records("C-4.L3")]
    boundaries = sum(1 for _ in document.records("C-5.L3"))

    soil, interface = _material_highs(document)
    steps = [step for record in elements if (step := record.int_at("birth")) is not None]

    updated = control
    if nodes:
        updated = updated.set("highest_node", max(nodes))
    updated = updated.set("element_count", len(elements))
    if boundaries > (updated.int_at("boundary_count") or 0):
        updated = updated.set("boundary_count", boundaries)
    if soil and soil > (updated.int_at("soil_materials") or 0):
        updated = updated.set("soil_materials", soil)
    if interface and interface > (updated.int_at("interface_materials") or 0):
        updated = updated.set("interface_materials", interface)
    if steps and max(steps) > (updated.int_at("load_steps") or 0):
        updated = updated.set("load_steps", max(steps))

    return document.replaced(control_index, updated)


def _material_highs(document: Document) -> tuple[int, int]:
    """Highest soil and highest interface material number defined."""
    soil = interface = 0
    for _, record in document.records("D-1"):
        number = record.int_at("material") or 0
        if record.int_at("model") == 6:
            interface = max(interface, number)
        else:
            soil = max(soil, number)
    return soil, interface


def renumber_elements(document: Document) -> Document:
    """Renumber ``C-4`` lines 1..n in file order.

    CANDE requires element numbers to start at 1 and ascend, so any insertion
    that is not at the end needs this afterwards.
    """
    changes: dict[int, Record] = {}
    for position, (index, record) in enumerate(document.records("C-4.L3"), start=1):
        if record.int_at("element") != position:
            changes[index] = record.set("element", position)
    return document.with_changes(changes)
