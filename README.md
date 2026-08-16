# candejar

A CANDE preprocessor core — reads, validates and writes CANDE `.cid` input files.

CANDE (Culvert ANalysis and DEsign) is the FHWA/NCHRP finite element program for
buried structures. Its own 2025 User Manual states that the official GUI "has not
been fully updated for the new capabilities," and that using any capability added
since 2011 "requires" hand-editing the fixed-column input file. That covers the
Mohr/Coulomb soil model, the modified Duncan/Selig unload model, Continuous Load
Scaling, composite and death-option link elements, full pavement benefits for load
rating, and the April-2025 thermoplastic design criteria.

`candejar` exists to close that gap.

> **Status: pre-alpha.** Phase 0 (foundations) is complete: package layout, a real
> test corpus, and the line envelope. The codec, domain model and validation rules
> are Phase 1 and Phase 2. See [`docs/REDESIGN-PROPOSAL.md`](docs/REDESIGN-PROPOSAL.md)
> for the plan and [`docs/CID-FORMAT.md`](docs/CID-FORMAT.md) for the verified format.

## The format, in one line

Every command line in a `.cid` file has exactly one shape:

```python
f"{command_name:>25}!!" + fixed_column_record
```

The command name is right-justified in 25 characters; the data record always begins
at column 28. Verified against the CANDE-2025 User Manual and against every command
line of two real files of very different shape. That single rule is why a
declarative field spec can drive both the reader and the writer, rather than
scattered column constants and duplicated regexes.

```python
from candejar.io import split_line

line = split_line("                   C-4.L3!!    1  687   42    0    0    7    1    0")
line.name              # 'C-4.L3'
line.field(26, 30)     # '    7'   material number
line.field(31, 35)     # '    1'   birth load step
```

## Layout

```
src/candejar/
├── io/          fixed-column codec — reader and writer from one field spec
├── model/       typed domain model                          (Phase 1)
└── validate/    rules that run before CANDE does            (Phase 2)
tests/fixtures/  real .cid files, scrubbed — the corpus correctness is defined by
docs/            the proposal, and the verified format notes
legacy/          the previous Tkinter editor, kept runnable during the rewrite
```

Mesh generation, solver integration, parametric studies and the full application
live in the separate, proprietary `candejar_pro` distribution. The boundary is
deliberate and is explained in [§4.6 of the proposal](docs/REDESIGN-PROPOSAL.md).

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check .
mypy
```

Python 3.12+.

## The previous editor

The Tkinter tool this replaces still runs:

```bash
cd legacy && python main.py
```

It is not maintained. Its known defects are catalogued in
[§1 of the proposal](docs/REDESIGN-PROPOSAL.md) — the most consequential being that
it creates every interface element twice, duplicates interface material definitions
on save, and cannot see link elements, boundary conditions, or soil material
definitions at all.

## License

MIT — see [LICENSE](LICENSE).
