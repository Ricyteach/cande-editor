"""Fixed-column codec for CANDE ``.cid`` files."""

from candejar.io.line import (
    NAME_WIDTH,
    RECORD_START,
    SEPARATOR,
    TERMINATOR,
    CommandLine,
    join_line,
    split_line,
)

__all__ = [
    "NAME_WIDTH",
    "RECORD_START",
    "SEPARATOR",
    "TERMINATOR",
    "CommandLine",
    "join_line",
    "split_line",
]
