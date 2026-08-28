# Issue 18 — real-data production: 1000 beam-on + 1000 beam-off events

Data counterpart of [issue #16](https://github.com/HaiwangYu/wire-cell-toolkit-ai-helper/issues/16)
(13,213 MC events). Same chain (img → clus → Q/L match → tagger → PR), same
computing setup (32 workers × 1 core, one `lar` process per event), **same
configuration** — which means the same `#17` operating-point gap; see Caveats.

Work/output: `/exp/sbnd/data/users/yuhw/production-prep/img-clus-match-tag-pr-data-1000evt-2026-08-21/`

| sample | status |
|---|---|
| **beam-on**, 1000 events | **complete** — 1000/1000, 25 min |
| **beam-off**, 1000 events | **complete** — 1000/1000, 69 min |

**Headline result: the rate of real reconstructions is 42.1% beam-on against
3.4% beam-off — a factor 12.4, a 38.7 ± 1.7% difference (23σ).** That is the
strongest end-to-end sanity check the chain has had: the tagger fires on beam
and very rarely off beam, on real data, with no truth involved.
*(Corrected 2026-08-27 from 43.4% / 7.5% / 5.8× — see "Counting corrected".)*

## Data mode differs from MC in four ways

Config is `sbnd/wcls-img-clus-matching-xin-data.fcl`, which already existed:
`reality="data"` plus the `sptpc2d` product tags (`sptpc2d:dnnsp` ×2,
`sptpc2d:wienersummary`, `sptpc2d:badmasks`). Consequences, all verified:

1. **No truth Bee layers.** 16 layers instead of 20 — no `truth_trackid_labeled`,
   no `truth_unlabeled`, no three `sed-*`. Bee zips are ~4× smaller
   (1.01 MB vs 4.61 MB).
2. **`mc.json` is reco-only, and still present.** e.g. `gamma 86 MeV`,
   `gamma 5 MeV`, `proton 111 MeV` at top level with no "reco nu" wrapper —
   `merge_metadata_key` finds no truth tree, so the reco nodes are published
   directly. Not empty, not missing. **This verifies issue 13's T4** (exercise
   the empty PF branch on data).
3. **nugraph is input-only.** `y_semantic` and `y_instance` are **all −1**, so
   the graph carries features and edges but **no training target**. Still
   produced; do not expect to train on it.
4. **Frameshift is mandatory upstream.** Every Gen2 real-data reco1 file must
   have `run_frameshift.fcl` applied before this chain or the TPC/PMT time
   alignment is wrong and Q/L matching is meaningless. The beam-on input was
   already frameshifted; `prep-beam-off.sh` does it for beam-off and then
   *verifies the FrameShift product actually landed* rather than assuming.

## The `--nskip` ordering bug (found and fixed here)

Worth reading before reusing any of this.

The first smoke wrote a file named `r18259_s1_e171099` whose `Trun` said
**18255/1/49415**. Cause:

> **`lar --nskip k` counts in art's logical `FileIndex` order — sorted by
> (run, subrun, event) — not the Events-tree write order that `EventAuxiliary`
> is read in.**

For a single-run-per-file input (every MC reco1 file) the two orders coincide,
so the issue-16 harness was correct **by luck**. This merged data file (1000
events from 20 reco1 files) starts its Events tree with run 18259 while art
starts with 18255, so `--nskip 0` processed tree entry **300**.

Why it is dangerous: every output file is internally self-consistent — the Bee
JSON, `Trun` and the nugraph key all carry the RSE the job really saw. Only the
*filename* is wrong. Nothing fails and nothing warns. Unsorted, all 1000
outputs would have been mislabelled invisibly.

Two fixes, both in place:

- `make-manifest.sh` sorts the RSE triplets into art's order before assigning
  the `--nskip` index. Verified at indices **0, 1, 499, 999** — index 0 agreeing
  proves nothing on its own.
