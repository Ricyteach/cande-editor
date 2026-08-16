# Strata — a proposal to rebuild this into a real CANDE preprocessor

**Status:** proposal, not yet approved
**Author:** drafted for Rick Teachey
**Scope:** replaces `cande-editor` v2.0 in its entirety

> **Update — format verified against CANDE-2025.** The CANDE-2025 User Manual (April 2025,
> which "supersedes all previous user manuals") and two structurally different real files
> have been read. The format is pinned in [`docs/CID-FORMAT.md`](CID-FORMAT.md); §4.2 below
> now carries the verified column table, and §1.4 the extra defects. Nothing in the
> architecture changed — the codec turned out *simpler* than assumed. But §0 changed the
> case for the project entirely.

---

## 0. The strongest argument is in CANDE's own manual

CANDE-2025 User Manual, page viii, first bullet:

> "The Graphical User Interface (GUI) used for the 'screen mode' input method of generating
> a CANDE input file **has not been fully updated for the new capabilities.** Therefore,
> when exercising a new capability, **it is required to enter the relevant data directly on
> the CANDE input-file ('batch mode')** by following the input instructions given in
> Chapter 5."
>
> "For clarity, the input instructions that relate to the new capabilities are written in
> **red ink** to remind the user that this input data must be entered via batch mode."

Eleven capabilities have been added to CANDE since 2011. **Every one of them is
unreachable from the official GUI.** Among them:

- Mohr/Coulomb elastoplastic soil model
- Modified Duncan/Selig with permanent deformation on unload
- Continuous Load Scaling — the modern replacement for reduced surface loads
- Composite link elements; link elements with a death step
- Full pavement benefit for load rating (AAMP-θ\*)
- The April-2025 thermoplastic design criteria (thrust-strain limit, new global buckling)

The vendor's answer is to hand-edit fixed-column text and watch for red ink in a 338-page
PDF. Your own files already depend on this: the sample Level 3 model runs `Iscale = 2`,
i.e. CLS-AAM-θ\*, which no GUI can author or even display.

This is no longer a proposal to build a nicer editor. **The official preprocessor stopped
covering the program a decade ago, and the gap widens with each release.** A tool that
simply parses the whole current format — before any mesh generation, before any of the
ambitious parts — closes a gap that nothing else closes.

*"Strata" is a suggested working name — CANDE's central idea is incremental
construction in layers, which is also how the software should be built. Rename
freely.*

---

## 1. Where the current tool stands

`cande-editor` v2.0 does one useful thing well enough to be worth keeping the
*idea* of: it draws a Level 3 mesh, lets you rubber-band select elements, and
bulk-assigns material and step numbers. That is a genuinely tedious job in the
stock CANDE GUI, and this tool removes real pain.

Everything below is about why it cannot grow past that.

### 1.1 The architecture is a text patcher, not a model

`CandeModel` holds `file_content: List[str]`, and every entity carries the line
it came from:

```python
# models/node.py, models/element.py
line_number: int
line_content: str
```

Every edit is a fixed-column string splice:

```python
# utils/constants.py:6-12
MATERIAL_START_POS = 52
MATERIAL_END_POS   = 57
STEP_START_POS     = 57
STEP_END_POS       = 62
```

```python
# models/cande_model.py:727-730
prefix = line[:MATERIAL_START_POS] if len(line) > MATERIAL_START_POS else line
suffix = line[MATERIAL_END_POS:]   if len(line) > MATERIAL_END_POS   else ""
line = prefix + material_str + suffix
```

This works for the two operations it was written for and fails for everything
else. `save_file()` is 200 lines of "find the last `C-4` line, swap `!!L` back to
`!! `, insert here, swap it back" heuristics
(`models/cande_model.py:242-446`). Adding a node means guessing an insertion
point. Renumbering is unthinkable. There are two independent write paths —
`update_elements()` mutates `self.file_content` in place, `save_file()` rebuilds
from `self.file_content` — and nothing keeps them consistent.

### 1.2 It understands about four line types out of roughly forty

