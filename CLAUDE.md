# candejar — orientation for agents

A CANDE preprocessor. CANDE is the FHWA/NCHRP finite element program for buried
culverts; its input is a fixed-column `.cid` file. Read
[`docs/CID-FORMAT.md`](docs/CID-FORMAT.md) before touching the codec and
[`docs/REDESIGN-PROPOSAL.md`](docs/REDESIGN-PROPOSAL.md) for why any of this exists.

The corpus sweep that task asked for has been done:
[`docs/CORPUS-FINDINGS.md`](docs/CORPUS-FINDINGS.md) records what 2,886 real
files said about the codec. Read it before changing the validation rules — two
of them were found to be crying wolf, and it says why.

## The one thing to understand

Every command line in a `.cid` file has exactly one shape:

```python
f"{command_name:>25}!!" + fixed_column_record
```

The command name is right-justified in 25 characters, so the data record always
begins at absolute column 28 (0-based index 27). Verified on every command line
of both fixtures. The User Manual's column tables are relative to the record, so
`absolute = 27 + (manual_column - 1)`.

## Invariants — do not break these

These are load-bearing. Each has tests; if you find yourself weakening a test to
make a change pass, the change is wrong.

1. **Round-trip is byte-exact.** `dumps(loads(text)) == text` for any file,
   understood or not. Files are CRLF and read in binary — text mode silently
   rewrites line endings off Windows and destroys this.
2. **Unknown line types round-trip verbatim.** A line whose type has no spec
   becomes a `Verbatim` and is reproduced exactly. Fidelity must never depend on
   coverage; this is what makes it safe to ship a codec that covers part of a
   large format.
3. **Writing a field touches only that field's columns.** `Record.set()` splices
   one column range. A write must not perturb a neighbouring field, including
   fields this version has never seen. Editing one material in the 1,288-element
   fixture changes exactly two bytes.
4. **Nothing crashes on a malformed file.** Decoding raises `FieldDecodeError`,
   the tolerant accessors catch it, and `rule_field_decoding` reports it by line
   and field name. Empty, prose, binary, truncated and mangled files all produce
   findings, never tracebacks.
5. **A file CANDE accepted must not be reported as broken.** Both fixtures
   produce zero errors, and a test asserts it. False positives are worse than
   missing rules — they train the user to ignore output.
6. **Specs record their provenance.** `Source.MANUAL` means the columns came from
   a User Manual table; `Source.INFERRED` means they were derived from real files.
   Never quietly promote one to the other.

## Layout

```
src/candejar/
├── io/          fixed-column codec: spec, registry, line envelope, document
├── model/       typed domain over a document; entities remember their line index
├── validate/    21 rules; findings carry severity, entity and line index
├── ops/         structural edits: interface insertion, renumbering, control sync
├── cli.py       check · show · fmt · diff · interfaces · types · serve
├── web.py       local viewer server (JSON API, no server-side state)
└── static/      the viewer, one page
tests/fixtures/  real .cid files, scrubbed — see its README for fidelity per file
legacy/          the previous Tkinter editor; unmaintained, still runnable
```

## Conventions

- **The core has no runtime dependencies.** Standard library only. It is destined
  for a WebAssembly build, so keep it that way; dev tooling goes in the `dev`
  extra.
- **Mesh generation, solver integration and studies belong in `candejar-pro`**, a
  separate distribution that must never ship to a browser. That repo does not
  exist yet. Do not put that code here.
- **Licence is proprietary, all rights reserved**, from commit `052c005` onward.
  Do not reintroduce MIT headers.
- Python 3.11+. `ruff check . && ruff format --check . && mypy && pytest` must all
  pass; CI runs them on 3.11, 3.12 and 3.13.
- **The viewer must be discoverable.** Features should surface at the moment
  they become relevant and stay out of the way until then — the affordance for
  editing a material appears when a material is selected, not in a menu the user
  has to already know about. Two things follow. Nothing important may live only
  in a keyboard shortcut, a right-click, or documentation. And a control that
  cannot do anything useful right now should be absent or visibly inert with the
  reason given, never present and silently failing. Prefer revealing depth on
  demand over a flat wall of every option at once; the format has hundreds of
  fields and showing them all is the failure mode to avoid.

## Some CANDE facts that are easy to get wrong

- **`NPT` is the highest node *number*, not a node count.** CANDE permits gaps in
  numbering. `NELEM` must be exact. `NBPTC` may exceed the real count. `NSMAT` and
  `NXMAT` are read only by the GUI and ignored on batch input.
- **Soil and interface materials are separate ID sequences** sharing one `D-1`
  block, distinguished by model number. A beam's `IX(5)` is neither — it is a pipe
  *group* number from Parts A and B.
- **Element type needs both the class code and the node count.** `IX(7)` of 8 or 9
  is a link element with two nonzero nodes; node count alone calls it a beam.
- **`NE` and `NNP` are I4 fields** — node and element numbers cap at 9999 in the
  definition columns, while references in `IX(1..4)` are I5.
- **Under Continuous Load Scaling (`Iscale` > 0) the `C-5` lines carry full
  service loads**, not RSL-reduced ones. The same numbers mean different things.

## Status

Phases 0–2 complete, Phase 3 (viewer) working. 200 tests. Mesh generation
(Phase 4) and solver integration (Phase 5) are not started.

Nine fixtures, spanning Levels 1–3, steel/plastic/concrete/aluminum, both
analysis and design mode, and — since the corpus sweep — quadrilateral elements
and LRFD. Round-trip is verified byte-exact against 2,886 real files.

Still uncovered: link elements, CONRIB and CONTUBE (which occur in no known
file), and 41 command names that have no spec and so round-trip verbatim. There
is also a known field-level write asymmetry that `fmt` cannot see — §4 of
`docs/CORPUS-FINDINGS.md` — which needs a decision on `Record.set()`.
