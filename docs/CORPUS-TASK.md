# Open task: broaden the test corpus from OneDrive

**Left by:** the session that built Phases 0–3, which lost its Microsoft 365
connector partway through and could not finish this.
**For:** any agent that *does* have OneDrive access.
**Why it matters:** the codec's correctness is defined by the corpus, and the
corpus is currently two files, both thermoplastic. Everything else in the project
rests on specs that only two files have ever exercised.

If you have the connector, please do this before starting new features.

---

## 1. Where things are

| | |
|---|---|
| The files | `OneDrive/Documents/CID Files/` — roughly 200 `.cid` files |
| The manual | `CID Files/CANDE-2025 User Manual.pdf` — 338 pp, April 2025, supersedes all earlier manuals |
| Also there | `CANDE-2025 Program and Manuals package.zip` |
| Scratch folder | `OneDrive/_claude_cid_readable/` — **created by me**, holds two `.cid.txt` copies. Reuse or delete it; the owner has been told it exists. |

## 2. The blocker you will hit, and the way round it

The connector refuses `.cid` outright:

```
VALIDATION_ERROR: MIME type 'application/octet-stream' is not allowed
```

SharePoint reports `.cid` as `application/octet-stream`, which is not on
`read_resource`'s allow-list. **Copy the file and rename it with a `.txt`
suffix**, then read it:

```
sharepoint_copy_item(
    driveId="b!f5_ubACxtkSPDIjpNocZI3qP9wxGgy5MqzHbkH05XjoHSilc4JwPRLI3QM2AKwn3",
    itemId=<the .cid file>,
    destinationParentItemId="01SKO6JUQ2E4AC5CZCK5DYLKIRYUM2DIGI",   # _claude_cid_readable
    newName="whatever.cid.txt",
)
```

Large files exceed the token limit and get persisted to a local path instead of
returned — that is *better*, not worse. Grep and analyse them on disk rather than
pulling them into context.

## 3. What to actually do

### 3a. Run `fmt` over everything — the highest-value check

```bash
candejar fmt path/to/*.cid
```

`fmt` re-reads and re-renders each file and compares bytes. **Any file it reports
as `CHANGED` is a codec bug**, and it is the single most valuable signal
available: it means `candejar` would corrupt that file on save. Investigate every
one. Do not "fix" it by loosening the round-trip test.

### 3b. Run `check` over everything — look for false positives

```bash
candejar check path/to/*.cid
```

These are files CANDE accepted, so **errors are suspect until proven otherwise**.
A rule that cries wolf is worse than a missing rule (invariant 5 in
`CLAUDE.md`). When a rule fires wrongly, narrow the rule; when it fires rightly,
keep it and note the file.

### 3c. Add fixtures

Wanted, roughly in priority order — the corpus has none of these:

1. **Files CANDE rejected.** These pin down validation rules better than any
   number of valid ones. Ask the owner if none are obvious.
2. **Aluminum, CONRIB and CONTUBE** pipe types. Only Plastic is represented.
3. **Link elements** — `IX(7)` of 8, 9, 10 or 11 — including the death step.
   Nothing in the corpus exercises them, so `ElementKind.LINK_*` is untested
   against reality.
4. **`CX-1`…`CX-4`** extended-Level-2 lines.
5. **LRFD files carrying `E-1`.** Both current fixtures are service/ASD.
6. **Level 1** files, and box / arch / 2-radius geometries.
7. **Concrete and steel**, which appear plentiful (`Box 32S…`, `27S BC BOX…`,
   `BC 34A6…`, `CBC 16007…`).

Candidates I noted but never read, with sizes — small ones make the best
fixtures:

```
ADAMS FORK Level2-ANALYS-WSD-TREN-Pipe-PLASTIC-SMOOTH.cid    1,459   Level 2 trench
ALSP 16x8-3 skeleton.cid                                     1,318
BUCKEYE  22in  8-21-2012.cid                                 1,355
BC 34A6 design gage determination.cid                        4,872   design mode?
72''.cid  /  84''.cid                                        6,778
ALSP 16x8-3 pinned load combo 3.cid                         30,591
BC 34A6 Footing Reactions - LRFD FACTORED.cid               46,845   LRFD
CONTECH Blue Heron.cid                                      48,745
2.9' cover HS20.cid                                         94,270   box culvert
27S BC BOX 3ga 2.75' cover ... HS-20 truck.cid              93,892   steel box
Box 32S 4.0ft Cover 3Gage HL-93.cid                         97,096
22406 quad.cid                                             236,439   quad mesh (!)
22406 tria.cid                                             360,523
```

`22406 quad.cid` is worth an early look: **every element in the current corpus is
a triangle or a beam**, so `ElementKind.QUAD` and the quad paths in
`rule_element_geometry` have never met a real quadrilateral.

**Scrubbing rule.** Substitute text of *identical length* so every column is
preserved, then assert it:

- no line changed length
- the `!!` separator still ends at index 27 on every command line
- the identifying string is gone

Only the `A-1` title needed scrubbing on the existing fixture. Record each new
file's fidelity in `tests/fixtures/README.md` — mark it byte-exact only if it is
a true byte copy.

### 3d. Promote the inferred specs using the 2025 manual

Nine of the thirteen line specs were derived from files rather than read from the
manual. Confirming them is cheap once you can read the PDF, and would let their
`Source` change from `INFERRED` to `MANUAL`:

| Spec | Manual section | What is unresolved |
|---|---|---|
| `A-1` | 5.3.1 | Four trailing 5-wide control fields at cols 76–95, currently named `control_a`…`control_d` because nobody knows what they are |
| `A-2.L3`, `A-2.L12` | 5.3.2 | Only the first two fields are mapped |
| `C-3.L3` | 5.5.6.3 | Columns beyond 30 unknown; `LGTYPE` never located |
| `C-5.L3` | 5.5.6.5 | Whole layout inferred from two files; the `IIFLG` boundary codes (Table 5.5-7) are not modelled at all |
| `D-1` | 5.6.1 | `MATNAM` occupies the first five of the name columns for canned soils; kept as one wide field rather than split, because splitting it wrongly mangles names |
| `D-2.Isotropic` / `.Duncan` / `.Interface` | 5.6.2, 5.6.4.1, 5.6.7 | Partial |

Still entirely uncatalogued, and all present in real files: the whole of Part B
(`B-1.Plastic`, `B-2.Plastic`, `B-3.Plastic.A.Profile`, `B-3b.…`), the Level 2
canned-mesh lines (`C-1…C-4.L2.Pipe` / `.Box` / `.Arch`), `D-3.Duncan`,
`D-4.Duncan`, `CX-1`…`CX-4`, and `E-1`. They round-trip verbatim, so adding them
is safe and incremental — one spec, one test, in any order.

Page arithmetic for the 2025 manual: section `5-N` sits at roughly PDF page
`N + 83`. For the 2013 manual it was `N + 87`.

## 4. When you are done

Update `tests/fixtures/README.md`, the spec `Source` values, and the status line
in `CLAUDE.md`. If `fmt` found a genuine round-trip failure, that is the most
important thing to report back — say which file and which line.