The parser recognises `C-3` (nodes), `C-4` (elements), and `D-1`/`D-2.Interface`
(interface materials). Everything else in a `.cid` file is opaque text that gets
copied through:

| Group | What it holds | Understood today |
|---|---|---|
| A-1, A-2 | Master control: analysis vs design, solution level, load steps, LRFD vs service | no |
| B-1 … B-4 | Pipe-type data: Basic / Aluminum / Steel / Plastic / Concrete section and material properties | no |
| C-1, C-2 | Level 3 control and entity counts | counts only, by column arithmetic |
| C-3, C-4 | Nodes, elements | yes |
| C-5 | Boundary conditions | **no** |
| D-1, D-2.* | Soil materials: Isotropic, Orthotropic, Duncan / Duncan-Selig, Overburden, Extended Hardin, Interface, Composite Link | interface only |
| D-3, D-4, E-* | Model-specific properties, load factors, step data | no |

*(Exact catalogue to be pinned against the CANDE-2022 User Manual; the site was
unreachable from this environment. The point stands regardless of the exact
count.)*

A tool that cannot read boundary conditions cannot tell you your model is
under-restrained. A tool that cannot read `D-1` soil models cannot tell you that
element 412 references material 7 that you deleted. A tool that cannot read `A-1`
does not know how many load steps the run actually has.

### 1.3 Concrete defects that follow from the design

These are not nitpicks; each one is the architecture showing through.

**Duplicate interface elements.** `create_interfaces()` builds the same interface
element twice per shared node — same I/J/K node triple, two element IDs, and
`interface_count` only counts one of them (`models/cande_model.py:885-912`).
Every interface run silently doubles your interface element count.

```python
interface_element_id = max_element_id + 1
max_element_id += 1
self.elements[interface_element_id] = InterfaceElement(nodes=[i_node_id, j_node_id, k_node_id], ...)

# Create interface element                     <-- and again, identical
interface_element_id = max_element_id + 1
max_element_id += 1
self.elements[interface_element_id] = InterfaceElement(nodes=[i_node_id, j_node_id, k_node_id], ...)
```

**Any nonconforming line kills the whole load.** `BaseElement.__post_init__`
raises on `material <= 0` or `step <= 0`; `InterfaceElement` raises unless it has
exactly three nodes. Those exceptions propagate to `load_file()`'s blanket
`except Exception`, which returns `False`, and the user sees *"Failed to open
file."* One odd line, no model, no diagnostic.

**Silent geometric fallbacks.** `_calculate_beam_angles()` only produces an angle
for nodes joining exactly two beams. `create_interfaces()` then does
`node_angles.get(node_id, 0.0)` — a node it could not solve gets a horizontal
normal with no warning.

**Save depends on the `L` continuation flag being where it's expected.** Node and
element insertion locate the group end by matching `C-3.L3!!L` / `C-4.L3!!L`. If
a file marks its groups differently, insertion silently no-ops.

**The test suite cannot run.** The only test file imports
`utils.base_model`, `utils.identifiable`, and `utils.entity_reference_container`
— none of which exist. It is 1,100 lines of design notes with a `.py` extension.
There is no test of the parser, the writer, or the interface geometry.

**Layering has already broken down.** The controller hands the model to the view
(`self.canvas_view.model = self.model`, `controllers/cande_controller.py`), and
the 737-line controller mixes Tk event handling with domain logic. The
`element_type_filter` is variously `None`, a string, or a list, and three
different methods each re-implement the same "is it a str or a list" branch.

**Packaging is broken.** `[tool.setuptools.py-modules] modules = [...]` is not a
real key. Top-level packages named `models`, `views`, `utils`, and `controllers`
will collide with anything else installed. `requires-python = ">=3.12"` while the
README says 3.6.

### 1.4 Further defects, confirmed against the real format

Reading the manual and a real file surfaced four more, all of them consequences of
the same root cause. Detail and evidence in [`docs/CID-FORMAT.md`](CID-FORMAT.md) §8.

