"""Fixed-column codec for CANDE ``.cid`` files."""

from candejar.io.document import (
    Document,
    Line,
    Record,
    Verbatim,
    dumps,
    has_terminator,
    loads,
    make_record,
    read_cid,
    write_cid,
)
from candejar.io.line import (
    NAME_WIDTH,
    RECORD_START,
    SEPARATOR,
    TERMINATOR,
    CommandLine,
    join_line,
    split_line,
)
from candejar.io.registry import LINE_TYPES, spec_for
from candejar.io.spec import Field, LineSpec, Real, Source, Text, Whole

__all__ = [
    "LINE_TYPES",
    "NAME_WIDTH",
    "RECORD_START",
    "SEPARATOR",
    "TERMINATOR",
    "CommandLine",
    "Document",
    "Field",
    "Line",
    "LineSpec",
    "Real",
    "Record",
    "Source",
    "Text",
    "Verbatim",
    "Whole",
    "dumps",
    "has_terminator",
    "join_line",
    "loads",
    "make_record",
    "read_cid",
    "spec_for",
    "split_line",
    "write_cid",
]
