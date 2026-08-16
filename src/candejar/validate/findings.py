"""Findings produced by the validation rules."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

__all__ = ["Finding", "Severity"]


class Severity(Enum):
    """How much a finding matters.

    ``ERROR`` means CANDE will reject the file or silently compute the wrong
    answer.  ``WARNING`` means the model is probably not what was intended.
    ``NOTE`` is information worth surfacing that is not a defect.
    """

    ERROR = "error"
    WARNING = "warning"
    NOTE = "note"

    @property
    def rank(self) -> int:
        return {"error": 0, "warning": 1, "note": 2}[self.value]


@dataclass(frozen=True, slots=True)
class Finding:
    """One thing worth telling the engineer about."""

    rule: str
    """Stable identifier, e.g. ``element-count``.  Safe to filter on."""
    severity: Severity
    message: str
    """One sentence naming the offending entity and what is wrong with it."""
    entity: str | None = None
    """Human label for the thing at fault, e.g. ``element 412``."""
    index: int | None = None
    """Document line index, so a UI can jump straight to it."""
    hint: str | None = None
    """What to do about it, when that is not obvious from the message."""

    def __str__(self) -> str:
        where = f" [{self.entity}]" if self.entity else ""
        return f"{self.severity.value}: {self.message}{where}"
