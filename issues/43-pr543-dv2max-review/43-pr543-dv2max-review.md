# Issue 43: review and validate WCT PR #543 (DV2-MAX neutrino vertexer)

- PR: https://github.com/WireCell/wire-cell-toolkit/pull/543, `dsnehadri:dv2-max-vertexer` → `master`, head `feb3ddeb`, 4 commits, base `b7bd2a1a` (= master today).
- Tracking: https://github.com/HaiwangYu/wire-cell-toolkit-ai-helper/issues/43
- Work area: `/exp/sbnd/data/users/yuhw/production-prep/pr543-review/` (lists, setup, runner, comparator, outputs).

## The request (owner, 2026-11-02)

**Questions:**
1. Can the original uboone-model DL vertexing still be used for comparison after this PR?
2. Was the Python-standalone vs Wire-Cell-integrated inference consistency tested? Check it again here.
3. What is the inference CPU and memory cost, compared with the old uboone model?

**Plan of the review:**
- **Samples:** 100 MC CV and 100 MC nueCC events, plus the real-data nueCC and NC events of `sbnd-wirecell-production/validation-xin/README.md`.
- **Metrics:** the DL vertex, and the reco numu/nue scores.
- **Methods to compare:** current master (the uboone model); the uboone model after the PR (`original`); and the PR's `dv2_snap`, `dv2_split` and `dv2_split_move`.
- **Load:** interactive runs on sbndbuild03, using < 60 % of its CPU and memory.
- **Afterwards:** in the review comment, suggest moving the models (`cfg/dv2max/r7_cloud/`) to wire-cell-data `uboone/dsnehadri/`.

**Clarifications (owner, 2026-11-02):**
- **MC sample:** Xin's evaluation MC (`validation-xin` `mc-cv`/`mc-nuecc`) is entirely in r7: all 154 CV and 225 nueCC files are in r7's unit lists. DV2-MAX `r7_cloud` was trained on folds 1–4 of the r7 DL-vertex dump (`bundle.json` `trained_on_folds: [1,2,3,4]`), so about 80 % of those events were training events. The MC therefore comes from **fg1 files that are in neither r7 nor r8**, so DV2-MAX has certainly never seen them.
- **Real data:** `nuecc48` (48 hand-scanned nueCC candidates) and `ncpi0` (19 NC-sideband events).

## Setup

