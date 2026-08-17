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
| parsed as a spec'd `Record` | 7,012,577 | 75.3% |
| verbatim, not a command line | 2,275,610 | 24.4% |
| verbatim, command line with no spec | 22,913 | 0.2% |

Three-quarters of the corpus goes through the field machinery rather than past
it, so the clean sweep is real evidence and not an artefact of the fallback.
Of the lines that *are* command lines, 99.7% now have a spec.

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

## 4. Open: a field-level asymmetry that `fmt` cannot see

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

None of this corrupts a file today: nothing writes a field it has not been asked
to change, and every rewrite stays inside that field's own columns (invariant 3).
It matters for two reasons. The `Text` case is a genuine hazard where the column
is load-bearing — `MATNAM` at column 21 selects a canned soil. And a no-op write
that changes bytes makes diffs noisy and would surprise anyone who assumed
`set(f, get(f))` was free.

The narrow fix is to make `Record.set()` leave the raw text alone when the new
value decodes equal to the current one. That is a real design change to the
write path, so it is left for the owner to decide rather than folded into a
corpus sweep.

## 5. Corpus facts worth knowing

- **Level 1 is nearly extinct**: exactly one file in 2,886.
- **CONRIB and CONTUBE do not occur at all.** Fixtures for them must come from
  somewhere else.
- **`STEEL` dominates** (2,076 files), then `PLASTIC` (239), `ALUMINUM` (145),
  `CONCRETE` (36), `BASIC` (18).
- **Quadrilaterals are the norm**, not the exception: 2,269 files have them,
  though no fixture did until now.
- 41 command names still have no spec, out of 55 that occur. The largest are
  `B-3b.Plastic.A.Profile` (4,868 lines), `B-1.Steel` / `B-2.Steel.A` (~2,470
  each, in ~2,076 files), and `D-3.Duncan` / `D-4.Duncan` (926 each).
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
