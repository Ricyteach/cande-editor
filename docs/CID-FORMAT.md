# CANDE `.cid` input format — verified notes

**Sources**
- ***CANDE-2025 Culvert Analysis and Design — User Manual and Guideline***, Michael G.
  Katona, April 2025, 338 pp. **This is the authority** — it states it "supersedes all
  previous user manuals."
- *CANDE-2013 User Manual*, §5 (pages 5-151 … 5-175 read directly) — used for the Level 3
  column tables, which the 2025 manual confirms unchanged.
- *CANDE-2024 / 2025 Solution Methods and Formulations* (present; input instructions not
  in them).
- Two real files, structurally very different, both from the `CID Files` corpus:
  - `NDS-45 18in cover … SW100.cid` — Level 3, 2,433 lines, 1,288 elements, 70 boundary
    conditions, 24 materials, 9 pipe groups.
  - `ADAMS FORK Level2-ANALYS-WSD-TREN-Pipe-PLASTIC-SMOOTH.cid` — Level 2, 22 lines.

Everything below marked **verified** was confirmed against both a manual and a real file.
Anything else is flagged.

---

## 0. The finding that matters most

From the CANDE-2025 User Manual, page viii, first bullet:

> "The Graphical User Interface (GUI) used for the 'screen mode' input method of generating
> a CANDE input file **has not been fully updated for the new capabilities.** Therefore,
> when exercising a new capability, **it is required to enter the relevant data directly on
> the CANDE input-file ('batch mode')** by following the input instructions given in
> Chapter 5."

> "For clarity, the input instructions that relate to the new capabilities are written in
> **red ink** to remind the user that this input data must be entered via batch mode."

Everything added to CANDE since 2011 — Mohr/Coulomb, the modified Duncan/Selig unload
model, Continuous Load Scaling, composite links, full pavement benefits for load rating,
and the April-2025 thermoplastic design criteria — is **unreachable from the official GUI**.
The vendor's own answer is: hand-edit fixed-column text and watch for the red ink.

That is the case for this project, stated by the program's author.

---

## 1. The universal line rule — **verified**

Every command line in a `.cid` file has the identical shape:

```
{command_name:>25}!!{fixed_column_data_record}
```

The command name is **right-justified in 25 characters**, followed by `!!`. The
fixed-column data record therefore always begins at **absolute column 28**
(0-based index 27), with no exceptions.

Checked against all 2,432 command lines in the sample file: the `!!` terminator ended at
index 27 on **2,432 of 2,432** lines.

```
                      A-1!!ANALYS   3 0  9 NDS-45 18in cover w all short term E ASD…
                   C-3.L3!!    1  000   -243.98     56.81
                   C-4.L3!!    1  687   42    0    0    7    1    0
            D-2.Interface!!     9.080     0.300        10
|<------- 25 chars ------>|++|<-- data record, columns 01-nn ------------------
                           ^^ literal "!!"
```

This is the single most important fact for a codec: **one prefix rule plus a per-line
column table is the entire format.** The column tables in the manual are written relative
to the start of the data record, so `absolute_index = 27 + (manual_column - 1)`.

Other file-level facts, **verified**:

- Line endings are **CRLF** (2,433 CRLF, 0 bare LF in the sample).
- The file ends with a bare `STOP` line — no `!!` prefix, no padding.
- Part A/B repeats **once per pipe group**. The sample has `A-2.L3` nine times, each
  followed by its own `B-1`/`B-2`/`B-3` block. A parser must group these, not flatten them.

---

## 2. Line-type catalogue

From the manual's table of contents (§5). Line types the sample file actually exercises
are marked ✓ with their observed count.