- **Interface material definitions are duplicated on save.** The save path
  renumbers every interface element from material ID 1 and emits a fresh
  `D-1`/`D-2` pair per unique (friction, angle), then *inserts* them after the
  existing `D-1` block without removing the originals. The sample file already has
  19 interface materials; saving it would append a second, conflicting set
  numbered 1…19.
- **Link elements are invisible.** `ELEMENT_CLASS_DICT` knows only `{0: None,
  1: Interface}`. CANDE-2013 added link elements with `IX(7)` codes 8, 9, 10 and
  11. A link has two nonzero nodes, so it is parsed as a beam — and then becomes
  eligible for interface insertion, which is meaningless for a link.
- **The tensile-force / gap field is dropped.** `D-2.Interface` carries angle,
  friction, tensile force and gap distance. The parser reads two of the four and
  the writer emits two. The real file has the third field populated.
- **Element death cannot be represented.** `IX(6)` is the *birth* load step. Link
  elements also have a death step — that is how CANDE models removing temporary
  supports, excavation, and void creation. Nothing in the data model can hold it.

### 1.5 The instinct in the newest commits is right

The most recent work — `utils/copyable.py`'s `ImmutableCopyable.with_changes()`,
and the `EntityReferenceContainer` sketch — is reaching for exactly the right
thing: entities that reference each other by identity, immutable values, copy-on-
change. That instinct is correct and it is what this proposal formalises. It just
cannot be retrofitted onto a `List[str]` with line numbers stapled to it.

---

## 2. The one mistake, stated plainly

**The file is treated as the model.**

Every limitation above is a corollary. Make the model the model, and the `.cid`
file a serialisation of it, and the whole class of problems disappears: you can
renumber, insert, delete, validate, undo, diff, generate, and round-trip, because
none of those operations are string surgery any more.

---

## 3. What a CANDE preprocessor should do that none does today

This is the part that makes it worth rebuilding rather than repairing. Ranked by
how much time each saves a working culvert engineer.

### 3.1 Parametric geometry and a real mesh generator

Today, a Level 3 mesh comes from CANDE's canned Level 2 templates, a spreadsheet,
AutoCAD, or hand entry. Level 2 covers the standard shapes and nothing else; the
moment you have a real site — a skewed trench, a sloping ground surface, an
adjacent footing, twin barrels, a headwall — you are on your own.

Describe the *installation*, not the mesh:

```yaml
structure:
  type: box
  span: 12 ft
  rise: 8 ft
  haunch: 12 in
  wall_thickness: 10 in
installation:
  cover: 3 ft
  bedding: {material: SW95, thickness: 6 in}
  trench: {width: span + 4 ft, side_slope: 1:1, native: CL90}
  backfill: {material: SW90, lift: 12 in}
  water_table: -4 ft
```

…and get a graded quad mesh, structure beam elements, interface elements along
the soil–structure boundary, boundary conditions, and load steps derived from the
lift thickness. Structured/mapped meshing for the standard layouts (CANDE wants
well-shaped quads), with an unstructured fallback plus quad recombination for the
awkward ones.

This alone is the difference between "a mesh editor" and "a preprocessor."

### 3.2 A validation engine that runs before CANDE does

CANDE reports input problems as a crash or, worse, as a plausible-looking wrong
answer. A preprocessor should carry a rule set that runs on every save:

- inverted or negative-Jacobian elements, aspect ratio and skew limits
- orphan nodes, duplicate nodes at coincident coordinates, unattached beams
- elements referencing undefined materials; materials defined but unused
- interface elements whose K node geometry doesn't define the intended plane
- boundary conditions insufficient to restrain rigid-body translation/rotation
- load steps non-contiguous, or elements assigned to a step past `A-1`'s count
- counts on `C-2` disagreeing with actual entity counts
- soil material parameters outside the physically sensible range for the model
- LRFD load factor combinations that don't match the stated design method

Each finding names the offending entity, is clickable to zoom to it, has a
severity, and — where it can be — is auto-fixable.

### 3.3 Semantic diff for `.cid` files

