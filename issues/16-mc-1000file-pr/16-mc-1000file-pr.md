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

## Concurrency — 28 workers, not 32

Both stated constraints cannot be met at once, so the measurement decides:

| workers | sum-of-peaks | observed-concurrent scaling | verdict |
|---|---|---|---|
| 28 | 28 × 2.04 = **57.1 GB** | 28 × 1.89 = 52.9 GB | fits, with tail headroom |
| 32 | 32 × 2.04 = **65.3 GB** | 32 × 1.89 = 60.5 GB | **over 64 GB** on peaks |

Sized on sum-of-peaks rather than the observed concurrent sum, because the pilot
sampled no tail event — issue 13 saw a 212 s clustering event, and issue 11 saw
a 950 s one, neither of which is in these 10. 28 × 1 core costs ~13% wall
against 32 and keeps a 7 GB margin. The host has 64 cores / 125 GB, so 64 GB is
a courtesy cap on a shared box, not a hard limit.

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
- [ ] hand scan of the 10 events (user)
- [ ] full 1000-file run

## Open items

1. **`nugraph.h5` has one dataset per event keyed `..._rec-lab-apa0-1`**, even
   though the labeler sits on the all-APA node. Either the name is legacy or the
   graph covers only apa0 — worth confirming before this feeds training.
   `semantic_classes` also has only 2 entries.
2. **`nue_score = -15.000`** on the smoke event looks like a floor/sentinel
   rather than a score. Harmless for this run; check before anyone cuts on it.
3. **Issue 13 T1 is still open** — Route A has not been verified against Xin's
   original 2-step chain. This campaign runs Route A on 13k events regardless;
   T1 remains the thing that would validate it.