- `run-harness.sh` reads the RSE back from each job's own `tracking-pr.root:Trun`,
  **names the files from that**, and records an `rse_check` column. A wrong
  prediction is now loud instead of silent.

**Issue 16's MC dataset is unaffected**: single-run inputs, and `Trun` was
independently verified there.

## Beam-on results (complete)

Input: `add-frameshift-data-2nd-2k-2026-08-15/data_MCP2025C_reco1_frameshift_2nd1k_part1.root`
— exactly 1000 events, runs 18255 (850) and 18259 (150), subrun 1.

`2026-08-21 15:08:26 → 15:33:34 CDT`, **25 min 08 s**, 12.4 core-hours.

| | result |
|---|---|
| events | **1000 / 1000 (100%)** |
| deliverables | 1000 × 3, **0** zero-size or missing |
| RSE | 1000 unique, and **identical to the manifest prediction** (0 differences) |
| `audit` FAIL | **0** |
| `rse_check` != ok | **0** |
| wall | mean **44.5 s**, median 42, p90 58, p99 104, **max 192** |
| memory | mean 48.0 GB, **max 57.8 GB** at 32 jobs |
| disk | **2.4 GB** — Bee 968 MB, nugraph 1.3 GB, tracking-pr 114 MB |
| candidates | **434 / 1000 = 43.4%** |

Two things differ from the MC run in a useful way:

- **No tail.** Zero events over 300 s, max 192 s. MC had 25 events over 300 s
  and a 2988 s maximum. Real events are far more uniform than
  `prodgenie_corsika` MC.
- **The 10-event pilot over-estimated cost by 2×** (95.9 s vs 44.5 s). The pilot
  took the *first* ten manifest entries, which are systematically heavier;
  sampling the head of a sorted manifest is a biased estimator. Sample randomly
  next time.

Disk is 2.45 MB/event against MC's 5.78, almost all of it the absent truth
layers.

### Bee (first 10 events)

- full chain: <https://www.phy.bnl.gov/twister/bee/set/39fad5b1-bbb4-47ad-92c3-f1c95e1a6cea/event/list/>
- nugraph space points: <https://www.phy.bnl.gov/twister/bee/set/ab1514e6-ba9a-4c7f-bfac-dae731417d05/event/list/>

## Beam-off (complete)

Built here from the SAM definition
`data_MCP2025C_FallValidationII_RollingDev_offbeamlight_v10_14_00_reco1_sbnd`
(738 files; 60 resolved to `/pnfs`), merged + frameshifted into one 4.05 GB /
1000-event file by `prep-beam-off.sh`, which then **verifies the FrameShift
product actually landed** rather than assuming it. Owner decision: use this
definition as-is — it is the only Run-1 beam-off reco1 sample currently
available — despite being a different campaign and version from beam-on
(`FallValidationII_RollingDev` v10_14_00 vs `Fall25-Run1_BNB_Dev` v10_14_02).

`22:14:35 → 23:23:51 CDT`, **69 min**, 28.7 core-hours, **26** workers (see the
memory note below).

### samweb: reachable all along

An earlier version of this doc claimed samweb was unreachable from the build
node. **That was wrong.** It works inside SL7 once the ups environment is set
up — `source setup-local-opt.sh; setup sam_web_client` (v3_6). Two errors
produced the false conclusion: a hand-prepended PATH to the cvmfs v3_3 client,
and — the real one — testing reachability with `getent hosts samweb.fnal.gov`,
which **fails even where `samweb` itself works**. Recorded in `sbnd/CLAUDE.md`
and memory: run the real command, never a proxy for it.

### 26 workers, not 32

At 32 workers beam-off held **73.7 GB** (samples repeatedly 66–74 GB), over the
64 GB budget, with the host down to 29 GB available. Beam-off jobs are ~20%
heavier than beam-on: mean peak RSS **2.36 GB vs 1.96 GB**. The two stated
constraints ("32 cores", "<64 GB") conflict for this sample, so the memory cap
won — it is the one that affects other users of a shared box — and the run was
restarted at 26 workers, costing ~5 min of redone work. Result: mean 46.5 GB,
**max 60.2 GB**.

