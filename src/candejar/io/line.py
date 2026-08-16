"""Splitting and joining CANDE ``.cid`` command lines.

Every command line in a ``.cid`` file has exactly one shape::

    f"{command_name:>25}!!" + fixed_column_record

The command name is right-justified in 25 characters and followed by a literal
``!!``, so the fixed-column data record always begins at absolute column 28
(0-based index 27).  This was verified against the CANDE-2025 User Manual and
against every command line of two real files of very different shape; see
``docs/CID-FORMAT.md``.

The column tables in the manual are written relative to the start of the record,
so ``absolute_index == RECORD_START + (manual_column - 1)``.

This module deliberately knows nothing about *which* command names exist or what
their fields mean.  It only knows the envelope.
"""

from __future__ import annotations

from typing import NamedTuple

__all__ = [
    "NAME_WIDTH",
    "RECORD_START",
    "SEPARATOR",
    "TERMINATOR",
    "CommandLine",
    "join_line",
    "split_line",
]

#: Width of the right-justified command-name field.
NAME_WIDTH = 25

#: Literal separator between the command name and the data record.
SEPARATOR = "!!"

#: 0-based index at which the fixed-column data record begins.
RECORD_START = NAME_WIDTH + len(SEPARATOR)

#: Bare line that ends a ``.cid`` file.  Carries no name/separator envelope.
TERMINATOR = "STOP"


class CommandLine(NamedTuple):
    """A ``.cid`` line split into its command name and its data record.

    ``record`` is kept verbatim, including trailing whitespace, so that
    ``join_line(split_line(text)) == text`` for any conforming line.
    """

    name: str
    record: str

    def field(self, start: int, end: int) -> str:
        """Return manual columns ``start``..``end`` inclusive, 1-based.

        Short records are padded on the right, because trailing blank fields are
        routinely omitted from real files rather than space-filled.
        """
        if start < 1 or end < start:
            raise ValueError(f"invalid column range {start}-{end}")
        return self.record[start - 1 : end].ljust(end - start + 1)

    def with_field(self, start: int, end: int, text: str) -> CommandLine:
        """Return a copy with columns ``start``..``end`` replaced by ``text``.

        Only those columns change: every other byte of the record is carried
        through untouched.  Writing a field therefore cannot disturb a field the
        codec does not yet understand, which is what makes it safe to edit files
        containing line types this version has never seen.
        """
        width = end - start + 1
        if start < 1 or end < start:
            raise ValueError(f"invalid column range {start}-{end}")
        if len(text) != width:
            raise ValueError(
                f"expected {width} characters for columns {start}-{end}, got {len(text)}"
            )
        padded = self.record.ljust(end)
        return self._replace(record=padded[: start - 1] + text + padded[end:])


def split_line(text: str) -> CommandLine | None:
    """Split one line of a ``.cid`` file.

    Returns ``None`` for any line that is not a command line -- blank lines, the
    ``STOP`` terminator, and anything else the envelope does not describe.  Such
    lines must be preserved verbatim by a reader rather than discarded.

    The line-ending must already be stripped.
    """
    if len(text) < RECORD_START:
        return None
    if text[NAME_WIDTH:RECORD_START] != SEPARATOR:
        return None
    name = text[:NAME_WIDTH].strip()
    if not name:
        return None
    return CommandLine(name, text[RECORD_START:])


def join_line(line: CommandLine) -> str:
    """Render a :class:`CommandLine` back to its text form.

    Raises ``ValueError`` if the name does not fit the 25-character field, since
    silently truncating it would corrupt the file.
    """
    if len(line.name) > NAME_WIDTH:
        raise ValueError(f"command name {line.name!r} exceeds the {NAME_WIDTH}-character field")
    return f"{line.name:>{NAME_WIDTH}}{SEPARATOR}{line.record}"