| Part | Line | Purpose | In sample |
|---|---|---|---|
| A | `A-1` | Master control: execution mode, solution level, pipe-group count, title | ✓ 1 |
| A | `A-2.L3` | Pipe selection — one per pipe group | ✓ 9 |
| B | `B-1`…`B-7` + `B-2b/c/d`, `B-3b`, `B-4b` | Pipe-material data, per pipe type | ✓ 213 |
| C | `C-1`…`C-3` (Level 1) | Elasticity solution parameters, fill heights, LRFD factors | — |
| C | `C-1`…`C-4` (Level 2) | Canned mesh — separate families for **Pipe**, **Box**, **Arch** | — |
| C | `CX-1`…`CX-4` | **Extended Level 2** — patch nodes/elements/BCs of a canned mesh | — |
| C | `C-1.L3` | Prep word and title | ✓ 1 |
| C | `C-2.L3`, `C-2b.L3` | Key control variables | ✓ 1 + 1 |
| C | `C-3.L3` | Node input | ✓ 800 |
| C | `C-4.L3` | Element input | ✓ 1288 |
| C | `C-5.L3` | Boundary condition input | ✓ 70 |
| D | `D-1` | Material control — all models | ✓ 24 |
| D | `D-2.Isotropic` / `.Orthotropic` / `.Duncan` (+`D-3`,`D-4`) / `.Overburden` / Hardin (+`D-3`) / `.Interface` / `.Composite Link` | Per-model properties | ✓ 24 |
| E | `E-1` | Net LRFD load factor per load step | — (ASD file) |

**Seven pipe types**, not five: Aluminum, Concrete, Plastic, Steel, Basic, **CONRIB**
(rib-shaped / fibre-reinforced concrete), **CONTUBE** (concrete in FRP tubes).

`C-2b.L3` appears in the real file but is absent from the CANDE-2013 section list — it is a
**CANDE-2017 addition** for Continuous Load Scaling (see §5). Exactly why unparsed lines
must round-trip verbatim: a tool built on the 2013 manual would have silently not known
about it.

### Level 2 line names — **verified**

The Level 2 file confirms the prefix rule holds for a completely different file shape, and
gives the Level 1/2 naming: `A-2.L12` (Levels 1 and 2 share it, versus `A-2.L3`), then
`C-1.L2.Pipe`, `C-2.L2.Pipe`, `C-3.L2.Pipe`, `C-4.L2.Pipe` — with `.Box` and `.Arch`
variants for the other two canned families. `D-3.Duncan` and `D-4.Duncan` also appear.

```
                      A-1!!ANALYS   2 0  1ADAMS FORK 24 " SDR=17          -99    0    0    0
                  A-2.L12!!PLASTIC   1
              C-1.L2.Pipe!!TREN New Level 2 Pipe Mesh
              C-2.L2.Pipe!!     22.59         1      71.8       115
                      D-1!!    3    3       115USER                10
               D-2.Duncan!!    0       0.5    1
               D-3.Duncan!!         0        42      14.4       587      0.75      0.75
               D-4.Duncan!!        41      0.05         0
STOP
```

A whole Level 2 model is 22 lines. The equivalent Level 3 model is thousands.

---

## 2a. New capabilities since 2011 — **all batch-mode only**

| Capability | Added | Input lines |
|---|---|---|
| CONRIB pipe type (rib-shaped / fibre-reinforced concrete) | 2012 | `A-2`, `B-1`…`B-6` |
| CONTUBE pipe type (concrete in FRP tubes) | 2013 | `A-2`, `B-1`…`B-6` |
| **Link elements with death option** | 2013 | `C-4` |
| Deeply corrugated steel (AASHTO 12.8.9.5-1, 12.8.9.6-1) | 2013 | `B-*` Steel |
| Plastic variable profile properties around the periphery | 2013 | `B-3`, `B-3b` Plastic |
| **Mohr/Coulomb elastoplastic soil model** | 2015; non-associative 2017 | `D-1`, `D-2` |
| **Modified Duncan/Selig** — permanent deformation on unload | 2015; vetted 2017 | `D-2.Duncan` |
| **Continuous Load Scaling (CLS)** | 2017; 3D pavement 2022 | `C-2` `Iscale`, `C-2b`, `C-2c` |
| **Composite link element** | Dec 2022 | `C-4` codes 10, 11 |
| Full pavement benefit for load rating (AAMP-θ\*) | Jan 2022 | `C-2b` `Ipave3D`, `C-2c` |
| Updated thermoplastic design criteria — thrust-strain limit, new global buckling, mixed-term loading | **April 2025** | `B-*` Plastic |