## Both samples, side by side

| | beam-on | beam-off |
|---|---|---|
| events | **1000 / 1000** | **1000 / 1000** |
| zero-size / missing | 0 | 0 |
| RSE unique, == manifest | 1000, 0 diff | 1000, 0 diff |
| `audit` FAIL / `rse_check` | 0 / 0 | 0 / 0 |
| workers | 32 | 26 |
| wall | 25 min, 12.4 core-h | 69 min, 28.7 core-h |
| wall/event | mean **44.5 s**, median 42, p99 104, max 192 | mean **103.5 s**, median 53, p99 1769, max 2199 |
| events > 300 s | **0** | 27 |
| concurrent RSS | mean 48.0, max **57.8 GB** | mean 46.5, max **60.2 GB** |
| disk | 2.4 GB (2.45 MB/evt) | 2.4 GB (2.39 MB/evt) |
| **real reconstructions** | **421 / 1000 = 42.1%** | **34 / 1000 = 3.4%** |
| runs covered | 2 (18255, 18259) | 43 |

Medians are close (42 vs 53 s); the beam-off mean is driven entirely by a tail,
and that tail is one run.

### Run 18308 is an anomaly worth a look

23 of beam-off's 27 tail events come from **run 18308**, and it is not a
high-occupancy effect:

| | events | mean wall | Bee | nugraph | candidates |
|---|---|---|---|---|---|
| run 18308 | 28 | **1459.7 s** | 0.95 MB | 1.22 MB | **0 (0%)** |
| all other beam-off | 972 | **64.4 s** | 1.03 MB | 1.34 MB | 75 (8%) |

**23× the processing time on slightly *below*-average data volume, and not one
candidate in 28 events.** Whatever is slow is not proportional to the amount of
data, so this looks like a degenerate condition in clustering or PR rather than
a busy detector. Excluding 18308, beam-off is mean 64.4 s / median 52 / p99 260,
and the candidate rate is 7.7% — i.e. the physics conclusion does not depend on
this run, but the cost does. One 2199 s event in run 18277 is a separate
outlier.

All 27 tail events are stubs (0% candidates), against 8% for events under 300 s.

## Configuration confirmation vs issue #16 / #17

Verified 2026-08-21 by **compiling the data config and diffing it**, using the
issue-17 audit script (`issues/17-pr-operating-point-drift/scripts/audit-config-diff.py`)
— not by reading the fcl. Raw output:
[`config-diff-sim-vs-data-2026-08-21.txt`](config-diff-sim-vs-data-2026-08-21.txt).

### The issue-17 operating-point gap is identical here

Diffing the **data** config against Xin's 2-step reproduces the issue-17 result
exactly — same total, same components, same counts as the sim run:

| component | knobs Xin sets that we don't |
|---|---|
| `TaggerCheckNeutrino:pr` | **139** |
| `ClusteringProtectBundle:pr` | 5 |
| `CreateSteinerGraph:pr` / `:prrefresh` | 3 each |
| `ClusteringUnmergeBundle:pr`, `TaggerCheckTGM:pr`, `UbooneTaggerOutputVisitor:pr` | 2 each |
| `TaggerCheckFC:pr`, `TaggerCheckSTM:pr`, `ClusteringExamineBundles:all` | 1 each |
| **total** | **160** — identical to the MC campaign |

Diffing sim against data directly, **none of the issue-17 components appear**:
`TaggerCheckNeutrino`, `ClusteringProtectBundle`, `CreateSteinerGraph`,
`ClusteringUnmergeBundle`, all three `TaggerCheck*` and
`UbooneTaggerOutputVisitor` are byte-identical between the two runs. The
pre-flip PR operating point carried over unchanged.

