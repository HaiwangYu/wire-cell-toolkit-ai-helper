# Issue 16 — 1-step img/clus/match/tag/**PR** over 1000 MC files (~13k events)

Repeat of [issue 11](https://github.com/HaiwangYu/wire-cell-toolkit-ai-helper/issues/11)
(`img-clus-match-tag`, 13,211 events, 2026-08-14) with the **pattern-recognition
chain switched on** — the Route A configuration built and verified in
[issue 13](https://github.com/HaiwangYu/wire-cell-toolkit-ai-helper/issues/13).

Output tree: `/exp/sbnd/data/users/yuhw/production-prep/img-clus-match-tag-pr-mc-1000file-2026-08-20/`

## What is different from issue 11

| | issue 11 (08-14) | issue 16 (08-20) |
|---|---|---|
| chain | img → clus → Q/L match → TGM/STM/FC | **+ `clus_pr`: 15-name pipeline, neutrino tagger, both BDT scorers** |
| DL (SCN) vertex | not exercised | **on** (`setup-dlvtx.sh`) |
| deliverables kept | `mabc.zip` only | **Bee zip + `tracking-pr.root` + `nugraph.h5`**, all three per event |
| RSE in filenames | no (see below) | **yes**, from `EventAuxiliary` |
| concurrency | 10 workers × 2 cores | 28 workers × 1 core (measured, §Concurrency) |

## Input — identical to issue 11

`files-1000.lst`, md5 `4dc75514e652bddf49e41459a5091080`, byte-identical to
issue 11's list. Sample
`aurora/mc/v10_14_02_03/prodgenie_corsika_proton_rockbox0p1_sbnd/Gen2_2026/CV/reco1`,
13 events/file → **~13,200 events**.

Same scope caveat as issue 11: these files carry production `dnnsp` and **no
`raw::RawDigit`**, so this run exercises nothing in NF/SP. It measures
clustering + matching + tagging + pattern recognition on production signal
processing.

## Repository state (this is the configuration being run)

Captured 2026-08-20, after merging `origin/apply-pointcloud`.

| repo | path | branch | HEAD | clean? |
|---|---|---|---|---|
| wire-cell-toolkit | `/exp/sbnd/app/users/yuhw/wire-cell-toolkit` | `ap-yuhw` | `40cb45fc` | clean |
| wcp-porting-img | `/exp/sbnd/app/users/yuhw/wcp-porting-img` | `main` | `4afb6f2` | clean |
| larwirecell | `.../larsoft-wct036/v10_14_02/srcs/larwirecell` | `dev-v10_14_02_02` | `a02a1a4` | clean |
| wire-cell-data | `/exp/sbnd/app/users/yuhw/wire-cell-data` | `master` | `9e2f4b8` | +`uboone/weights/XGB_nue_seed2_0923.xml` (untracked, **required** — the issue-13 G1 fix) |
| sbndcode | `/exp/sbnd/app/users/yuhw/sbndcode` | `wcp-porting` | `2260962f0` | clean |

### The merge, and what it cost

`origin/apply-pointcloud` was 47 commits ahead. Three files conflicted, all of
them ones the issue-13 work had touched:

| file | resolution |
|---|---|
| `cfg/.../sbnd/clus.jsonnet` | union: their `bee_flash_pred_min` + our `rse_from_metadata` |
| `clus/inc/.../MultiAlgBlobClustering.h` | union: our `oft_out` (opflash_time column) + their `tf_in`/`do_reset` (doc pr/94 Phase 4b) |
| `clus/src/MultiAlgBlobClustering.cxx` | 3 hunks — see below |

The `.cxx` conflicts were all in `fill_bee_pf_tree`, where doc pr/94 added
**per-bundle** neutrino candidates while issue 13 had added the **truth-tree
graft**. Naively taking either side loses a feature, and taking both
mechanically leaves a real bug: upstream's per-bundle caller concatenates the
bundles and calls `set_particles(all)` **directly**, which bypasses the graft, so
`mc.json` would silently lose its truth half whenever `nu_per_bundle` is on.

Resolved by extracting the graft into a new shared
`MultiAlgBlobClustering::pf_set_particles()` that both the legacy tail and the
per-bundle caller go through. Also kept issue 13's removal of upstream's
`if (!tf) continue;` — that early-out is exactly the regression that dropped
`mc.json` for 6 of 10 events on the run-925-23 pilot.

**Build trap hit and recorded:** the first WCT build was accidentally run
*outside* the SL7 container, so ~230 objects compiled against the host's glibc
2.34. The container build then reused them and `libWireCellUtil.so` came out
referencing `__libc_single_threaded`, which SL7's glibc 2.17 does not export.
The symptom was not a build error but a **plugin-load failure at run time**
(`Unable to load ... liblarwirecell_Tools_WCLS_tool.so`). Fixed with
`./wcb clean` + a full in-container rebuild (11m21s), then relinking larwirecell
and re-copying the four `.so` into `opt`. `NeutrinoTaggerInfo.h` grew 44 lines
in this merge, so the larwirecell rebuild was needed regardless — that struct is
the known taginfo-ABI landmine.

## Harness

`scripts/run-harness.sh` — one `lar` process per event, each in its own cwd
(concurrent `lar` jobs otherwise collide on art's MemoryTracker/TFileService
sqlite files). Work-stealing over the file list via a `flock`-guarded cursor.
`MAXEV=1` caps to one event per file, which is how the pilot gets 10 events from
10 different files.

Four changes from the issue-11 harness:

1. **`enable_tracking_root: "true"` is safe here.** The fcl warns that the
   tracking writers share one filename under `RECREATE`+`UPDATE` and corrupt
   silently with `-n > 1`. One event per process makes that moot.
2. **RSE from `EventAuxiliary`, not the log.** Issue 11 grepped
   `run: N subRun: N event: N` out of `lar.log`; that regex matched **2 of
   13,217 rows**, i.e. it never worked and nobody noticed because the column was
   merely blank rather than wrong. `rse_list.py` now reads the RSE list with
   PyROOT in the same open that counts the events (3.4 s/file), so every
   archived file is named for the event it holds and nothing depends on log
   formatting.
3. **Peak RSS per event** via `/usr/bin/time -v`, plus `sample-mem.sh` for the
   *concurrent* sum — the number that actually decides how many jobs fit.
4. **Per-event silent-failure audit.** `check-pr-run.sh` runs in the work dir
   before the deliverables are moved out (one of its checks looks for
   `tracking-pr.root` next to the log) and its verdict is a CSV column. It
   catches the DL-vertex geometric fallback, an unregistered RSE attacher, an
   unlabeled pass-through, and blob loss — all of which leave `rc=0` and a
   plausible-looking result.

### Output layout

```
bee/bee_r<run>_s<sub>_e<evt>.zip                  20 Bee layers + merged mc.json
tracking-pr/tracking-pr_r<run>_s<sub>_e<evt>.root Trun/T_tagger/T_kine/T_rec_charge/...
nugraph/nugraph_r<run>_s<sub>_e<evt>.h5           one dataset, RSE-keyed internally
summary.csv                                       one row per event
logs/{fail,missing,audit}_*                        only for events that need looking at
```

`summary.csv` columns: `file_idx, event_idx, run, subrun, event, rc, wall_s,
peak_rss_kb, bee_bytes, trackpr_bytes, nugraph_bytes, audit, file`.

## Smoke test — 1 event

`r713/s74/e3`, rc=0, audit ok, 46 s, peak RSS 2.34 GB. All three deliverables
present and substantive:

- **Bee zip** 3.81 MB, 21 entries = 20 layers + exactly one `mc.json` (no
  duplicate `channel-deadarea`, i.e. the issue-13 G4 dead-area guard holds).
- **`mc.json`** carries both halves: truth `numu RES CC Etot 1821.6 MeV` at top
  level plus `reco nu 107.5 MeV numu -1.715 nue -15.000`. Real BDT scores, not
  the `0.000` that the pre-fix visitor ordering produced — so the merge did not
  regress the graft.
- **`tracking-pr.root`** 7 trees, `Trun` RSE = **713/74/3** (the issue-13 G3
  fix survived), `T_tagger` 1216 branches with `numu_score=-1.7148`,
  `T_kine.kine_reco_Enu=107.46` — consistent with the Bee text.
- **`nugraph.h5`** dataset `713_74_3__rec-lab-apa0-1`: 3044 space points with
  `pos`, 6 features, `y_semantic`, `y_instance`, 7490 edges.

## Pilot — 10 events, 10 concurrent

Event 0 of each of the first 10 files. **10/10 rc=0, 10/10 audit ok**, all 30
deliverables present.

| metric | value |
|---|---|
| wall per event | mean **44.5 s**, min 29 s, max 57 s (1 core) |
| peak RSS per job | mean **2.04 GB**, max 2.27 GB |
| concurrent total RSS at 10 jobs | max **18.9 GB** → 1.89 GB/job |
| Bee zip | mean 4.61 MB |
| `nugraph.h5` | mean 1.06 MB |
| `tracking-pr.root` | mean 0.113 MB — **but see below** |

### Only 4 of 10 events have PR content

`tracking-pr.root` comes out at two sizes: **8.2 kB** (6 events) or
211–404 kB (4 events). The small ones contain `Trun`, `T_bad_ch`, `T_proj`
only — no `T_tagger`, `T_kine` or `T_rec_charge`. That is the neutrino tagger
declining the event, which is the expected majority outcome, not a failure:
`Trun` still carries the correct RSE, so the file positively distinguishes
"ran, no candidate" from "did not run". Budget on **~40% of events carrying a
reconstructed candidate**.

The nugraph truth labels are consistent with this: the four events with PR
content are among those with the most neutrino-labelled space points
(1150, 262, 103, 10 of a few thousand), though the correspondence is not exact —
`s52_e1` has 65 nu points and no candidate.

### Bee

- full chain, 10 events: <https://www.phy.bnl.gov/twister/bee/set/958ac47a-c5b7-49ac-8f06-6794dff7986a/event/list/>
- `nugraph.h5` space points, same 10 events: <https://www.phy.bnl.gov/twister/bee/set/58769843-3b83-4a66-864e-911ae74a4d57/event/list/>

Both verified served at Bee's own endpoint (10 events each; event 0's merged
`mc.json` fetched back). Bee event index N = `summary.csv` row N ordered by
`file_idx`. The nugraph set is built by `scripts/nugraph_to_bee.py`, which is
`sbnd/TensorSetLabeler/h5_sp_to_bee.py` plus an outer loop over files (this
campaign writes one h5 per event, not one h5 per job). Colouring: `q` =
nu(1)/cosmic(0)/ghost(-1) from `y_semantic`, `cluster_id` = `y_instance` (truth
trackid).

## Hand scan of the 10 pilot events (owner, 2026-08-20)

Verdict: **passes the sanity check** — proceed to the full run.

| Bee evt | RSE | PR content | owner note |
|---|---|---|---|
| 0 | 713/74/3 | 211 kB | no in-beam, but a nu was reconstructed |
| 1 | 713/35/3 | stub | — |
| 2 | 713/0/11 | 230 kB | w-prolonged cosmic |
| 3 | 713/68/2 | stub | — |
| 4 | 713/59/9 | stub | w-prolonged cosmic |
| 5 | 713/5/4 | stub | — |
| 6 | 713/51/3 | 404 kB | very good case with pi0 |
| 7 | 713/70/3 | 235 kB | selection good, but pi0 not correct |
| 8 | 713/40/2 | stub | — |
| 9 | 713/52/1 | stub | match OK, but too small? truth depo 142 MeV |

Two things fall out of cross-referencing the notes against the file sizes:

- **The four events with a reconstructed candidate are exactly the four the
  owner flagged as having reco** (0, 2, 6, 7). The stub/non-stub split is
  therefore a faithful index of "the tagger accepted this event", not an
  artifact of the writer.
- **Two of those four look like false positives.** Event 2 is a w-prolonged
  cosmic that was nonetheless reconstructed as a neutrino candidate, and event 0
  has no in-beam activity yet produced one (its truth is `numu RES CC` with
  Etot 1821.6 MeV but only **19.8 MeV deposited**). W-plane prolongation is
  [issue 10](https://github.com/HaiwangYu/wire-cell-toolkit-ai-helper/issues/10);
  events 2 and 4 both show it, so 2 of 10 events carry that defect and one of
  them converts it into a candidate. This is the thing to quantify on 13k events.
- Events 6 and 7 are genuine pi0 cases: 6 reconstructs well, 7 selects correctly
  but gets the pi0 wrong.

## Concurrency — owner chose 32 workers

Both stated constraints cannot be met at once, so the measurement decides:

| workers | sum-of-peaks | observed-concurrent scaling | verdict |
|---|---|---|---|
| 28 | 28 × 2.04 = **57.1 GB** | 28 × 1.89 = 52.9 GB | fits, with tail headroom |
| 32 | 32 × 2.04 = **65.3 GB** | 32 × 1.89 = 60.5 GB | **over 64 GB** on peaks |

The recommendation was 28, sized on sum-of-peaks because the pilot sampled no
tail event (issue 13 saw a 212 s clustering event, issue 11 a 950 s one).
**The owner chose 32**, and the run vindicates it: over the first 9 minutes at
32 concurrent jobs the sampled total RSS is **mean 51.0 GB, max 60.6 GB** — the
observed-concurrent column, not the sum-of-peaks column, and inside the 64 GB
budget. Peaks do not coincide across independent jobs, which is why sum-of-peaks
was the conservative bound rather than the real one. The host has 64 cores /
125 GB, so 64 GB was a courtesy cap on a shared box, not a hard limit.

## Projection for the full run

| | estimate | basis |
|---|---|---|
| events | ~13,200 | 13,211 in issue 11 |
| wall | **~5.8 h** at 28 workers | 13,211 × 44.5 s / 28 |
| disk | **~76 GB** | 5.78 MB/event × 13,211 |
| — Bee | 61 GB | 4.61 MB/event |
| — nugraph | 14 GB | 1.06 MB/event |
| — tracking-pr | 1.5 GB | 0.113 MB/event |

91 TB free on `/exp/sbnd/data`, so disk is not a constraint. For reference,
issue 11's Bee zips alone were 68 GB.

The wall estimate is a floor: the pilot's 10 events ran 29–57 s and contained no
tail. Issue 11's mean was 35.6 s with a 950 s max, so expect the distribution to
be wider than the pilot suggests.

## Status

- [x] merge `origin/apply-pointcloud` (47 commits, 3 conflicts), rebuild WCT + larwirecell
- [x] harness with per-event RSE naming, three deliverables, audit column
- [x] 1-event smoke — all three deliverables verified substantive
- [x] 10-event pilot — 10/10 ok, timing/memory/disk measured, both Bee sets up
- [x] hand scan of the 10 events — passes, see above
- [x] full 1000-file run — **complete**, 6h29m, 13,213/13,217 events (99.97%)

## Full run — launched 2026-08-20 22:42 CDT

32 workers x 1 core, `scripts/sample-mem.sh` recording total RSS to `mem.txt`
every 30 s for the duration.

First 9 minutes:

| | measured | vs pilot projection |
|---|---|---|
| throughput | **32.4 events/min** | — |
| ETA (13,200 events) | **~6.8 h** (finish ~05:30 CDT) | 5.8 h projected at 28 |
| mean wall/event | 54.8 s | 44.5 s in the pilot |
| concurrent RSS | mean 51.0 GB, max 60.6 GB | 60.5 GB predicted at 32 |
| rc != 0 | **0** of 296 | — |
| audit FAIL | **0** of 296 | — |
| tracking-pr stubs | 51% | 60% in the pilot |

Two revisions to the pilot's projections, both from a larger sample:

- **Per-event wall is 54.8 s, not 44.5 s.** The pilot took only event 0 of each
  file; the bulk run takes every event, and 32-way single-core contention is
  worse than 10-way. ETA moves from 5.8 h to ~6.8 h.
- **~49% of events carry a reconstructed candidate**, not the ~40% the pilot
  suggested (51% stubs vs 60%). Revises the `tracking-pr.root` volume estimate
  upward, though it stays small in absolute terms.

## Full run — COMPLETE

`2026-08-20 22:42:12` → `2026-08-21 05:11:36` CDT, **6 h 29 m**, 32 workers × 1 core.

| | result |
|---|---|
| events | **13,213 ok / 13,217 attempted = 99.97%** |
| deliverables | 13,213 × 3 — Bee zip, `tracking-pr.root`, `nugraph.h5` |
| zero-size or missing deliverables | **0** |
| RSE collisions | **0** (13,213 unique RSE over 13,213 files) |
| audit FAIL among successes | **0** — the 4 audit fails are exactly the 4 `rc != 0` |
| coverage | 16 runs, 1000 distinct run/subrun pairs |
| total cost | 192.2 core-hours |

**No silent failures.** The audit column fired on nothing except the four hard
crashes, so across 13,213 events there was no DL-vertex geometric fallback, no
unregistered RSE attacher, no unlabeled pass-through and no blob loss. And
because the filenames are RSE and all 13,213 are unique, nothing silently
overwrote anything — the failure mode that a fixed-filename scheme would have
hidden.

### Wall time

| | s |
|---|---|
| mean | 52.4 |
| median | 48 |
| p90 | 68 |
| p99 | 118 |
| p99.9 | 414 |
| max | **2988** |

The distribution is tight through p99 and then has a long thin tail: 25 events
(0.19%) over 300 s, 7 over 600 s. The mean tracked the 9-minute estimate almost
exactly (52.4 vs 54.8 s), so the ETA was good — 6.5 h actual against 6.8 h
projected.

### Memory — 32 workers was correct

| | GB |
|---|---|
| mean over 709 samples at ≥30 concurrent jobs | **52.0** |
| max over the whole 6.5 h | **60.6** |

Never exceeded the 64 GB budget, and the max equals the max seen in the first 9
minutes, i.e. the ceiling was reached early and held. This settles the
28-vs-32 question: sum-of-peaks (65.3 GB) overestimates because peaks do not
coincide across independent jobs. **Size future campaigns on the sampled
concurrent sum, not on the sum of per-job peaks.**

### Disk — 84.7 GB (projected 76 GB)

| | actual | per event | projected |
|---|---|---|---|
| Bee | 67 GB | 5.41 MB | 4.61 MB |
| `nugraph.h5` | 16 GB | 1.25 MB | 1.06 MB |
| `tracking-pr.root` | 1.6 GB | 0.12 MB | 0.11 MB |

Both the Bee and nugraph means came in ~17% above the pilot, because the pilot
took only event 0 of each file and those happen to be lighter than the file
average. Max single event: 38.8 MB Bee, 9.4 MB nugraph.

### Reconstruction yield — 44.0% (corrected 2026-08-27)

**5,813 of 13,213 events (44.0%) carry a real reconstruction.**

This was first reported as 45.1% (5,960) using a `file size > 20 kB` filter.
That filter is wrong: a further **147 files are ~211 kB but empty** — the tagger
ran and wrote a verdict while finding no main vertex, so `T_tagger`'s 1216
branches are booked, `T_rec_charge` has 0 entries and `kine_reco_Enu` = 0.00.
Size cannot separate those from real reconstructions. The correct test is
`T_rec_charge.GetEntries() > 0` (`scripts/count_reco.py`).

The error was small here (147 of 13,213) but **large on beam-off data**, where
it more than doubled the apparent rate — see issue 18.

## The four failures

| file/evt | RSE | mode | in 08-14? |
|---|---|---|---|
| 196/11 | 719/77/35 | `vector::_M_range_check: __n (353) >= size() (353)` | **yes, identical index** |
| 224/1 | 714/44/10 | `vector::_M_range_check: __n (383) >= size() (383)` | **yes, identical index** |
| 684/7 | 471/18/33 | SIGSEGV, core dumped, during `apa0-0` clustering | **yes** |
| 932/0 | 718/51/3 | `vector::_M_range_check: __n (6) >= size() (6)` | **no — succeeded in 22 s** |

Three of the four are pre-existing and deterministic: they reproduce from issue
11 at the same (file, event) with the *same out-of-range index*, so they are
input-driven and independent of the PR chain. All three range-check throws have
`__n == size()` exactly — a one-past-the-end `.at()`, at three different sizes
(353, 383, 6), which suggests one bug reached by a common code path rather than
three unrelated ones.

**932/0 is genuinely new** — it completed in 22 s in issue 11 and now throws.
That is 1 new failure in 13,217 events (0.008%), attributable to either the PR
chain being on or the 47-commit merge. Worth a look, not worth blocking on.

### Why 4 failures here and 6 in issue 11

Not an improvement in the chain — a timeout change. Issue 11 used
`timeout 1800`; this harness uses `timeout 3600`. Issue 11's other three
failures (364/16, 470/4, 955/3) all **succeeded here**, taking 2512 s, 2988 s
and 2512 s. They were timeout kills, and their logs end with a normal timer
summary, which is why they showed no exception. Anything at this scale needs a
timeout above the p99.9 of ~414 s by a wide margin; 1800 s was not enough.

## Config audit vs Xin's 2-step chain (2026-08-21)

Done after the run, by compiling both chains with `wcsonnet` and diffing the
component `data` blocks — not by reading jsonnet. Full list:
[`config-diff-1step-vs-2step.md`](config-diff-1step-vs-2step.md).

Method note: the 2-step must be compiled with the production `pipeline_names`
TLA that `run_pr_chain_batch_isolated75base.sh` passes. Compiling its bare
defaults shows a phantom 10-vs-15-stage pipeline difference that does not exist
in the real chain — the first version of this audit made exactly that mistake.

### The shared files are genuinely shared

`sbnd_xin/clus.jsonnet` is a **10-line re-export** of
`pgrapher/experiment/sbnd/clus.jsonnet`, and `sbnd_xin/wct-pr-perevt.jsonnet` is
a one-line re-export of the in-tree file. Both chains therefore compile the same
`experiment/sbnd/clus.jsonnet` and the same `common/clus.jsonnet`, the latter
being imported from exactly one place. **No divergence is possible in either
clus jsonnet** — every difference comes from the entry point.

### Clustering half: matches

| instance | verdict |
|---|---|
| `apa0-0`, `apa1-0` | identical but for `bee_sink` / `rse_from_*` (1-step only) and `save_deadarea` false-vs-true |
| `clus_all_apa` | identical on all 23 shared keys; Xin additionally sets `bee_flash_pred_min: 0` |
| `clus_pr` pipeline | same 15 stages, same order |

`save_deadarea=false` and the `clustering-pr` set name are deliberate — both
follow from sharing one Bee zip (issue-13 G4); writing dead area from two nodes
is what produced the duplicate `channel-deadarea` entries that fix removed.

### PR half: 160 knobs missing

`wct-pr-perevt.jsonnet` passes **351** named arguments to `clus_maker.pr()`.
Our 1-step passes **7**. Compiled effective difference: **160 knobs**.

| component | missing knobs |
|---|---|
| `TaggerCheckNeutrino:pr` | **139** — incl. 39 `shower_*`, 24 `mvga_*`, 10 `kine_*`, `fit_exclusion`, `mvfit_robust`, `nu_per_bundle`, `neutrino_type_bitmask`, `fiducial`+`fv_tolerance` |
| `ClusteringProtectBundle:pr` | 5, plus `graph_name` = `relaxed` vs `relaxed_strict_img_2d_rescue_long_wtrack` |
| `CreateSteinerGraph:pr`, `:prrefresh` | 3 each |
| `ClusteringUnmergeBundle:pr` | 2 (`require_provenance`, `restore_demoted_mains`) |
| `TaggerCheckTGM:pr` | 2 |
| `UbooneTaggerOutputVisitor:pr` | 2 |
| `TaggerCheckFC:pr`, `TaggerCheckSTM:pr`, `ClusteringExamineBundles:all` | 1 each |

This is **by design on Xin's side and an oversight on ours.**
`wct-pr-perevt.jsonnet:568` states it outright: *"Per doc 68 the SBND operating
point lives HERE only; clus.jsonnet's clus_pr()/pr() function defaults stay
null."* The 1-step bypasses that entry point, so it silently gets the
conservative defaults. Worse, the 1-step jsonnet contains a comment claiming to
"Match the SBND production operating point ... mirror it here" — for
`iso_endpoint` alone. One knob of roughly 160 was mirrored, and the comment
reads as though the operating point had been handled.

These knobs are default-OFF in C++ *specifically* so config selects them, so
absent means pre-flip behaviour, not "same as production".

### Consequences for the 13,213-event dataset

- `T_tagger`/`T_kine` were computed with the pre-flip tagger; the 10 `kine_*`
  knobs feed `kine_reco_Enu` directly.
- `nu_per_bundle=true` books per-bundle `T_tagger` branches in Xin's chain, so
  this dataset is **not schema-compatible** with a production 2-step `T_tagger`.
- The 45.1% candidate yield and the hand-scan false positives are **not**
  production numbers. Several missing knobs
  (`shower_bragg_protect_start_segment`, the `*_straight_guard` family,
  `shower_nv_bridge_track`) target exactly the misclassification the scan saw.
- The clustering half matches, so `T_rec_charge` geometry and the nugraph inputs
  are the least affected.

### This answers T1

Issue 13's task T1 was "verify Route A against Xin's original 2-step chain". The
audit answers it without running anything: the two chains agree on imaging,
clustering and matching, and diverge on the PR operating point by 160 knobs. T1
was the right task and the answer is that Route A was **not** equivalent.

### Proposed fix (not applied)

Tracked separately in [issue #17](https://github.com/HaiwangYu/wire-cell-toolkit-ai-helper/issues/17), with a reproducible audit script as the acceptance gate.


Factor the operating point out of `wct-pr-perevt.jsonnet` into a single jsonnet
that both entry points import. Copying 351 arguments into the 1-step would work
today and drift again tomorrow — copying is how this happened. After the fix,
re-run the 10-event pilot and diff the compiled configs to zero before
regenerating the 13k.

## Open items

1. ~~**`nugraph.h5` keyed `..._rec-lab-apa0-1`** — does it cover only apa0?~~
   **Resolved 2026-08-21: naming artifact only.** Sampled x ranges run −234 to
   +234 cm, roughly balanced across the cathode, so the graph spans both APAs.
   `semantic_classes` is still only `['nu','cosmic']`, and every event is
   labelled `train`.
2. **`nue_score = -15.000`** on the smoke event looks like a floor/sentinel
   rather than a score. Harmless for this run; check before anyone cuts on it.
3. **`vector::_M_range_check` with `__n == size()`** on 3 events (196/11,
   224/1, 932/0) and a SIGSEGV on 1 (684/7). The first two reproduce from issue
   11 with identical indices, so they are a standing bug in the chain rather
   than a scale artifact — 4 reproducible test cases now exist for whoever
   fixes it.
4. **Issue 13 T1 is still open** — Route A has not been verified against Xin's
   original 2-step chain. This campaign runs Route A on 13k events regardless;
   T1 remains the thing that would validate it.
