# Test fixtures

Real CANDE `.cid` files, with identifying text scrubbed. They are the corpus the
codec's correctness is defined by: if a change makes any of these fail to
round-trip byte-for-byte, the change is wrong.

## Provenance and fidelity

| File | Fidelity | Notes |
|---|---|---|
| `level3_plastic_asd.cid` | **byte-exact** | Level 3, 2,433 lines, 800 nodes, 1,288 elements, 70 boundary conditions, 24 materials, 9 pipe groups. Uses Continuous Load Scaling (`Iscale = 2`, CLS-AAM-θ\*). |
| `level2_plastic_trench_wsd.cid` | **reconstructed** | Level 2 trench pipe mesh, plastic/HDPE, working stress. Command-name prefixes are generated from the verified rule, so the envelope is certainly correct; trailing padding on the records could not be confirmed from the source capture and was not invented. Use it for line-type coverage, not as a fidelity reference. |

## Scrubbing

Only the `A-1` title field was changed, and only by substituting text of
**identical length**, so every column position in the file is preserved. The
generator asserted that no line changed length and that the `!!` separator still
ended at index 27 on every command line.

Everything else is left exactly as the engineer wrote it — including
`SW100  Embankement Fill`, whose misspelling is load-bearing: preserving it is
evidence that the reader and writer are not "helpfully" normalising content.

## Adding fixtures

Wanted, in rough priority order:

- files CANDE **rejected** — these pin down validation rules better than any
  number of valid files
- aluminum, CONRIB and CONTUBE pipe types
- models using **link elements** (`IX(7)` = 8, 9, 10, 11), including the death step
- the `CX-1`…`CX-4` extended-Level-2 lines
- Level 1, and LRFD files carrying `E-1`
- box, arch and 2-radius geometries

Scrub by substituting equal-length text, never by deleting or reflowing, and
record the fidelity of each new file in the table above.
