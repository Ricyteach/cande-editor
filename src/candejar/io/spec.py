"""Declarative field specifications for CANDE ``.cid`` line types.

A line type is a table of fields, each occupying a fixed column range within the
data record (see :mod:`candejar.io.line` for the envelope).  Both the reader and
the writer are driven from these tables, so adding a line type is data entry
rather than new code.

Columns are 1-based and inclusive, matching the User Manual exactly, so a spec
can be checked against the manual line by line without arithmetic.

Every spec records where it came from.  Some column tables were read directly
from the manual; others were derived from real files and cross-checked across
several of them.  The distinction matters when a field misbehaves -- see
:class:`Source`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from itertools import pairwise
from typing import Protocol, runtime_checkable

__all__ = [
    "Field",
    "FieldDecodeError",
    "FieldKind",
    "LineSpec",
    "Real",
    "Source",
    "Text",
    "Whole",
    "format_real",
]


class FieldDecodeError(ValueError):
    """A field's text does not match the type its spec declares.

    Raised rather than swallowed so the problem can be reported against the
    offending field instead of silently becoming a default value.  Real files
    do contain junk, and the engineer needs to be told which column it is in.
    """

    def __init__(self, text: str, kind: str) -> None:
        super().__init__(f"{text.strip()!r}, which is not {kind}")
        self.text = text
        self.kind = kind


class Source(Enum):
    """Where a spec's column positions came from."""

    #: Read directly from a CANDE User Manual input-instruction table.
    MANUAL = "manual"
    #: Derived from real files and cross-checked; not yet confirmed against the
    #: manual.  Correct for every file in the corpus, but treat with care.
    INFERRED = "inferred"


@runtime_checkable
class FieldKind(Protocol):
    """Decodes and encodes one field's text."""

    def decode(self, text: str) -> object | None: ...

    def encode(self, value: object, width: int) -> str: ...


class Text:
    """Left-justified text.  Blank decodes to ``None``."""

    def decode(self, text: str) -> str | None:
        stripped = text.strip()
        return stripped or None

    def encode(self, value: object, width: int) -> str:
        if value is None:
            return " " * width
        rendered = str(value)
        if len(rendered) > width:
            raise ValueError(f"{rendered!r} does not fit in {width} columns")
        return rendered.ljust(width)


class Whole:
    """Right-justified integer.  Blank decodes to ``None``."""

    def decode(self, text: str) -> int | None:
        stripped = text.strip()
        if not stripped:
            return None
        try:
            return int(stripped)
        except ValueError:
            raise FieldDecodeError(text, "a whole number") from None

    def encode(self, value: object, width: int) -> str:
        if value is None:
            return " " * width
        rendered = str(int(value))  # type: ignore[call-overload]
        if len(rendered) > width:
            raise ValueError(f"{rendered} does not fit in {width} columns")
        return rendered.rjust(width)


class Real:
    """Right-justified real number.  Blank decodes to ``None``."""

    def decode(self, text: str) -> float | None:
        stripped = text.strip()
        if not stripped:
            return None
        try:
            return float(stripped)
        except ValueError:
            raise FieldDecodeError(text, "a number") from None

    def encode(self, value: object, width: int) -> str:
        if value is None:
            return " " * width
        return format_real(float(value), width)  # type: ignore[arg-type]


def format_real(value: float, width: int) -> str:
    """Render ``value`` right-justified in ``width`` columns.

    CANDE reads plain Fortran reals, so the only requirement is that the number
    parses back to the same value and fits.  Decimal places are dropped one at a
    time until it fits, which keeps ordinary values looking like the ones a human
    typed rather than like ``4.4999999999999996e+01``.
    """
    for places in range(6, -1, -1):
        rendered = f"{value:.{places}f}"
        if len(rendered) <= width:
            # Trim a trailing ".0" only when it is not the whole number.
            if "." in rendered:
                trimmed = rendered.rstrip("0").rstrip(".")
                if trimmed and float(trimmed) == value and len(trimmed) <= width:
                    rendered = trimmed
            return rendered.rjust(width)
    rendered = f"{value:.{max(0, width - 8)}e}"
    if len(rendered) > width:
        raise ValueError(f"{value!r} cannot be rendered in {width} columns")
    return rendered.rjust(width)


@dataclass(frozen=True, slots=True)
class Field:
    """One fixed-column field within a data record.

    ``start`` and ``end`` are 1-based inclusive manual columns.
    """

    name: str
    start: int
    end: int
    kind: FieldKind
    doc: str = ""

    def __post_init__(self) -> None:
        if self.start < 1:
            raise ValueError(f"{self.name}: columns are 1-based, got start={self.start}")
        if self.end < self.start:
            raise ValueError(f"{self.name}: end {self.end} precedes start {self.start}")

    @property
    def width(self) -> int:
        return self.end - self.start + 1


@dataclass(frozen=True, slots=True)
class LineSpec:
    """The field table for one line type."""

    name: str
    fields: tuple[Field, ...]
    source: Source = Source.MANUAL
    doc: str = ""
    #: Set when the spec covers only part of the record.  The unlisted columns
    #: are still preserved verbatim; they simply cannot be addressed by name.
    partial: bool = False
    _by_name: dict[str, Field] = field(init=False, repr=False, compare=False, default_factory=dict)

    def __post_init__(self) -> None:
        by_name: dict[str, Field] = {}
        for spec_field in self.fields:
            if spec_field.name in by_name:
                raise ValueError(f"{self.name}: duplicate field {spec_field.name!r}")
            by_name[spec_field.name] = spec_field
        object.__setattr__(self, "_by_name", by_name)

        ordered = sorted(self.fields, key=lambda f: f.start)
        for earlier, later in pairwise(ordered):
            if later.start <= earlier.end:
                raise ValueError(
                    f"{self.name}: {earlier.name} (cols {earlier.start}-{earlier.end}) "
                    f"overlaps {later.name} (cols {later.start}-{later.end})"
                )

    def __getitem__(self, name: str) -> Field:
        try:
            return self._by_name[name]
        except KeyError:
            known = ", ".join(sorted(self._by_name))
            raise KeyError(f"{self.name} has no field {name!r}; known fields: {known}") from None

    def __contains__(self, name: str) -> bool:
        return name in self._by_name

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(f.name for f in self.fields)
