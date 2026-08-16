"""The ``candejar`` command line.

Deliberately built on the standard library alone.  The core has no runtime
dependencies, which keeps the browser build small and means ``pip install
candejar`` pulls in nothing at all.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from candejar import __version__
from candejar.io import dumps, read_cid
from candejar.model import Problem
from candejar.report import describe, outline, uncatalogued
from candejar.validate import Finding, Severity, run_rules

__all__ = ["main"]

_COLOURS = {
    Severity.ERROR: "\033[31m",
    Severity.WARNING: "\033[33m",
    Severity.NOTE: "\033[36m",
}
_BOLD = "\033[1m"
_DIM = "\033[2m"
_RESET = "\033[0m"


def _use_colour(stream: object) -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    return bool(getattr(stream, "isatty", lambda: False)())


class _Style:
    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled

    def __call__(self, text: str, code: str) -> str:
        return f"{code}{text}{_RESET}" if self.enabled else text

    def severity(self, finding: Finding) -> str:
        label = finding.severity.value
        return self(f"{label:>7}", _COLOURS[finding.severity])

    def bold(self, text: str) -> str:
        return self(text, _BOLD)

    def dim(self, text: str) -> str:
        return self(text, _DIM)


# ------------------------------------------------------------------ commands


def _cmd_check(args: argparse.Namespace) -> int:
    style = _Style(_use_colour(sys.stdout))
    worst = 0
    for path in args.files:
        problem = Problem(read_cid(path))
        findings = run_rules(problem)
        if args.severity == "error":
            findings = [f for f in findings if f.severity is Severity.ERROR]
        elif args.severity == "warning":
            findings = [f for f in findings if f.severity is not Severity.NOTE]

        if len(args.files) > 1:
            print(style.bold(str(path)))
        for finding in findings:
            where = f" line {finding.index + 1}" if finding.index is not None else ""
            print(f"{style.severity(finding)}  {finding.message}{style.dim(where)}")
            if finding.hint and args.verbose:
                print(f"{'':>9}{style.dim(finding.hint)}")

        errors = sum(1 for f in findings if f.severity is Severity.ERROR)
        warnings = sum(1 for f in findings if f.severity is Severity.WARNING)
        if errors:
            worst = 1
        tally = f"{errors} error{'s' * (errors != 1)}, {warnings} warning{'s' * (warnings != 1)}"
        print(style.dim(f"  {'-' * 5} {path.name}: {tally}"))
        if len(args.files) > 1:
            print()
    return worst


def _cmd_show(args: argparse.Namespace) -> int:
    problem = Problem(read_cid(args.file))
    style = _Style(_use_colour(sys.stdout))
    print(style.bold(str(args.file)))
    print()
    for line in describe(problem):
        print(line)
    if args.outline:
        print()
        print(style.bold("File outline"))
        for line in outline(problem):
            print(line)
    return 0


def _cmd_fmt(args: argparse.Namespace) -> int:
    """Verify that a file survives a read/write cycle unchanged."""
    style = _Style(_use_colour(sys.stdout))
    failures = 0
    for path in args.files:
        original = path.read_bytes()
        rendered = dumps(read_cid(path)).encode("latin-1")
        if rendered == original:
            print(f"{style.dim('unchanged')}  {path}")
            continue
        failures += 1
        print(f"{style('  CHANGED', _COLOURS[Severity.ERROR])}  {path}")
        print(
            style.dim(
                "            candejar would not reproduce this file byte-for-byte. "
                "Please report it with the file attached."
            )
        )
    return 1 if failures else 0


def _cmd_diff(args: argparse.Namespace) -> int:
    from candejar.diff import diff_problems, render_diff

    style = _Style(_use_colour(sys.stdout))
    left = Problem(read_cid(args.left))
    right = Problem(read_cid(args.right))
    changes = diff_problems(left, right)
    if not changes:
        print(style.dim("no semantic differences"))
        return 0
    for line in render_diff(changes):
        print(line)
    return 1 if args.exit_code else 0


def _cmd_serve(args: argparse.Namespace) -> int:
    from candejar.web import serve

    serve(args.file, host=args.host, port=args.port, open_browser=not args.no_browser)
    return 0


def _cmd_interfaces(args: argparse.Namespace) -> int:
    from candejar.io import write_cid
    from candejar.model import ElementKind
    from candejar.ops import insert_interfaces

    style = _Style(_use_colour(sys.stdout))
    problem = Problem(read_cid(args.file))
    beams = [
        element.number
        for element in problem.elements.values()
        if element.kind is ElementKind.BEAM
        and (args.group is None or element.material == args.group)
    ]
    if not beams:
        where = f" in pipe group {args.group}" if args.group else ""
        print(f"candejar: no beam elements found{where}", file=sys.stderr)
        return 1

    result = insert_interfaces(
        problem, beams, friction=args.friction, tensile=args.tensile, gap=args.gap
    )
    print(result.summary)
    for skipped in result.skipped:
        print(style.dim(f"  node {skipped.node}: {skipped.reason}"))
    if not result.created:
        return 0

    target = args.output or args.file
    if args.dry_run:
        print(style.dim(f"  (dry run; would have written {target})"))
        return 0
    write_cid(result.document, target)
    print(style.dim(f"  written to {target}"))
    return 0


def _cmd_types(args: argparse.Namespace) -> int:
    from candejar.io import LINE_TYPES

    style = _Style(_use_colour(sys.stdout))
    if args.file is not None:
        unknown = uncatalogued(Problem(read_cid(args.file)))
        print(style.bold("Present in this file but not yet catalogued"))
        for name, count in sorted(unknown.items()) or [("(none)", 0)]:
            print(f"  {count:>6,}  {name}")
        print()
    print(style.bold(f"Catalogued line types ({len(LINE_TYPES)})"))
    for name, spec in sorted(LINE_TYPES.items()):
        flag = "partial" if spec.partial else "complete"
        print(f"  {name:<16} {spec.source.value:<9} {flag:<9} {spec.doc}")
        if args.verbose:
            for spec_field in spec.fields:
                cols = f"{spec_field.start}-{spec_field.end}"
                print(f"      {cols:>7}  {spec_field.name:<22}{style.dim(spec_field.doc)}")
    return 0


# -------------------------------------------------------------------- parser


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="candejar",
        description="Read, check and explore CANDE .cid input files.",
    )
    parser.add_argument("--version", action="version", version=f"candejar {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check", help="report problems in a file before CANDE sees it")
    check.add_argument("files", nargs="+", type=Path)
    check.add_argument(
        "--severity",
        choices=("error", "warning", "all"),
        default="all",
        help="lowest severity to report (default: all)",
    )
    check.add_argument("-v", "--verbose", action="store_true", help="include hints")
    check.set_defaults(func=_cmd_check)

    show = sub.add_parser("show", help="summarise what a file contains")
    show.add_argument("file", type=Path)
    show.add_argument("--outline", action="store_true", help="list the line types in order")
    show.set_defaults(func=_cmd_show)

    fmt = sub.add_parser("fmt", help="verify a file round-trips byte-for-byte")
    fmt.add_argument("files", nargs="+", type=Path)
    fmt.set_defaults(func=_cmd_fmt)

    diff = sub.add_parser("diff", help="compare two files by meaning, not by line")
    diff.add_argument("left", type=Path)
    diff.add_argument("right", type=Path)
    diff.add_argument("--exit-code", action="store_true", help="exit 1 when differences are found")
    diff.set_defaults(func=_cmd_diff)

    serve = sub.add_parser("serve", help="open the mesh viewer in a browser")
    serve.add_argument("file", nargs="?", type=Path)
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8737)
    serve.add_argument("--no-browser", action="store_true")
    serve.set_defaults(func=_cmd_serve)

    interfaces = sub.add_parser(
        "interfaces", help="insert interface elements between the structure and the soil"
    )
    interfaces.add_argument("file", type=Path)
    interfaces.add_argument("-o", "--output", type=Path, help="write here instead of in place")
    interfaces.add_argument("--group", type=int, help="only this pipe group (default: all beams)")
    interfaces.add_argument("--friction", type=float, default=0.3)
    interfaces.add_argument("--tensile", type=float, default=0.0, help="tensile force capacity")
    interfaces.add_argument("--gap", type=float, default=0.0, help="initial gap distance")
    interfaces.add_argument("--dry-run", action="store_true", help="report without writing")
    interfaces.set_defaults(func=_cmd_interfaces)

    types = sub.add_parser("types", help="list the line types candejar understands")
    types.add_argument("file", nargs="?", type=Path)
    types.add_argument("-v", "--verbose", action="store_true", help="list every field")
    types.set_defaults(func=_cmd_types)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = args.func(args)
        return int(result)
    except FileNotFoundError as error:
        print(f"candejar: {error.filename}: no such file", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
