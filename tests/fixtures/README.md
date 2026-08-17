# Test fixtures

Real CANDE `.cid` files, with identifying text scrubbed. They are the corpus the
codec's correctness is defined by: if a change makes any of these fail to
round-trip byte-for-byte, the change is wrong.

## Provenance and fidelity

| File | Fidelity | Notes |
|---|---|---|
| `level1_steel_wsd.cid` | **scrubbed** | Level 1, steel, working stress. 7 lines. The *only* Level 1 file in a 2,886-file corpus. Carries `C-1.L1` and `C-2.L1`, and no `D-1` at all — Level 1 puts its soil on `C-2.L1`. |
| `level2_arch_steel_design.cid` | **scrubbed** | Level 2 **arch** canned mesh, steel, `DESIGN` mode. 77 lines. The only fixture in design mode, and the only one carrying `C-1…C-4.L2.Arch`, `CX-4` and `B-2.Steel.D.WSD`. |
| `level2_pipe_steel_lrfd.cid` | **byte-exact** | Level 2 pipe mesh, steel, **LRFD**. 59 lines. Carries `E-1` and `B-3.Steel.AD.LRFD`; the only LRFD fixture. |
| `level2_pipe_steel_wsd.cid` | **byte-exact** | Level 2 pipe mesh, steel, working stress. 57 lines. `CX-1`…`CX-3`. |
| `level2_plastic_trench_wsd.cid` | **reconstructed** | Level 2 trench pipe mesh, plastic/HDPE, working stress. Command-name prefixes are generated from the verified rule, so the envelope is certainly correct; trailing padding on the records could not be confirmed from the source capture and was not invented. Use it for line-type coverage, not as a fidelity reference. |
| `level3_aluminum_wsd.cid` | **byte-exact** | **Input skeleton, not a model CANDE ran** — see below. The only source of `B-1.Alum` and `B-2.Alum.A`. |
| `level3_concrete_wsd.cid` | **byte-exact** | **Input skeleton, not a model CANDE ran** — see below. The only source of `B-1…B-3.Concrete` and `B-4.Concrete.Case1_2`. |
| `level3_plastic_asd.cid` | **byte-exact** | Level 3, 2,433 lines, 800 nodes, 1,288 elements, 70 boundary conditions, 24 materials, 9 pipe groups. Uses Continuous Load Scaling (`Iscale = 2`, CLS-AAM-θ\*). |
| `level3_quad_steel.cid` | **scrubbed** | Level 3, steel, 20 lines, 6 nodes, 3 elements — including **quadrilaterals**. Until this was added, every element in every fixture was a triangle or a beam, so `ElementKind.QUAD` and the quad paths in `rule_element_geometry` had never met a real four-node element. |

### Skeletons

`level3_aluminum_wsd.cid` and `level3_concrete_wsd.cid` are GUI-emitted input
skeletons: one element on a node that is never defined, and no restraint
anywhere. They are here because nothing else small in the corpus carries the
Concrete and Aluminum Part B lines. They are listed in `INCOMPLETE_MODELS` in
`tests/conftest.py` and excluded from the "produces no errors" tests, because
invariant 5 is a promise about files CANDE *accepted* — these were never run, so
asserting they validate cleanly would prove nothing and would quietly redefine
the invariant. They are still held to round-trip and to every editing test.

## Scrubbing

Only identifying text was changed, and only by substituting text of **identical
length**, so every column position in the file is preserved. The generator
asserted, per file, that no line changed length, that the `!!` separator still
ended at index 27 on every command line, that the identifying string was gone,
that the byte count was unchanged, and that the result still round-trips.

| File | Substitution |
|---|---|
| `level1_steel_wsd.cid` | `Denver, Colorado` → `Example Location` |
| `level2_arch_steel_design.cid` | `Alliance Coal` → `Example Owner` |
| `level3_quad_steel.cid` | `Special Underpass` → `Example Structure` |

Everything else is left exactly as the engineer wrote it — including
`SW100  Embankement Fill`, whose misspelling is load-bearing: preserving it is
evidence that the reader and writer are not "helpfully" normalising content.

## Adding fixtures

Still wanted — none of these appear in any fixture:

- **CONRIB and CONTUBE** pipe types. Neither occurs anywhere in the 2,886-file
  corpus, so these have to come from elsewhere.
- **Link elements** (`IX(7)` = 8, 9, 10, 11), including the death step. 69
  corpus files have them, but the smallest is 98 KB — too big to add as-is.
- **`CX-3`** together with an arch mesh, and **`D-2.MohrCoulomb`** /
  **`D-2.Orthotropic`** / **`D-2.Link`**, whose smallest carriers are 130 KB+.
- **Files CANDE rejected.** The best corpus candidate found is
  `14637 - Mesh2D Trial 6.cid`, whose `C-4.L3` lines are correct through element
  57 and shift one column right from element 58 on; candejar reports the field
  rather than crashing. It is ~100 KB, so it needs trimming to a minimal
  reproducer first.

Scrub by substituting equal-length text, never by deleting or reflowing, and
record the fidelity of each new file in the table above.
