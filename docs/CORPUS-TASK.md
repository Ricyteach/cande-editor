# Corpus task — done, and what is left

The sweep this file used to ask for has been run against the OneDrive
`CID Files` folder, which by then held **2,886** `.cid` files and the CANDE-2025
User Manual. The results are in [`CORPUS-FINDINGS.md`](CORPUS-FINDINGS.md).

The short version: **`fmt` reported zero changed files** — there is no
round-trip bug in the corpus — and 75% of its 9.3 million lines go through the
field machinery rather than past it, so that is real evidence rather than an
artefact of the verbatim fallback. Two validation rules were found to be crying
wolf and were narrowed; `A-1` and a new `E-1` were promoted to `Source.MANUAL`;
seven fixtures were added; and a field-level write asymmetry the sweep turned up
— which `fmt` cannot see — was fixed in `Record.set()`.

---

## Still open

### 1. Fixtures that could not be obtained

- **CONRIB and CONTUBE** — absent from all 2,886 files. Must come from elsewhere.
- **Link elements** (`IX(7)` = 8–11) including the death step — 69 files have
  them, smallest 98 KB. Needs a hand-built minimal reproducer.
- **A file CANDE rejected** — best candidate is `14637 - Mesh2D Trial 6.cid`,
  whose `C-4.L3` lines are correct through element 57 and shift one column right
  from element 58 onward. ~100 KB; needs trimming.

### 2. Line types still uncatalogued

41 command names have no spec. They round-trip verbatim, so adding them is safe
and incremental — one spec, one test, in any order. By corpus weight:

| Spec | Lines | Files | Manual section |
|---|---:|---:|---|
| `B-3b.Plastic.A.Profile` | 4,868 | 159 | 5.4.4.5 |
| `B-3.Plastic.A.Profile` | 2,411 | 159 | 5.4.4.4 |
| `B-4.Concrete.Case1_2` | 2,158 | 36 | 5.4.3.4 |
| `D-3.Duncan` / `D-4.Duncan` | 926 each | 292 | 5.6.4.2 / 5.6.4.3 |
| `B-1.Plastic` / `B-2.Plastic` | 421 / 428 | ~258 | 5.4.4.1 / 5.4.4.2 |
| `B-1…B-3.Concrete` | 223 each | 36 | 5.4.3.1–5.4.3.3 |
| `CX-1`…`CX-4` | 18–689 | 8–18 | 5.5.5.1–5.5.5.4 |
| `C-1…C-4.L2.Pipe` / `.Arch` | 8–11 each | 8–11 | 5.5.2 / 5.5.4 |

Plastic is the obvious next material: it is the second most common pipe type
(239 files) and `B-1.Plastic`/`B-2.Plastic` are the last common lines with no
spec. Its profile-wall lines are the largest remaining block by line count.

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