Six of these eleven post-date the CANDE-2013 manual entirely. Any tool must reference the
2025 manual, even though the Level 3 column tables themselves turn out to be unchanged.

---

## 3. `C-4.L3` — element input — **verified**

Manual §5.5.6.4. Columns are relative to the data record.

| Cols | Name | Fmt | Meaning |
|---|---|---|---|
| 01-01 | `LIMIT` | A1 | blank = more lines follow; `L` = last `C-4` line |
| 02-05 | `NE` | **I4** | element number — must start at 1 and ascend; gaps are auto-generated |
| 06-10 | `IX(1)` | I5 | node I — required, nonzero for every element type |
| 11-15 | `IX(2)` | I5 | node J — required, nonzero for every element type |
| 16-20 | `IX(3)` | I5 | node K — 0 for beams; for interface/link, a node shared with nothing else, and **must be greater than `IX(1)` and `IX(2)`** |
| 21-25 | `IX(4)` | I5 | node L — quadrilaterals only, else 0 |
| 26-30 | `IX(5)` | I5 | material / group number (see below) |
| 31-35 | `IX(6)` | I5 | **birth** load step — the step at which the element enters the system |
| 36-40 | `IX(7)` | I5 | element-class code |

Decoding a real line confirms it exactly:

```
                   C-4.L3!!    1  687   42    0    0    7    1    0
                           LIMIT=' ' NE='   1' I='  687' J='   42' K='    0'
                           L='    0' MAT='    7' STEP='    1' CODE='    0'
```

### `IX(7)` element-class codes

| Code | Element |
|---|---|
| 0 | continuum or beam-column — discriminated by the count of nonzero `IX(1..4)` |
| 1 | interface |
| 8 | **link, fixed connection** ("welds" two beam nodes) |
| 9 | **link, pinned connection** |
| 10, 11 | composite link |

Element type is therefore a function of **both** the nonzero-node count and `IX(7)` — you
cannot infer it from node count alone.

### `IX(5)` material number — separate namespaces

| Element type | `IX(5)` means | Range |
|---|---|---|
| Quadrilateral / triangle | soil material ID → defined in Part D | 1–100 |
| Beam-column | **pipe group number** → defined in Parts A and B | 1–30 |
| Interface | interface property number → defined in Part D | 1–99 |
| Link (8, 9) | unused | any |

Soil materials and interface materials are **independent ID sequences** that coexist in the
same `D-1` block, disambiguated by model type. The sample file bears this out:

```
D-1 model 1 (Isotropic):  1 material,  id 1
D-1 model 3 (Duncan):     4 materials, ids 2..5
D-1 model 6 (Interface): 19 materials, ids 1..19     <-- ids restart
```

The manual also notes that **interfaces on a curved surface need a separate material number
per element**, because the interface angle differs at each one. That is why a real model has
19 interface materials for one structure.

---

## 4. `C-3.L3` — node input — **verified**

| Cols | Name | Fmt | Meaning |
|---|---|---|---|
| 01-01 | `LIMIT` | A1 | blank / `L` for last node line |
| 02-05 | `NNP` | **I4** | node number, 1…`NPT` |
| 06-08 | `KRELAD` | I3 | 0 = plain coords; 1/2/3 = take x, y, or both from a previously defined node |
| … | `MODEG`, `LGTYPE`, `XCOORD`, `YCOORD` | | generation controls and coordinates |

```
                   C-3.L3!!    1  000   -243.98     56.81
```

Two features worth exploiting in a generator:

- **Nodes may be defined in any order**, forward or backward.
- Any node referenced by `C-4` but never defined on a `C-3` line gets its coordinates
  **automatically interpolated by Laplace generation**. A mesh generator can emit only the
  boundary nodes and let CANDE fill the interior.

---

