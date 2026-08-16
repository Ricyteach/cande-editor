"""Reading and writing whole ``.cid`` files, without losing anything.

A :class:`Document` is the ordered sequence of a file's lines.  Lines whose
command name is catalogued in :mod:`candejar.io.registry` become
:class:`Record`\\ s with named, typed field access; every other line -- the
``STOP`` terminator, blank lines, and command lines whose type is not yet
catalogued -- is kept as :class:`Verbatim` and reproduced byte-for-byte.

That is the property the whole design rests on: ``dumps(loads(text)) == text``
for any file, whether or not this version understands its contents.  It is what
makes it safe to ship a codec that covers part of a large format.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, replace
from pathlib import Path

from candejar.io.line import TERMINATOR, CommandLine, join_line, split_line
from candejar.io.registry import spec_for
from candejar.io.spec import LineSpec

__all__ = [
    "Document",
    "Line",
    "Record",
    "Verbatim",
    "dumps",
    "loads",
    "read_cid",
    "write_cid",
]

_CRLF = "\r\n"


@dataclass(frozen=True, slots=True)
class Verbatim:
    """A line reproduced exactly as it was read."""

    text: str

    def render(self) -> str:
        return self.text


@dataclass(frozen=True, slots=True)
class Record:
    """A command line whose type is catalogued, with named field access."""

    line: CommandLine
    spec: LineSpec

    @property
    def name(self) -> str:
        return self.line.name

    def render(self) -> str:
        return join_line(self.line)

    def raw(self, name: str) -> str:
        """The unparsed text of a field, exactly as it sits in the file."""
        spec_field = self.spec[name]
        return self.line.field(spec_field.start, spec_field.end)

    def get(self, name: str) -> object | None:
        """The decoded value of a field, or ``None`` if the field is blank."""
        spec_field = self.spec[name]
        return spec_field.kind.decode(self.raw(name))

    def int_at(self, name: str) -> int | None:
        value = self.get(name)
        return None if value is None else int(value)  # type: ignore[call-overload]

    def float_at(self, name: str) -> float | None:
        value = self.get(name)
        return None if value is None else float(value)  # type: ignore[arg-type]

    def str_at(self, name: str) -> str | None:
        value = self.get(name)
        return None if value is None else str(value)

    def set(self, name: str, value: object) -> Record:
        """Return a copy with one field replaced.

        The rest of the record is untouched, down to the byte, so a write cannot
        perturb a neighbouring field -- including fields this version does not
        know about.
        """
        spec_field = self.spec[name]
        text = spec_field.kind.encode(value, spec_field.width)
        return replace(self, line=self.line.with_field(spec_field.start, spec_field.end, text))


Line = Record | Verbatim


@dataclass(frozen=True, slots=True)
class Document:
    """One ``.cid`` file, in order."""

    lines: tuple[Line, ...]
    newline: str = _CRLF
    trailing_newline: bool = True
    path: Path | None = None

    def __iter__(self) -> Iterator[Line]:
        return iter(self.lines)

    def __len__(self) -> int:
        return len(self.lines)

    def records(self, *names: str) -> Iterator[tuple[int, Record]]:
        """Yield ``(index, record)`` for records matching any of ``names``.

        With no names, yields every record.  The index is the position in
        :attr:`lines`, so it can be handed straight to :meth:`replaced`.
        """
        wanted = frozenset(names)
        for index, line in enumerate(self.lines):
            if isinstance(line, Record) and (not wanted or line.name in wanted):
                yield index, line

    def first(self, name: str) -> Record | None:
        for _, record in self.records(name):
            return record
        return None

    def count(self, name: str) -> int:
        return sum(1 for _ in self.records(name))

    def replaced(self, index: int, line: Line) -> Document:
        """Return a copy with the line at ``index`` replaced."""
        lines = list(self.lines)
        lines[index] = line
        return replace(self, lines=tuple(lines))

    def with_changes(self, changes: dict[int, Line]) -> Document:
        """Return a copy with several lines replaced at once."""
        if not changes:
            return self
        lines = list(self.lines)
        for index, line in changes.items():
            lines[index] = line
        return replace(self, lines=tuple(lines))


def loads(text: str, *, path: Path | None = None) -> Document:
    """Parse the full text of a ``.cid`` file."""
    newline = _CRLF if _CRLF in text else "\n"
    trailing = text.endswith(newline)
    body = text[: -len(newline)] if trailing else text
    lines: list[Line] = []
    for raw in body.split(newline):
        command = split_line(raw)
        spec = spec_for(command.name) if command is not None else None
        if command is not None and spec is not None:
            lines.append(Record(command, spec))
        else:
            lines.append(Verbatim(raw))
    return Document(tuple(lines), newline=newline, trailing_newline=trailing, path=path)


def dumps(document: Document) -> str:
    """Render a document back to text."""
    body = document.newline.join(line.render() for line in document.lines)
    return body + document.newline if document.trailing_newline else body


def read_cid(path: str | Path) -> Document:
    """Read a ``.cid`` file.

    Opened in binary: text mode would rewrite line endings on a non-Windows host
    and quietly destroy the fidelity this module exists to guarantee.
    """
    path = Path(path)
    return loads(path.read_bytes().decode("latin-1"), path=path)


def write_cid(document: Document, path: str | Path) -> None:
    """Write a document to a ``.cid`` file, preserving its line endings."""
    Path(path).write_bytes(dumps(document).encode("latin-1"))


def has_terminator(document: Document) -> bool:
    """Whether the document ends with the bare ``STOP`` line CANDE expects."""
    for line in reversed(document.lines):
        text = line.render().strip()
        if text:
            return text == TERMINATOR
    return False
