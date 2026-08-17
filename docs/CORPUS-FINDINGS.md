# What a 2,886-file corpus said about the codec

The task in [`CORPUS-TASK.md`](CORPUS-TASK.md) asked for `fmt` and `check` to be
run across the OneDrive `CID Files` folder. It has grown since that note was
written — 2,886 `.cid` files, 9.3 million lines, plus the CANDE-2025 User Manual
— so this records what the sweep found and what changed as a result.

The files themselves are **not** in the repository. Seven small ones were
scrubbed and added as fixtures; see [`../tests/fixtures/README.md`](../tests/fixtures/README.md).

## 1. Round-trip: clean, and the result is meaningful

```
2,886 files    2,886 unchanged    0 CHANGED    0 crashes
```

**No round-trip bug exists in this corpus.** `dumps(read_cid(path))` reproduced
every one of the 2,886 files byte-for-byte, and no file raised.

That number is worth only as much as the share of the corpus it actually
exercises, because an unknown line type becomes a `Verbatim` and round-trips by
construction (invariant 2). So coverage was measured alongside it:

| | lines | share |
|---|---:|---:|
| parsed as a spec'd `Record` | 7,020,772 | 75.4% |
| verbatim, not a command line | 2,275,610 | 24.4% |
| verbatim, command line with no spec | 14,718 | 0.2% |

Three-quarters of the corpus goes through the field machinery rather than past
it, so the clean sweep is real evidence and not an artefact of the fallback.
Of the lines that *are* command lines, **99.79%** now have a spec.

Line share understates the Part B work in §3: those lines are few per file — a
handful per pipe group — but they appear in 2,076 of 2,886 files, and they are
where the pipe's material and section properties live.

## 2. Two validation rules were crying wolf

These are files CANDE accepted, so an error is suspect until proven otherwise
(invariant 5). Two rules produced almost all of the noise.

### `interface-connectivity` — 64,421 findings, all false

The rule errored when an interface or link element's K node did not exceed
*both* I and J. The manual (5.5.6.6) says IX(3)

> must be larger than either IX(1) or IX(2), preferably larger than both

Only the first half is a requirement. Measured across all 78,158 interface and
link elements in the corpus:

| | elements | files |
|---|---:|---:|
| `k <= min(i, j)` — real rule broken | **0** | 0 |
| `min < k <= max` — preference only | 64,421 | 1,671 |
| `k > max(i, j)` — both satisfied | 13,737 | — |

The rule caught nothing that was actually wrong and fired on 58% of the corpus.
It now errors on `k <= min(i, j)`; the preference is not reported.

### `element-count` — 86 of 135 findings false

`NELEM` was compared against the number of `C-4` lines. CANDE fills gaps in
element numbering by generating the missing elements, so a gapped file
legitimately lists fewer lines than `NELEM`. Of 135 files flagged, 86 were
gapped files CANDE had accepted. The rule now compares `NELEM` against the
highest element number.

### Result

| | before | after |
|---|---:|---:|
| files reporting at least one error | 1,871 | 167 |
| files reporting none | 1,015 | 2,719 (94%) |

The 167 that remain look real: 48 files declaring one more element than they
define (one bad model, copied many times), 46 missing their `STOP` line, and
clusters of interface elements pointing at materials no `D-1` defines.

## 3. Specs promoted and added, from the 2025 manual

| Spec | Was | Now | What the manual settled |
|---|---|---|---|
| `A-1` | `INFERRED`, partial | **`MANUAL`** | The four trailing 5-wide fields are `ITMAX`, `CULVERTID`, `PROCESSID`, `SUBDID`. `XMODE` is columns 1–8, not 1–6, and `LEVEL` is 9–10, not 7–10 — the old columns decoded correctly only because no mode name is longer than six characters. |
| `E-1` | *absent* | **`MANUAL`** | `INCRS` 1–5, `INCRL` 6–10, `FACTOR` 11–20, `COMMENT` 21–60 (5.7.1). Present in 2,030 of 2,886 files and 261,571 lines — by far the largest single gap. |

Both were re-checked against the whole corpus after the change: every one of
those 261,571 `E-1` lines and every `A-1` line decodes without error, and the
round-trip sweep was re-run and still reports 2,886 unchanged. That second run
is the stronger one — those 261,571 lines had previously been `Verbatim`
passthrough and are now actually parsed.
| `D-1` | `INFERRED` | `INFERRED`, documented | See below. |

### The Part B pass: steel and aluminum

A second pass catalogued the pipe-material lines, all at `Source.MANUAL`:

| Spec | Manual | Lines | Files |
|---|---|---:|---:|
| `B-1.Steel` | 5.4.5.1 | 2,468 | 2,076 |
| `B-2.Steel.A` | 5.4.5.2 | 2,467 | 2,075 |
| `B-3.Steel.AD.LRFD` | 5.4.5.8 | 1,956 | 1,795 |
| `B-1.Alum` | 5.4.1.1 | 442 | 145 |
| `B-2.Alum.A` | 5.4.1.2 | 442 | 145 |
| `B-3.Alum.AD.LRFD` | 5.4.1.4 | 420 | 131 |

All six verified against the whole corpus: **zero** fields refusing to decode,
**zero** lines with content past the last spec'd column, and round-trip still
clean. Unlike `D-1`, the manual and reality agree exactly here.

Two things worth knowing. `B-2.Steel.A` and `B-2.Alum.A` carry the section
properties — area, moment of inertia and section modulus **per unit length** —
that a corrugation-and-gage library would supply; steel adds `PZ`, a plastic
modulus for deep corrugations, which aluminum has no counterpart to. And
aluminum is *not* steel with a different name: it has no joint-slip option, so
`NONLIN` and `IBUCK` sit five columns earlier. Assuming the layouts matched
would have read `NONLIN` out of `PE2`'s columns.