## 5. `C-2.L3` — key control variables — **verified against CANDE-2025**

| Cols | Name | Meaning | Sample |
|---|---|---|---|
| 01-05 | `NINC` | number of load steps | 10 |
| 06-10 | `MGENPR` | mesh generation / print control | 3 |
| 11-15 | `NPUTCK` | input check control | 0 |
| 16-20 | `IPLOT` | plot control | 3 |
| 21-25 | `IWRT` | response print: 0 minimal · 1 standard · 2 +Duncan trace · 3 +interface trace · **4 +Mohr/Coulomb trace** | 1 |
| 26-30 | `NPT` | **highest node number used** — *not* the node count | 800 |
| 31-35 | `NELEM` | element count — **must match exactly** | 1288 |
| 36-40 | `NBPTC` | boundary-condition count — **upper bound**, may exceed actual | 70 |
| 41-45 | `NSMAT` | soil material count — **GUI-only hint, ignored in batch input** | 9 |
| 46-50 | `NXMAT` | interface material count — **GUI-only hint** | 25 |
| 51-55 | `MINBW` | bandwidth minimiser: 0 none · 1 minimise · 2 minimise and print | 1 |
| 56-60 | `Iscale` | **Continuous Load Scaling**: 0 off · 1 CLS-EBM · 2 CLS-AAM-θ\* | 2 |

Three of these are **not counts**, which matters for a writer:

- **`NPT` is the highest node *number*, not how many nodes there are.** CANDE explicitly
  permits skipped node numbers. Writing a count here is wrong whenever the numbering has
  gaps.
- **`NBPTC` may be larger than the actual count** — the manual recommends "some
  sufficiently large number, say 200."
- **`NSMAT` and `NXMAT` are used only by the GUI** and "may be ignored for batch input."
  That explains the sample file's 9 and 25 against 5 and 19 actually defined.

