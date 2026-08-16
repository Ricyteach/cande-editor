"""Model operations: structural edits that keep the document consistent."""

from candejar.ops.interfaces import InterfaceResult, Skipped, insert_interfaces
from candejar.ops.mutate import renumber_elements, sync_control_counts, sync_limit_flags

__all__ = [
    "InterfaceResult",
    "Skipped",
    "insert_interfaces",
    "renumber_elements",
    "sync_control_counts",
    "sync_limit_flags",
]
