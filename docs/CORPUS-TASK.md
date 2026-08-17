# Corpus task — done, and what is left

The sweep this file used to ask for has been run against the OneDrive
`CID Files` folder, which by then held **2,886** `.cid` files and the CANDE-2025
User Manual. The results are in [`CORPUS-FINDINGS.md`](CORPUS-FINDINGS.md).

The short version: **`fmt` reported zero changed files** — there is no
round-trip bug in the corpus — and 75% of its 9.3 million lines go through the
field machinery rather than past it, so that is real evidence rather than an
artefact of the verbatim fallback. Two validation rules were found to be crying
wolf and were narrowed; `A-1` and a new `E-1` were promoted to `Source.MANUAL`;
seven fixtures were added.

---

## Still open

### 1. Decide what `Record.set()` should do about no-op writes

The one unresolved correctness question. Re-encoding a field with the value just
read from it does not reproduce the original bytes in 44 field kinds — `Real`
drops the file's decimal places, `Whole` normalises `00` to ` 0`, and `Text`
left-justifies past a leading space. Nothing corrupts a file today, but the
`Text` case is a hazard wherever a column is load-bearing, and `MATNAM` at
column 21 is exactly that. §4 of `CORPUS-FINDINGS.md` has the numbers and a
proposed narrow fix. This is a change to the write path, so it wants an owner's
decision, not a drive-by.

### 2. Fixtures that could not be obtained

- **CONRIB and CONTUBE** — absent from all 2,886 files. Must come from elsewhere.
- **Link elements** (`IX(7)` = 8–11) including the death step — 69 files have
  them, smallest 98 KB. Needs a hand-built minimal reproducer.
- **A file CANDE rejected** — best candidate is `14637 - Mesh2D Trial 6.cid`,
  whose `C-4.L3` lines are correct through element 57 and shift one column right
  from element 58 onward. ~100 KB; needs trimming.

### 3. Line types still uncatalogued

41 command names have no spec. They round-trip verbatim, so adding them is safe
and incremental — one spec, one test, in any order. By corpus weight:

| Spec | Lines | Files | Manual section |
|---|---:|---:|---|
| `B-3b.Plastic.A.Profile` | 4,868 | 159 | 5.4.4.5 |
| `B-1.Steel` | 2,468 | 2,076 | 5.4.5.1 |
| `B-2.Steel.A` | 2,467 | 2,075 | 5.4.5.2 |
| `B-3.Plastic.A.Profile` | 2,411 | 159 | 5.4.4.4 |
| `B-4.Concrete.Case1_2` | 2,158 | 36 | 5.4.3.4 |
| `B-3.Steel.AD.LRFD` | 1,956 | 1,795 | 5.4.5.8 |
| `D-3.Duncan` / `D-4.Duncan` | 926 each | 292 | 5.6.4.2 / 5.6.4.3 |
| `CX-1`…`CX-4` | 18–689 | 8–18 | 5.5.5.1–5.5.5.4 |
| `C-1…C-4.L2.Pipe` / `.Arch` | 8–11 each | 8–11 | 5.5.2 / 5.5.4 |

`C-3.L3`, `C-5.L3` and `D-2.*` remain `INFERRED` and partial. `C-5.L3`'s
`IIFLG` boundary codes (Table 5.5-7) are still not modelled at all.

## Reading the manual

`CID Files/CANDE-2025 User Manual.pdf`, 338 pages, April 2025, supersedes all
earlier manuals. `pypdf`'s `extract_text()` handles it well enough to grep.

Each input parameter is laid out as a stack — name, `(SYMBOL)`, `(01-05)`,
`(I5)`, `(units)` — so the surest way to recover a column table is to find the
section heading, then pull every line matching `^\s*\(\d+\s*-\s*\d+\)\s*$` with
the three lines above it. Section `5-N` sits at roughly PDF page `N + 83`; for
the 2013 manual it was `N + 87`.

Watch for the manual describing a stricter format than files actually use.
Both false-positive rules and the `D-1` `MATNAM` question came from that gap:
the manual's column table is what CANDE *reads*, which is not always what the
GUI *writes*.

## Scrubbing rule

Substitute text of **identical length** so every column is preserved, then
assert it: no line changed length, the `!!` separator still ends at index 27 on
every command line, the identifying string is gone, the byte count is unchanged,
and the result still round-trips. Record each file's fidelity in
`tests/fixtures/README.md`, and mark it byte-exact only if it is a true byte copy.