*(Manual erratum: the `NXMAT` description says interface materials are "identified in line
C-4 with variable `IX(7)`". `IX(7)` is the element-class code; the interface material number
is `IX(5)`. Don't implement from that sentence.)*

`MINBW` confirms that **bandwidth is a first-class CANDE concern**, which is an argument for
doing node renumbering at export time.

### `C-2b.L3` and `C-2c.L3` — Continuous Load Scaling

Set `Iscale` = 1 or 2 and `C-2b.L3` becomes required; add pavement 3D benefits
(`Ipave3D` = 1) and `C-2c.L3` is required too. `C-2b` carries: starting and ending live-load
step (`LSstart`, `LSstop`, cols 01-05 / 06-10), wheel footprint length and width, axle
spacing, soil-surface reference node, the 3DSE distribution widths `Wmin` and `Wcritical`,
the pipe-group range for 3DSE, and `Ipave3D`.

The sample file's `C-2b.L3` record is `    9   10` — live load applied across steps 9→10,
everything else defaulted — and its `Iscale` is 2, so it is already using **CLS-AAM-θ\***.
This is one of the capabilities the CANDE GUI cannot author.

Note the modelling consequence: under CLS the `C-5` boundary conditions carry the **actual
service wheel load**, not an RSL-reduced load. Whether a file uses CLS therefore changes how
its live loads must be *interpreted* — a preprocessor that shows live loads without reading
`Iscale` will mislabel them.

---

## 6. `D-1` — material control — **verified**

| Cols | Name | Fmt | Meaning |
|---|---|---|---|
| 01-01 | `LIMIT` | A1 | blank / `L` on the last `D-1` |
| 02-05 | material ID | I4 | within its own namespace (soil or interface) |
| 06-10 | model type | I5 | 1 Isotropic · 2 Orthotropic · 3 Duncan/Duncan-Selig · 4 Overburden · 5 Extended Hardin · 6 Interface · 7 Composite Link |
| 11-20 | density | I10/F10 | |
| 21-40 | `MATNAM` + name | A20 | canned soil name (e.g. `SW100`) plus free text |

```
                      D-1!!    1    1       000 Insitu
                      D-1!!    2    3       120SW100  Crushed Rock
                      D-1!!L  19    6         0           Inter #19
```

## 7. `D-2.Interface` — **verified, and larger than the current tool assumes**

The manual section is titled *"D-2 — Interface Element — **Angle, Friction, Tensile Force
and Gap Distance**"* — four parameters. The real file carries a third populated field:

```
            D-2.Interface!!     9.080     0.300        10
                              angle      friction    (tensile force / gap)
```

The current editor parses only angle and friction, and regenerates the line with only
those two fields.

---

## 8. Consequences for the rewrite

Confirmed by this exercise:

1. **The declarative codec is the right call, and cheaper than estimated.** One prefix rule
   plus a column table per line type covers the entire format. No per-line parsing code.
2. **`RawLine` pass-through is mandatory, not just prudent.** `C-2b.L3` and the 12th `C-2`
   field are already outside the section list; version drift is real.
3. **CRLF must be preserved byte-for-byte** for a round-trip test to mean anything. Reading
   with Python text mode and writing back on a non-Windows host silently rewrites every
   line ending.
4. **`NE` and `NNP` are I4 fields** — node and element numbers appear to cap at 9,999 in the
   definition columns, while node *references* in `IX(1..4)` are I5. Worth confirming with a
   large model before relying on it; either way it is a validation rule the current tool
   does not have.

Defects in the current editor that this investigation newly confirms:

- **Link elements are invisible.** `ELEMENT_CLASS_DICT` maps only `{0: None, 1: Interface}`.
  An `IX(7)` of 8 or 9 (link) has two nonzero nodes and would be parsed as a beam
  (`Element1D`) — and then be eligible for interface insertion, which is meaningless for a
  link.
- **Interface material definitions are duplicated on save.** `_generate_interface_material_lines()`
  renumbers every interface element from material ID 1 and emits a fresh `D-1`/`D-2` pair
  for each unique (friction, angle), then `save_file()` **inserts** those after the existing
  `D-1` block without removing the originals. On this sample file — which already has 19
  interface materials — a save would append a second, conflicting set numbered 1…19.
- **The tensile-force / gap field is dropped** from every regenerated `D-2.Interface` line.
- **Only `IX(6)` birth step is modelled.** Link elements have a *death* step (CANDE-2013
  added element removal, for temporary supports, excavation, or void creation); nothing in
  the current data model can represent it.
- **`NPT` is written as a node count.** `_update_c2_line()` sets the `NPT` field to
  `len(self.nodes)`. `NPT` is the *highest node number used*, and CANDE explicitly permits
  gaps in node numbering. Any model with skipped numbers gets an `NPT` that is too small.
  The same routine treats `NSMAT`/`NXMAT` as values to grow monotonically, when the manual
  says they are GUI-only hints ignored on batch input.
- **`Iscale` is invisible.** A file using Continuous Load Scaling carries unreduced service
  wheel loads on its `C-5` lines. Nothing in the current tool reads `C-2`, so it cannot tell
  a CLS model from an RSL one — and the two mean different things by the same numbers.

## 9. Beyond the input file

Two findings that change the later phases:

- **CANDE has a documented NASTRAN import path** (User Manual §7.2): `GRID`, `CBAR`,
  `CTRIA3`, `CQUAD4`, `CGAP`, `SPC`, `FORCE`. A mesh generator could target NASTRAN and let
  CANDE import it. Writing `.cid` Level 3 directly is still preferable — full control, no
  second format to satisfy — but this is a useful fallback and a compatibility target.
- **Output is already partly XML.** Runs emit `_MeshGeom.xml`, `_MeshResults.xml`, and
  `_BeamResults.xml` alongside `.out`, `PLOT1.DAT`, `PLOT2.dat`, and NCHRP Process 12-50
  results — all documented in User Manual §7.1. Post-processing is therefore substantially
  cheaper than assumed: no need to scrape the text report.
- **CANDE-2024 ships `CANDE_DLL.dll`.** If the solver is callable in-process rather than only
  as an executable, batch and parametric runs get much faster and more controllable.