### A-2 was reporting a canned-mesh code as an element count

Both `A-2` specs named columns 11–15 `elements`. The manual (5.3.2) gives two
different fields there: `NPMATX`, the connected beam count, on `A-2.L3` — but
`NPCAN`, the **canned-mesh code**, on `A-2.L12`, and only for Level 2.

So every Level 1 or 2 file reported a fictitious element count:
`PipeGroup(pipe_type='STEEL', elements=1)` for a canned circular pipe mesh that
has no `C-4` lines at all, because CANDE generates them. A viewer would have
shown "1 element" for a mesh of hundreds. Both specs are now `MANUAL`, and
`A-2.L12`'s field is `canned_mesh`. Across the corpus, 3,549 groups carry
`NPMATX` and 19 carry `NPCAN`, and **no group carries both**.

`D-1` deliberately still deviates from the manual, which is why it was **not**
promoted. The manual gives `MATNAM` as columns 21–40 (`5A4`) and a GUI-only
layer count at 41–42 (`I2`), and states that `MATNAM` "starts in column 21 and
is 4 or 5 capital letters and/or numbers" — so column 21 is positional and must
be preserved. But real files run descriptive text straight through column 40:
the existing fixture writes `SW100  Embankement Fill`, whose `il` lands in
columns 41–42. Modelling 41–42 as an integer reported those files as broken —
manufacturing exactly the kind of false positive just removed — so the `name`
field stays one wide span and the layer count is left unaddressed rather than
invented. Invariant 6: the provenance label stays honest about that.

## 4. A field-level asymmetry that `fmt` cannot see — found, and fixed

`fmt` proves the *envelope* round-trips. It does not prove that writing a field
back is lossless, because `Record.set()` only rewrites the one field it is given.
Re-encoding each field with the value just decoded from it does not reproduce the
original bytes in 44 field kinds:

| Cause | Example | Occurrences |
|---|---|---|
| `Whole` normalises leading zeros | `00` → ` 0` | 2,534,368 |
| `Real` drops the file's decimal formatting | `   -300.00` → `      -300` | 185,979 |
| `Text` left-justifies, shifting past a leading space | ` Inter # 1` → `Inter # 1 ` | 65,417 |

(Counted before the `A-1` and `E-1` spec changes in §3, which shift the totals
slightly without changing the three causes.)

No file was being corrupted: nothing writes a field it has not been asked to
change, and every rewrite stays inside that field's own columns (invariant 3).
But it mattered for two reasons. The `Text` case is a genuine hazard where the
column is load-bearing — the manual says `MATNAM` "starts in column 21", and a
one-column shift changes which canned soil CANDE selects. And a no-op write that
changes bytes makes diffs noisy and would surprise anyone who assumed
`set(f, get(f))` was free.

**Fixed.** `Record.set()` now returns the record untouched when the field
already decodes to the value being written. A field whose text will not decode
at all is still overwritten — that is exactly what a write is for. Verified
across the corpus: rewriting every field of every record with the value just
read from it changes **0** lines, down from 2.8 million.

The encoders themselves are deliberately unchanged and still render
canonically — that is what they are for when a value really does change. The
fix is that `set()` no longer invokes them when nothing has changed. Invariant 3
in `CLAUDE.md` now states both halves of the property.

## 5. Corpus facts worth knowing

- **Level 1 is nearly extinct**: exactly one file in 2,886.
- **CONRIB and CONTUBE do not occur at all.** Fixtures for them must come from
  somewhere else.
- **`STEEL` dominates** (2,076 files), then `PLASTIC` (239), `ALUMINUM` (145),
  `CONCRETE` (36), `BASIC` (18).
- **Quadrilaterals are the norm**, not the exception: 2,269 files have them,
  though no fixture did until now.
- 35 command names still have no spec, out of 55 that occur. The largest are
  `B-3b.Plastic.A.Profile` (4,868 lines) and `B-3.Plastic.A.Profile` (2,411),
  `B-4.Concrete.Case1_2` (2,158), and `D-3.Duncan` / `D-4.Duncan` (926 each).
  Plastic is the obvious next material: second most common pipe type at 239
  files, and its Part B lines are the largest remaining block.
- **67 Level 3 files declare more pipe groups than they define** — `A-1` gives
  `NPGRPS = 3` while the file carries one `A-2` and one Part B set. The reading
  is not in doubt: `NPGRPS` is columns 13–15, it decodes correctly on the
  nine-group fixture, and every `A-1` in the corpus decodes without error. No
  rule was written for this, because it is not known whether CANDE accepted
  these files, and a rule guessed at is how invariant 5 gets broken. Worth an
  answer from someone who can run them.
- Two files carry genuinely malformed fields, and candejar reports them by field
  rather than crashing (invariant 4): `14637 - Mesh2D Trial 6.cid`, whose `C-4`
  lines shift one column right from element 58 on, and two
  `PE-…DESIGN GUIDE; REV 4.cid` files whose `D-2.Duncan` `IBULK` column holds
  `0.33`.

## How to reproduce

The sweep scripts are not in the repo — they are short and were run against a
local checkout. Each is a loop over `rglob("*.cid")` doing one of:

- `dumps(read_cid(p)).encode("latin-1") == p.read_bytes()` — the `fmt` check
- `run_rules(Problem(read_cid(p)))`, grouped by rule with numbers masked — the
  `check` sweep
- for every `Record` field, `kind.encode(kind.decode(raw), width) == raw` — the
  field-level asymmetry in §4