### …but the two runs are not byte-identical: `reality=data` changes 24 things

These are the reality switch working as intended, not operating-point toggles:

| what | sim | data |
|---|---|---|
| `coords` on 9 `Clustering*` + both labelers' `tagger_coords` | `["x_t0cor","y","z"]` | `["x_t0cor","y_cor","z_cor"]` |
| `DetectorVolumes` `pos_offset` (APA0 / APA1) | `null` | `[0,-1.1,6.7]` / `[0,1.1,-6.7]` |
| `QLMatching:matching_joint` `QtoL` | `1` | **`0.86`** |
| `QLMatching:matching_joint` `data` | `false` | `true` |
| `wclsCookedFrameSource` product tags | `simtpc2d:*` | `sptpc2d:*` |
| `reality` on both labelers | `"sim"` | `"data"` |
| `bee_points_sets` coords on `clus_all_apa`, `clus_pr` | — | follows the coord change |

The per-TPC `pos_offset` is the source of the `y_cor`/`z_cor` coordinates
(`pos_offset_on=true` for data), and `QtoL = 0.86` is a real physics difference
in the light-yield scaling used by Q/L matching.

### What this means

- **The #17 caveat transfers exactly.** Absolute candidate rates, `T_tagger`,
  `T_kine` and `kine_reco_Enu` are this pre-flip configuration's numbers in the
  data run just as in the MC one.
- **Beam-on vs beam-off is internally consistent** — both data samples used
  the identical config, so the 12.4× ratio is not a configuration artifact.
- **Data vs MC comparisons are affected by the 24 reality differences**,
  independently of #17 — particularly `QtoL 0.86` and the position offsets.

Not settled by config alone: this confirms the *configuration* matched, not the
*binaries*. Both campaigns loaded the same `opt` install (built 2026-08-20
20:48–21:09 and unchanged since), so the code matched too — but that rests on
install timestamps, not on a compiled diff.

## Bug found in the data Bee `mc.json`, and fixed (2026-08-27)

Owner spotted it by comparing Bee event displays: the MC `mc.json` carries a
`reco nu 107.5 MeV numu ... nue ...` node, the data one does not.

**Nothing was miscomputed and nothing is missing from the dataset — the values
were never rendered.** On beam-on event `18255/1/49987` (Bee event 6 of the
pilot set), `mc.json` held a single bare `mu- 480 MeV` node while
`tracking-pr.root` held `kine_reco_Enu = 486.69 MeV`,
`numu_score = 2.6033`, `nue_score = -4.3009`.

### Cause — three links, each verified

1. `TensorSetLabeler.cxx:550` returns early when `reality != "sim"`, so
   `m_pf_particles` stays empty and line 1735 never publishes the
   `bee_pf_truth` metadata key. **Data has no upstream truth tree.**
2. `MultiAlgBlobClustering::pf_set_particles()` took an early return in exactly
   that case:
   ```cpp
   if (!have_upstream) { tree.set_particles(particles); return; }
   // ...only past here was the "reco nu <Enu> MeV numu X nue Y" node built
   ```
3. The summary text existed **only** inside the merge wrapper.

So the summary was coupled to "is there truth to merge with", which is
independent of "is there reco to summarise". MC always has truth, so it always
appeared; data never does, so it never did. Introduced in issue 13 G5, when the
truth+reco merge was added — the summary was made a property of the wrapper
rather than of the reco.

It also means the T4 verification reported earlier was incomplete: `mc.json` was
confirmed present and non-empty on data, but not confirmed to carry everything
it should.

### Fix

`pf_summary_node()` extracted, and built whenever there is reco, independent of
the upstream truth tree; the truth forest is grafted on top only when it exists.
Plus a **no-candidate marker**, so a declined event says so instead of looking
like a bare particle list (MC) or an empty layer (data). The reason is carried
in parentheses, since "no main vertex" and "no PR graph" are different failures
and that is what a hand scan wants to know. New `BeePFConfig::no_candidate_text`
(default on; `""` disables).

