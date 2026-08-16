# candejar

A CANDE preprocessor — reads, checks, explores and edits CANDE `.cid` input files.

CANDE (Culvert ANalysis and DEsign) is the FHWA/NCHRP finite element program for buried
structures. Its own 2025 User Manual states that the official GUI "has not been fully
updated for the new capabilities," and that using any capability added since 2011
"requires" hand-editing the fixed-column input file. That covers the Mohr/Coulomb soil
model, the modified Duncan/Selig unload model, Continuous Load Scaling, composite and
death-option link elements, full pavement benefits for load rating, and the April-2025
thermoplastic design criteria.

`candejar` exists to close that gap.

> **Status: early, but usable.** The codec, model, validation engine, CLI and mesh viewer
> work on real files. Mesh generation and solver integration are not built yet. See
> [`docs/REDESIGN-PROPOSAL.md`](docs/REDESIGN-PROPOSAL.md) for the plan and
> [`docs/CID-FORMAT.md`](docs/CID-FORMAT.md) for the verified format.

## Install

```bash
pip install -e .
```

Python 3.11 or newer. No runtime dependencies.

## Use

### Look at a model

```bash
candejar serve culvert.cid
```

Opens a browser on `127.0.0.1:8737` with the mesh drawn and coloured by material,
construction step, or element type. Click an element to inspect it, drag to box-select,
reassign material or load step, save. Nothing leaves your machine.

Run `candejar serve` with no file and drop one onto the page.

### Check a model before CANDE sees it

```bash
$ candejar check culvert.cid
  error  C-2 declares NELEM = 1288 but the file defines 1291 elements; CANDE
         requires these to match exactly. line 1024
  error  Elements 412, 413 are all defined on nodes [88, 91, 214]. line 1438
warning  Element 907 has an aspect ratio of 34:1, beyond the 10:1 guideline. line 1933
   note  This model uses Continuous Load Scaling (CLS-AAM-theta*), so the C-5 live
         loads are full service loads, not RSL-reduced ones.
  ----- culvert.cid: 2 errors, 1 warning
```

Exits non-zero when there are errors, so it drops into a pre-run script or a git hook.

### Understand a model you did not build

```bash
$ candejar show culvert.cid
Title:                Three-cell arch, 18 in cover, ASD
Level:                3
Load steps:           10
Pipe groups:          9 (Plastic)
Nodes:                800
Elements:             1,288
Live-load method:     Continuous Load Scaling (AAMP-theta*)
Extents:              488.0 wide x 95.8 high (x -244.0 to 244.0, y -33.0 to 62.8)

Elements by type
   1,159  triangle
      72  beam
      57  interface

Construction sequence
  step   1     509 elements enter
  step   2      98 elements enter
  ...
```

### Compare two models by meaning

```bash
$ candejar diff before.cid after.cid
elements
  23 elements moved from material 7 to 3
  20 elements moved from step 1 to 5
materials
  soil material 2: density 120.0 -> 135.0
```

A line diff of fixed-column text tells you nothing. This tells you what changed.

### Insert interfaces between the structure and the soil

```bash
$ candejar interfaces culvert.cid --friction 0.3 --tensile 10 -o interfaced.cid
57 interface elements, 25 new interface material(s), 32 reused
  written to interfaced.cid
```

Or select the beams in the viewer and the action appears. One element per shared
node — not two. Nodes where the two beams are collinear are reported by number
rather than silently given a horizontal normal.

Run against a real production model with its interfaces stripped out, this
reproduces all 57 the engineer placed by hand, at the same locations, with
angles agreeing to within 0.04°. That comparison is a test.

### Other commands

| | |
|---|---|
| `candejar fmt FILE` | verify the file round-trips byte-for-byte |
| `candejar types [FILE]` | list the line types candejar understands, and what a file uses that it doesn't |

## The format, in one line

Every command line in a `.cid` file has exactly one shape:

```python
f"{command_name:>25}!!" + fixed_column_record
```

The command name is right-justified in 25 characters; the data record always begins at
column 28. Verified against the CANDE-2025 User Manual and every command line of two real
files of very different shape. That single rule is why a declarative field spec drives both
the reader and the writer, instead of scattered column constants and duplicated regexes.

```python
from candejar.model import Problem
from candejar.validate import run_rules

problem = Problem.read("culvert.cid")
print(problem.title, problem.level, len(problem.elements))

for finding in run_rules(problem):
    print(finding.severity.value, finding.message)
```

Two properties make it safe to ship a codec that covers only part of a large format:

- **Unknown line types round-trip verbatim.** Fidelity never depends on coverage. Both test
  fixtures still contain line types with no spec, and both come back byte-identical.
- **Writing a field replaces only that field's columns.** Editing a material number in a
  1,288-element model changes exactly two bytes of a 163 KB file. A write cannot disturb a
  neighbouring field, including fields this version has never seen.

## Layout

```
src/candejar/
├── io/          fixed-column codec — reader and writer from one field spec
├── model/       typed domain: nodes, elements, materials, boundaries, pipe groups
├── validate/    21 rules that run before CANDE does
├── ops/         structural edits: interface insertion, renumbering, control sync
├── cli.py       check · show · fmt · diff · types · serve
├── diff.py      semantic comparison
├── web.py       local viewer server
└── static/      the viewer
tests/fixtures/  real .cid files, scrubbed — the corpus correctness is defined by
docs/            the proposal, and the verified format notes
legacy/          the previous Tkinter editor, kept runnable during the rewrite
```

Mesh generation, solver integration, parametric studies and the full application will live
in the separate `candejar-pro` distribution. Both are proprietary; the split exists because
`candejar` is compiled to WebAssembly and shipped to the browser for the public validator,
and anything shipped there can be extracted from it. See
[§4.6 of the proposal](docs/REDESIGN-PROPOSAL.md).

## Development

```bash
pip install -e ".[dev]"
pytest          # 118 tests
ruff check .
mypy
```

## The previous editor

The Tkinter tool this replaces still runs:

```bash
cd legacy && python main.py
```

It is not maintained. Its known defects are catalogued in
[§1 of the proposal](docs/REDESIGN-PROPOSAL.md) — the most consequential being that it
creates every interface element twice, duplicates interface material definitions on save,
drops the `D-2.Interface` tensile field, cannot see link elements, and writes `NPT` as a
node count when CANDE wants the highest node number.

## License

**Proprietary — all rights reserved.** See [LICENSE](LICENSE).

Versions up to commit `052c005` were published under the MIT Licence; that grant
stands for anyone who already has them. Everything from the following commit
onward is proprietary.