```
$ strata diff before.cid after.cid
  materials
    3  Duncan SW95 → SW90            (E_i 1450 → 1100 psi)
  elements
    +18 interface elements on the invert
    142 elements moved from step 4 → step 5
  boundary conditions
    node 891 released in Y
```

Any engineer who has ever checked someone else's culvert model — or their own
from six months ago — knows why this matters. A line diff of fixed-column text
tells you nothing.

### 3.4 Everything scriptable, with the GUI as one client

The Python API is the product; the GUI drives the same API the scripts do. Then a
fill-height study is ten lines:

```python
from strata import Project

base = Project.load("box_12x8.strata")
for cover in range(2, 41, 2):
    m = base.with_cover(cover * ft)
    m.export_cid(f"runs/cover_{cover:02d}.cid")
```

Parametric studies, batch load rating, design sweeps, and regression checks
against a reference model all become ordinary programming instead of hours of
GUI clicking.

### 3.5 Close the loop: run CANDE and bring results back

Launch the solver, parse the output, and map results back onto the *same* mesh
objects: deformed shape, soil stress contours, thrust/moment/shear along the
structure, per-step, plus LRFD demand/capacity ratios per element. A preprocessor
that can also show you the answer stops being a preprocessor and starts being the
place you work.

### 3.6 A project format built for version control

The canonical file is a readable, diffable YAML/TOML document under git. `.cid` is
an *export target*, regenerated on demand and stamped with the model hash, the
tool version, and the parameters that produced it — so a reviewer can reproduce
it exactly.

### 3.7 Standard-installation templates

"AASHTO Type 2 standard installation," "Class B bedding," "positive projecting
embankment," the Duncan and Duncan/Selig canned soil library (SW/ML/CL at 85, 90,
95% compaction) as named, parameterised recipes rather than numbers you look up
and retype every time.

### 3.8 Real editing ergonomics