| arm | build | vertexing |
|---|---|---|
| `master` | the production `opt`: toolkit `sbnd-wc-flatcaf` `4b6853d4` = master `b7bd2a1a` + #39 flat tree + #41 truth match | the uboone SCN net (`uboone/scn_vtx/t48k-m16-l5-lr5d-res0.5-CP24.pth`) and the original chain |
| `pr-original` | `opt-pr543`: the same branch + PR #543 (local branch `pr543-review` = merge `58e99669`, never pushed) | `vertex_method=original` |
| `pr-dv2_snap`, `pr-dv2_split`, `pr-dv2_split_move` | `opt-pr543` | `vertex_method=dv2_*` (`dv2_split_move` is the PR's SBND default) |

- **The merge** of the PR into `sbnd-wc-flatcaf` had 2 config conflicts (`sbnd-pr-stage.jsonnet`, `wct-pr.jsonnet`): our `flat_tree`/`truth_match`/`blob_truth` arguments next to the PR's `vertex_method`/`dv2_bundle`. Both sides were kept.
- **The build:** worktree `/exp/sbnd/app/users/yuhw/wct-pr543`, the production configure line with `--prefix=/exp/sbnd/app/users/yuhw/opt-pr543` (plus `CXXFLAGS=-DSPDLOG_FMT_EXTERNAL`), `wcb install`.
- **Run environment for the PR arms (`setup-pr543.sh`):** the production setup with whole path entries swapped: `opt` → `opt-pr543` and the toolkit `cfg/` → the worktree's.
- **Python:** the embedded interpreter is Python 3.9.15. numpy 2.0.2 and torch 2.6.0 come from the uboone scn product, and scipy 1.13.1 from the wire-cell-python venv. lightgbm was missing: **lightgbm 4.6.0** + threadpoolctl were installed with `pip --target /exp/sbnd/app/users/yuhw/pyenv-dv2`; 4.6.0 is the newest with a glibc-2.17 wheel, while the PR used 4.7.0.
- **Step 2 only, for MC:** every arm runs step 2 (`wct-pr.jsonnet`) from the same fg1 step-1 `qlpctree.tar.gz`. The PR changes nothing before the vertex step. The real-data files need step 1 once (production build).
- **Settings:** the same as production (`dl_vtx_dump`, `flat_tree`, `truth_match` on MC), 1 thread, `DV2_STRICT=1`, and `DV2_HOOK_LOG` (one record per DV2 call).
- **Tools (`pr543-review/`):**
  - `run-step2.sh <qlpctree> <outdir> <sim|data> <arm>` records `/usr/bin/time -v` and the log;
  - `compare-arms.py` compares two runs' `tracking-pr.root` value by value.

## Samples

| sample | source | pairs / files | events |
|---|---|---|---|
| MC CV | fg1 `OK` pairs not in r7/r8, seeded random (20261102); `lists/mc-cv.tsv` | 8 | 100 |
| MC nueCC | the same; `lists/mc-nuecc.tsv` | 10 | 109 |
| data nueCC | `sbnd-gen2-data/nuecc-lynn/filtered-reco1/data_filtered_decoded_reco1-fe6033f3-…_eventidfiltered_frameshift.root` | 1 | 48 |
| data NC | `sbnd-gen2-data/nc-sideband-lynn/filtered-reco1/nc-sideband_filtered_frameshift.root` | 1 | 19 |

## Answers

All 5 arms × 27 inputs (8 MC CV pairs / 100 events, 10 MC nueCC pairs / 109 events, 6 + 3 data slices / 48 + 19 events).

**Crashes:** 4 of 135 runs crashed in step 2 (`pr-original` 1, `pr-dv2_snap` 3).
- All were **intermittent**: each rerun twice; the 3 `dv2_snap` inputs succeeded 2/2, and the `pr-original` data slice 1 of 2 (`master` passed it).
- They are the known step-2 crash family (after "deghosting" in `TaggerCheckNeutrino`, RSS 4.1–4.5 GB; one in `TrackFitting`), and are not caused by any vertex method.
- The failed runs are kept in `runs-failed/`; the successful retries are used.

### Q1: the original uboone model after the PR — yes, unchanged

- **Config:** with `vertex_method=original` the PR branch compiles `wct-pr.jsonnet` byte-identically to production (md5 `a30b5d3164ab`, with `dl_vtx_dump`, `flat_tree` and `truth_match` on). The PR's default `dv2_split_move` differs only by `vertex_method`, `dv2_bundle`, and `dl_weights` = `dv2_split_move:dv2max/r7_cloud/bundle.json`.
- **Output:** `pr-original` vs `master`, value by value on every tree of every `tracking-pr.root` (`compare-arms.py`): **identical in all 27 inputs: 276 events, 4,965 trees, 920,419 branch arrays**. The only difference is `Trun.wct_version` and its flat-tree copy, which hold the build name.
- **Metrics:** identical to `master` (all tables below).
- **Caveat:** `original` is not the PR's SBND default (`dv2_split_move` is). To keep the uboone model, pass `--tla-str vertex_method=original` (2-step `wct-pr.jsonnet`, per-event `wct-pr-perevt.jsonnet`, or the 1-step lib).

### Q2: standalone vs in-chain inference — identical (228 / 228)

- **What the PR did:** replayed the r7 fold-0 export through the Python function (`validate_r7.py`). It did not compare the in-chain result with standalone Python for the same calls.
- **Here:** every in-chain DV2 call (229 per DV2 arm) was replayed standalone, from its dumped inputs through `DV2_Vertex.DV2_Vertex` in the same Python environment (`dv2-standalone.py`):
  - the cloud is `T_dlvtx_cloud` (x, y, z, q as float32, in `ipoint` order);
  - `n_vertex_rows`, `q_scale`, `q_offset` and the traditional vertex come from `T_dlvtx_call`.
- **Result:** compared with the in-chain record (`DV2_HOOK_LOG`), **all 228 calls with a prediction are identical**: max 1.6e-5 cm (float32 rounding; median 4.4e-6 cm), calibrated score equal to 3e-8. The 229th call is a 2-point cloud with no prediction on either side. The same holds in all three DV2 arms.
- **Correction (2026-11-03):** a first replay reported 2 / 228 calls off by 0.09 and 0.22 cm. That was my replay's bug, not a difference inside `wire-cell`.
  - When a candidate has no traditional vertex, the chain passes `trad = NaN`, and DV2-MAX then has no `tag_nu`. The dump stores this as `trad_valid = 0` with `trad_x/y/z = 0`.
  - The first replay passed `(0, 0, 0)`: a fake traditional vertex at the origin. It changed the tag-distance features (`pr_prox`, `cand_desc`, `event_summary`), hence the ranker's candidate set and its pick.
  - Exactly 2 of the 229 calls have `trad_valid = 0`, and they are the 2.
  - Found by capturing every intermediate of the call in-chain and standalone, with a `sitecustomize.py` that wraps `Vertexer.run(with_records=True)` (`scripts/dv2-sitecustomize.py`). Inputs, features, pass-1/pass-2 CNN records, ranker rows and scores were compared stage by stage: the first difference was in the features.
  - With the replay passing NaN when `trad_valid = 0`, every call matches. The pass-1 CNN outputs agree to 1e-7 (float noise, no effect).
- **Note for the PR:** a replay from the dump must honour `trad_valid`; the dump writes 0, not NaN, for a missing traditional vertex.
- **lightgbm:** 4.6.0 here, with the ranker trained and saved by 4.7.0. It loads without warnings, and in-chain and standalone use the same 4.6.0. The PR's fold-0 parity test (`validate_r7.py`) needs the r7 export (on Eagle) and was not rerun here.

### Q3: cost

All runs at 1 thread (`OMP`/`MKL`/`OpenBLAS`/`DV2_THREADS` = 1); one `wire-cell` process per input file, as in production.

**Is the model loaded per event?** No: once per `wire-cell` process. Step 2 runs one process per input file, as in production: the 2-step chain's `wct-pr.jsonnet` reads all events of a qlpctree; the 1-step lar job loads once per job.
- **Here:** 27 loads for 276 events (one per file, about 10 events and 8.5 DV2 calls per file).
- **Load breakdown, warm file cache:** about 4.8 s (`import numpy` 0.3 s, `import torch` 2.9 s, `import dv2max_vertexer` 0.4 s, model load and sha256 check 1.3 s).
- **Cold cache:** when 24 processes started at once and read torch from CVMFS, it took 16–23 s.
- **Totals (`dv2_split_move`, 27 runs):** loads 193 s, inference 145 s, against 3,234 s of step-2 CPU. That is **6 % for loading, 4.5 % for inference**.
- **The uboone model also loads once per process:** master's first vertex call takes about 5.2 s (torch import + SCN net), its later calls about 20 ms. So per process the two models cost about the same to load; they differ per call (0.63 s vs 0.02 s).
- **Per-event mode** (`wct-pr-perevt.jsonnet`, one process per event): both models would pay about 5 s per event, against about 11.7 s (dv2) or 16 s (master) of step-2 CPU per event. That would be a large overhead (+40 %) for either model, and cold-cache stalls would make it worse. For production, keep several events per process (as the 2-step chain does). The PR's README suggests the same.

**Vertex step per call** (`TaggerCheckNeutrino timing: overall main vertex took`):

| | master / original (uboone SCN) | dv2_* (DV2-MAX) |
|---|---|---|
| calls (27 runs) | 462 (2 per candidate: the dual chain) | 231 (1 per candidate; 229 DV2 calls) |
| per call, median | 21 ms | 630–645 ms |
| per call, p90 | 49–52 ms | 5.4 s (the first call of each process) |
| first call of a process | ~5.4 s (net load) | ~9 s (imports: torch 2.7 s, `dv2max_vertexer` 4.5 s, model load 1.2 s) |
| total vertex step, 27 runs | 166 s | 343–354 s |

**Whole step 2:**

| | master | pr-original | dv2_snap | dv2_split | dv2_split_move |
|---|---|---|---|---|---|
| CPU, 27 runs | 4,442 s | 4,421 s | 3,182 s | 3,210 s | 3,234 s |
| CPU vs master, median per run | | +0.3 s | −44 s | −41 s | −40 s |
| peak RSS, median | 1,537 MB | 1,531 MB | 1,718 MB | 1,727 MB | 1,714 MB |
| peak RSS, max | 2,508 MB | 2,498 MB | 2,666 MB | 2,662 MB | 2,663 MB |
| RSS vs master, median per run | | +2 MB | +166 MB | +163 MB | +166 MB |

- **The DL inference itself** is about 30× the uboone net per call (0.63 s vs 21 ms), plus about 9 s once per process.
- **But the whole step 2 needs about 28 % less CPU** with any dv2 method: the `original` vertex chain (dual chain, re-rank, snaps, `improve_vertex`, audit, conn3) does not run.
- **Memory:** about +165 MB per process (the two 80 MB models + lightgbm).

## Results (the same events for every arm)

**Vertex (MC):** `|final − truth|`, truth SCE-shifted into the reco frame, for the candidate whose cloud contains the truth vertex (within 3 cm); only events where every arm has that candidate.

| sample | n | master | pr-original | dv2_snap | dv2_split | dv2_split_move |
|---|---|---|---|---|---|---|
| CV, < 1 cm | 42 | 0.595 | 0.595 | 0.714 | 0.762 | **0.810** |
| nueCC, < 1 cm | 99 | 0.667 | 0.667 | 0.667 | 0.758 | **0.848** |
| all MC, < 1 cm | 141 | 0.645 | 0.645 | 0.681 | 0.759 | **0.837** |
| all MC, < 2 cm | 141 | 0.752 | 0.752 | 0.837 | 0.894 | **0.915** |
| all MC, median | 141 | 0.56 cm | 0.56 | 0.64 | 0.56 | **0.47** |

The PR's table, on 327 held-out r7 fold-0 events: 0.581 / 0.661 / 0.801 / 0.847.

**Selection (MC):** truth from `T_truth_nu` (largest-edep interaction, vertex in the active volume); the PR's cuts (generic ν = `numu_cc_flag ≥ 0`; ν_e: + `nue_score > 7`; ν_μ: + `numu_score > 0.9`).

| | master | pr-original | dv2_snap | dv2_split | dv2_split_move |
|---|---|---|---|---|---|
| ν_e CC selected as ν_e (n = 101) | 42 (0.416) | 42 | 49 (0.485) | 45 (0.446) | **51 (0.505)** |
| ν_μ CC selected as ν_μ (n = 30) | 23 (0.767) | 23 | 21 | 20 | 22 (0.733) |
| ν_μ CC + NC selected as ν_e (n = 52) | 0 | 0 | 0 | 0 | 1 (an NC event) |
| generic ν: ν_e CC / ν_μ CC / NC | 100 / 28 / 17 | the same | the same | the same | the same |

The statistics are small: ±5 points on ν_e, ±8 on ν_μ.

**Real data:** counts, then changes vs master (gained / lost):

| sample | | master | pr-original | dv2_snap | dv2_split | dv2_split_move |
|---|---|---|---|---|---|---|
| nueCC-48 (hand-scanned ν_e CC candidates) | ν_e | 38 | 38 | 38 | 38 | **41** |
| | ν_μ | 5 | 5 | 3 | 6 | 4 |
| NCπ0-19 (NC sideband) | ν_e | 1 | 1 | 1 | 1 | 1 |
| | ν_μ | 2 | 2 | 3 | 3 | 2 |
| changes vs master (both samples) | | | none | ν_e +3/−3, ν_μ +1/−2 | ν_e +4/−4, ν_μ +5/−3 | ν_e +5/−2, ν_μ +1/−2 |

## Metrics

- **Vertex:** per MC event, the candidate whose cloud contains the truth vertex (within 3 cm, as in #35 `dlvtx-truth-eval.py`); then `|final − truth_reco|` from `T_dlvtx_call`. Report the fraction < 1 cm and < 2 cm, and the median.
- **Scores:** `T_tagger` `nue_score` and `numu_score` per event; selections as in the PR (generic ν + `nue_score > 7`; `numu_score > 0.9`). On data, the counts selected per method and the event-by-event changes.
- **Crashes and fallbacks:** rc, `DL vertex failed`, DV2 WARN fallbacks.

## Review comment, to post after the validation

- The answers to Q1–Q3.
- Suggest moving the models (`cfg/dv2max/r7_cloud/`: `pass1.pt`, `pass2.pt`, about 80 MB each, plus the ranker and isotonic files) to wire-cell-data `uboone/dsnehadri/`, resolved through `WIRECELL_PATH` like the SCN weights.

## Log

- 2026-11-02:
  - PR merged into a local review branch; 2 config conflicts resolved; built to `opt-pr543`; lightgbm 4.6.0 env.
  - Samples chosen. Smoke test: Q1 identical; DV2 runs in-chain.
  - Data step 1: 9 slices, FrameShift applied.
  - Matrix: 5 arms × 27 inputs, 24 in parallel, my share ≤ 22 cores and ≤ 40 GB.
- 2026-11-03:
  - Matrix done; the 4 intermittent crashes were rerun.
  - Metrics; Q1 full compare: identical.
  - Q2 replay: first 226/228 exact. The 2 were traced to the replay passing (0,0,0) for a missing traditional vertex instead of NaN; fixed: 228/228 identical.
