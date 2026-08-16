# CANDE `.cid` input format — verified notes

**Sources**
- *CANDE-2013 Culvert Analysis and Design — User Manual and Guideline*, §5 "Detailed CANDE
  Input" (pages 5-151 … 5-175 read directly). Page footers in that range read
  "CANDE-2012 User Manual"; the file is the 2013 release.
- *CANDE-2024 Solution Methods and Formulations* (present; input instructions not in it).
- One real Level 3 file: `NDS-45 18in cover w all short term E ASD per testing SW100.cid`
  — 2,433 lines, 800 nodes, 1,288 elements, 70 boundary conditions, 24 materials,
  9 pipe groups.

Everything below marked **verified** was confirmed against both the manual and that file.
Anything else is flagged.

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

`C-2b.L3` appears in the real file but is not in the section list I read — a CANDE-2013
addition. This is exactly why unparsed lines must round-trip verbatim.

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

## 5. `C-2.L3` — key control variables — **verified**

| Cols | Name | Meaning | Sample |
|---|---|---|---|
| 01-05 | `NINC` | number of load steps | 10 |
| 06-10 | `MGENPR` | mesh generation / print control | 3 |
| 11-15 | `NPUTCK` | input check control | 0 |
| 16-20 | `IPLOT` | plot control | 3 |
| 21-25 | `IWRT` | write control | 1 |
| 26-30 | `NPT` | **number of nodes** | 800 ✓ = 800 `C-3` lines |
| 31-35 | `NELEM` | **number of elements** | 1288 ✓ = 1288 `C-4` lines |
| 36-40 | `NBPTC` | **number of boundary condition lines** | 70 ✓ = 70 `C-5` lines |
| 41-45 | `NSMAT` | number of soil materials | 9 |
| 46-50 | `NXMAT` | number of interface materials | 25 |
| 51-55 | `MINBW` | minimum bandwidth flag | 1 |
| 56-60 | (unlabelled in the pages read) | | 2 |

`NPT`, `NELEM`, and `NBPTC` match the actual line counts exactly. `NSMAT` (9) and
`NXMAT` (25) **exceed** the materials actually defined (5 and 19) — so they are declared
capacities or stale values, not exact counts. A validator should treat
`NSMAT >= max soil material id` as the rule, not equality.

`MINBW` being an input parameter confirms that **bandwidth is a first-class CANDE concern**,
which is an argument for doing node renumbering at export time.

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