Undo/redo on every operation. Named selection sets that persist across sessions.
Selection by geometric predicate ("all elements above the springline within the
trench"). Mirror, sweep, split, and refine as model operations rather than
manual node arithmetic.

---

## 4. Architecture

### 4.1 Layers

```
┌──────────────────────────────────────────────────────────────┐
│  strata.ui        PySide6 desktop app — renders, dispatches   │
│  strata.cli       typer CLI: fmt, check, mesh, diff, run      │
│                   (both are thin clients; neither owns state) │
├──────────────────────────────────────────────────────────────┤
│  strata.studies   parametric sweeps, batch runs               │
│  strata.solve     CANDE runner, output parsing                │
│  strata.validate  rule engine, findings, auto-fixes           │
│  strata.mesh      generators, quality metrics, renumbering    │
│  strata.ops       commands: assign, insert interfaces, split… │
├──────────────────────────────────────────────────────────────┤
│  strata.model     typed domain: Project, Structure, Mesh,     │
│                   Materials, LoadSteps, BoundaryConditions    │
├──────────────────────────────────────────────────────────────┤
│  strata.io        fixed-column codec — reader + writer        │
│                   driven by one declarative field spec        │
└──────────────────────────────────────────────────────────────┘
```

Nothing above `strata.model` touches a file. Nothing below `strata.ops` knows a
UI exists.

### 4.2 The five load-bearing decisions

**(a) One declarative field spec drives both reader and writer.**
Rather than constants scattered across modules and regexes duplicated between
parse and save, each line type is a table:

```python
# Every line is exactly: f"{name:>25}!!" + fixed-column record.
# Columns below are 1-based within the record, per the User Manual.
LINE_TYPES["C-4.L3"] = LineSpec(
    name="C-4.L3",
    fields=[
        Field("limit",    cols=(1, 1),   kind=A1),   # blank, or "L" on the last line
        Field("element",  cols=(2, 5),   kind=I4),
        Field("i",        cols=(6, 10),  kind=I5),
        Field("j",        cols=(11, 15), kind=I5),
        Field("k",        cols=(16, 20), kind=I5),
        Field("l",        cols=(21, 25), kind=I5),
        Field("material", cols=(26, 30), kind=I5),
        Field("birth",    cols=(31, 35), kind=I5),
        Field("code",     cols=(36, 40), kind=I5, default=0),
    ],
)
```

**This is now verified, not illustrative.** Every command line in a `.cid` file is
`{command_name:>25}!!` followed by a fixed-column record starting at absolute
column 28 — confirmed on 2,432 of 2,432 lines in a real file, with the manual's
column tables decoding it exactly. See [`docs/CID-FORMAT.md`](CID-FORMAT.md).

The reader and the writer are both generated from this. Adding the remaining line
types becomes data entry with a test each, not new code. The spec is versioned, so
CANDE-2007 / 2013 / 2024 differences are a table variant rather than a fork.

**(b) Unknown lines round-trip verbatim.**
Any line the codec doesn't yet understand becomes an ordered `RawLine` in the
model. The tool is therefore *never lossy*, even before it understands the whole
format. This is what makes an incremental rollout safe: v0.1 can open your real
files on day one and give them back byte-identical.

The acceptance test is blunt: for every file in the corpus, `read → write` must
be byte-identical.

**(c) Entity identity is internal; file numbers are assigned at export.**
Nodes and elements carry stable internal handles. Node and element *numbers* are
generated on export, with bandwidth-optimal renumbering (reverse Cuthill-McKee)
as a free side benefit. Deleting node 14 stops being a catastrophe.

This is the correct form of the `EntityReferenceContainer` idea already sketched
in the repo.

**(d) Immutable model + command log.**
Every edit is a command object with an inverse. That yields undo/redo, an audit
trail of how a model was built, and cheap change detection for the UI — from one
mechanism. `ImmutableCopyable.with_changes()` generalised and made the spine of
the system.

**(e) Headless core, thin clients.**
The GUI holds no domain state. It renders a model and dispatches commands. That
is what makes the CLI, the scripting API, batch runs, and automated testing
possible at all — and it means a future web front end is a new client, not a
rewrite.

### 4.3 Technology

| Concern | Choice | Why |
|---|---|---|
| Language | Python 3.12+ | already the codebase; the ecosystem is right |
| Domain model | pydantic v2 | already a dependency; validation and (de)serialisation for free |
| Geometry | numpy + shapely | vectorised mesh math, robust polygon ops |
| Unstructured meshing | gmsh (Python API) | fallback for non-standard geometry, with quad recombination |
| UI | **Web, client-side** — Pyodide (core compiled to WASM) + WebGL rendering | see below |
| CLI | typer + rich | the native client; covers solver runs, batch sweeps, job folders |
| Tests | pytest + hypothesis | property-based round-trip tests on the codec, golden-file corpus |

### 4.4 Decision: web, not desktop — and no Qt at all

**Decided.** The original recommendation (PySide6/Qt) assumed a single user on
Windows next to the solver. The intent to publish the tool — potentially on the
KBJW site, as a lead source — changes the audience, and once the public client is
web there is no case for maintaining a second GUI for internal use.

What genuinely needs to be native is not a GUI: running CANDE, batch and
parametric sweeps, and working against job folders. That is **CLI** work. The
client matrix is therefore **web + CLI**, and Qt drops out — one fewer UI than
originally proposed.

**The core runs client-side.** The Python core is compiled to WASM via Pyodide and
shipped as a **static site**. Nothing is uploaded. That matters more than it
sounds:

- **Confidentiality.** No engineer uploads a client's culvert model to a
  consultant's website. "Runs entirely in your browser — your file never leaves
  your machine" is the headline feature, not a caveat, and it is the difference
  between a tool people try and a tool people adopt.
- **No data custody, therefore no liability** for holding third-party models.
- **Static hosting** — no backend, no server cost, no ops, no attack surface.
- **One codebase.** The same core runs in the browser, in the CLI, and in batch
  scripts. A TypeScript port would mean two implementations drifting apart.

Cost is a ~10 MB first load, cached thereafter — acceptable for a tool opened
deliberately. Rendering uses **WebGL**, not Canvas2D: the largest files in the
corpus are ~900 KB, well past what Canvas2D handles comfortably and well within
WebGL's range.

This also partitions the feature set cleanly. Anything needing gmsh or the CANDE
solver is desktop/CLI territory; parsing, validation, visualisation and reporting
run anywhere. If interactive editing at very large mesh sizes ever demands native
performance, Qt remains available off the same headless core — but it should not
be built speculatively.

### 4.5 The public tool

Not the full preprocessor. **A validator and inspector**: drop in a `.cid`, get the
mesh drawn, the model explained in plain language, and a ranked list of what is
wrong with it.

That is Phase 1 plus Phase 2 output, so it is nearly free once the codec exists —
and it is the thing nobody has. It needs no solver, which keeps CANDE licensing
and Windows hosting out of scope entirely, and it draws a clean commercial line:
**the free tool tells you what is in your model; running it, designing it, and
sealing it is the engineering service.** A call to action sits in context above the
findings rather than as an advertisement.

Worth more than the button: a **client-side-generated PDF report** on KBJW
letterhead, which ends up saved in the client's own project folder.

Two things to settle before it goes live, both outside the code:

- "Available in all 50 states and Canada" is a **licensure claim** — the wording
  should go past whoever handles the firm's COAs and reciprocity.
- The tool needs a **one-line scope disclaimer**: it checks file and model
  consistency, not design adequacy. That keeps its output from being read as an
  engineering review once strangers are using it.

---

## 5. Roadmap

Six phases. Each one ships something usable on its own; none of them requires the
next one to justify itself.

### Phase 0 — Foundations *(~1 week)*
`src/` layout, single top-level package, working `pyproject.toml`, pytest + ruff +
mypy in CI, `.cid` test corpus assembled. The current `tests/utils/…` file moves
to `docs/notes/` where it belongs as the design sketch it is.
**You get:** a repo that builds and tests.

### Phase 1 — Codec and model *(~3 weeks)*
`strata.io` + `strata.model`. All line types the corpus exercises, `RawLine`
pass-through for the rest, byte-identical round-trip test, and a CLI:
`strata check` (structural validation), `strata fmt` (normalise a file),
`strata show` (human-readable summary of what a `.cid` actually contains).
**You get:** a library and CLI that already do something the stock tools don't —
tell you what's wrong with a `.cid` before you run it. No GUI needed.

### Phase 2 — Operations and validation *(~3 weeks)*
`strata.ops` and `strata.validate`. Assign material/step, insert interface
elements **correctly** (with the duplicate-creation bug gone and the angle
fallback made explicit), renumber, delete, mirror. Rule engine with severities
and auto-fixes. `strata diff`.
**You get:** batch editing and model checking from scripts; semantic diffs for QA.

### Phase 1.5 — Public validator *(~1.5 weeks)*
The codec and rule engine compiled to WASM behind a single static page: drop a
`.cid`, see the mesh, read a plain-language summary of the model, get a ranked list
of findings, download a branded PDF report. Nothing uploads. Deployable to the KBJW
site or a subdomain with no backend.
**You get:** a lead source running about six weeks in, while everything after it is
still being built — and a public artefact that demonstrates the tool works.

### Phase 3 — The full web application *(~5 weeks)*
The editor: mesh rendering coloured by material, step or soil model; selection
sets; undo/redo; a validation panel that zooms to findings; property editors for
soil and structural materials — including the models the CANDE GUI cannot reach.
Feature parity with today's tool, plus everything Phases 1–2 added.
**You get:** the tool you have now, but correct, faster, undoable, aware of the
whole file, and reachable from any machine without an install.

### Phase 4 — Mesh generation *(~6 weeks)*
`strata.mesh`. Parametric structure library (box, circular, arch, 2R/3R, ellipse,
custom polyline), installation geometry, automatic interface insertion, automatic
load-step assignment, mesh quality metrics and refinement. AASHTO standard
installation templates.
**You get:** the headline feature — model from parameters, not from node lists.

### Phase 5 — Closing the loop *(~4 weeks)*
`strata.solve` and `strata.studies`. Run CANDE, parse output, map results back
onto the mesh, contour and diagram plots, LRFD D/C ratios, parametric sweeps and
batch load rating.
**You get:** the whole workflow in one place.

Roughly five months of focused part-time work to Phase 5; genuinely useful output
at the end of Phase 1, about a month in.

---

## 6. Non-goals

- **Not a CANDE replacement.** The solver stays the solver. This is input,
  validation, and interpretation.
- **Not a general FE pre/post-processor.** Every design decision is allowed to
  assume buried culverts.
- **Not backwards compatible with the v2.0 internals.** The `.cid` files are the
  compatibility surface, and they round-trip losslessly. Nothing else carries
  over.

## 7. Risks and how they're handled

| Risk | Handling |
|---|---|
| The `.cid` format surface is large | `RawLine` pass-through means the tool is useful and lossless long before it's complete; line types get added by priority |
| No corpus of real files to test against | Needed early — see below |
| CANDE version differences (2007/2019/2022) | Codec spec is versioned data, not code |
| Mesh generation is the hardest part | It's Phase 4, behind four phases of value; structured meshing for standard cases covers most of the benefit before gmsh is needed |
| Scope drift into a general FE tool | The non-goals above are the fence |

## 8. What I need from you

Items 1 and 2 are **received and then some**. `OneDrive/CID Files/` holds the
**CANDE-2025 User Manual and program package** plus a corpus with genuinely good
spread — Level 2 and Level 3, box / arch / 2-radius / double-radius / pipe,
concrete / steel gauges / plastic, HS-20 / tandem / HL-93, factored and service,
quad and triangle meshes, with-and-without-interface pairs, and files from 1.3 KB
to 908 KB. That is enough to build the codec against. What remains:

1. **A `.cid` MIME workaround.** The connector refuses `.cid` (SharePoint reports
   `application/octet-stream`, which is not on its allow-list). Copying a file and
   renaming it `.cid.txt` works — two are staged in `OneDrive/_claude_cid_readable/`
   as proof. For the real corpus, **the repo is the better home**: a set of
   anonymised fixtures under version control next to the round-trip tests. Say the
   word and I'll delete the staging folder.
2. **A few gaps in the spread.** No aluminum, CONRIB, or CONTUBE model spotted yet;
   nothing obviously using link elements or the `CX-*` extended-Level-2 lines; and
   no examples CANDE *rejected* — those last ones pin down the validation rules
   better than any number of valid files.
3. **Two decisions** — the UI question is **settled: web + CLI, no Qt** (§4.4):
   - Level 3 only at first, or Level 1/2 in the model from the start? *(Leaning
     both: the Level 2 file is 22 lines, so the canned-mesh line types are cheap
     to support, and the public validator is more useful if it accepts anything.)*
   - Who owns the published page — does it live on the KBJW site proper, or a
     subdomain? That affects nothing technical, but it decides who signs off.
4. **Whether to start.** Phase 0 + Phase 1 is the smallest slice that proves the
   architecture. Phase 1.5 turns it into something public about a week and a half
   later.

## 9. Two findings that make the later phases cheaper

- **Output is already partly XML.** Runs emit `_MeshGeom.xml`, `_MeshResults.xml`
  and `_BeamResults.xml` alongside the text report, `PLOT1.DAT`, `PLOT2.dat` and
  NCHRP Process 12-50 results — all documented in User Manual §7.1. Phase 5 does
  not need to scrape the `.out` report.
- **CANDE-2024 ships `CANDE_DLL.dll`.** If the solver is callable in-process rather
  than only as an executable, batch runs and parametric sweeps get materially
  faster and more controllable. Worth a spike early in Phase 5.
- **CANDE can import NASTRAN** (`GRID`, `CBAR`, `CTRIA3`, `CQUAD4`, `CGAP`, `SPC`,
  `FORCE`; User Manual §7.2). Writing `.cid` Level 3 directly is still preferable,
  but this is a useful fallback and a compatibility target for Phase 4.