Display-only: it cannot change reconstruction, `T_tagger`, `T_kine`, or the
nugraph.

### Verified on all four cases

| case | `mc.json` after the fix |
|---|---|
| data, candidate (`18255/1/49987`) | `reco nu  486.7 MeV   numu 2.603   nue -4.301` with `mu- 480 MeV` nested under it |
| data, no candidate (`18255/1/50273`) | `no reco neutrino candidate (no TrackFitting)` |
| MC, truth+reco (`713/74/3`) | `1 numu RES CC …` + `reco nu  107.5 MeV   numu -1.715   nue -15.000` — **unchanged** |
| MC, truth only (`713/74/4`) | two truth nodes + `no reco neutrino candidate (no TrackFitting)` (new) |

The data numbers match `T_kine`/`T_tagger` exactly (486.69 → 486.7,
2.6033 → 2.603, −4.3009 → −4.301), and the MC candidate case is byte-identical
to before, so the merge path did not regress.

### Datasets already produced

The MC 13,213-event and data 2,000-event Bee zips were written **before** this
fix, so their `mc.json` still shows the old behaviour. The reconstructed
quantities for those events are unaffected and remain available in
`tracking-pr.root` (`T_kine.kine_reco_Enu`, `T_tagger.numu_score`/`nue_score`).
Regenerating is Bee-only and costs ~1.6 h for the two data samples and ~6.5 h
for the MC campaign — not yet done.

## Counting corrected (2026-08-27): 12.4×, not 5.8×

Found while testing the `mc.json` fix. Two beam-on pilot events showed the
no-candidate marker despite having "non-stub" 211 kB `tracking-pr.root` files.
Opening them: **6 trees, `T_rec_charge` with 0 entries, `kine_reco_Enu` = 0.00,
`numu_score` = −1.9417.** The tagger ran and wrote a verdict but found no main
vertex, so `T_tagger`'s 1216 branches are booked with nothing behind them.

**File size cannot distinguish that from a real reconstruction** — both are
~211 kB and up. The earlier claim that "size alone is a reliable index of 'the
tagger accepted this event', verified against a hand scan" was wrong: it holds
on MC, where the hand scan checked it, and fails on data.

Recounted on `T_rec_charge.GetEntries() > 0`:

| sample | size-based (reported) | correct | booked-but-empty |
|---|---|---|---|
| MC | 5,960 = 45.1% | **5,813 = 44.0%** | 147 |
| beam-on | 434 = 43.4% | **421 = 42.1%** | 13 |
| beam-off | 75 = 7.5% | **34 = 3.4%** | 41 |

Beam-off was over-counted by more than a factor two, because off-beam events far
more often get a tagger verdict with no vertex. **The corrected discrimination
is stronger than first reported — 12.4× and 23σ, not 5.8× and 20σ** — but the
published numbers were wrong either way, and the dataset guide told readers to
filter on file size. Both are now corrected, and `count_reco.py` ships with
issue 16's scripts.

## Caveats

- **The candidate rates are configuration-dependent.** The 42.1% / 3.4% split is
  a strong relative statement — same chain, same config, both samples — and that
  is what makes it a good sanity check. The *absolute* rates are not production
  numbers; see the next point.
- **The `#17` operating-point gap applies here too.** This ran the same
  pre-flip PR configuration as issue 16: 160 knobs that Xin's 2-step chain sets
  are at default, 139 of them on `TaggerCheckNeutrino`. So the 43.4% candidate
  rate, `T_tagger`, `T_kine` and `kine_reco_Enu` are **this configuration's**,
  not SBND production's. Requested explicitly as "same configuration as
  issue-16".
- Validation output, not production. No stability guarantee.
- `nue_score` is a floor at −15.00 for most candidates (measured on MC); expect
  the same here.
