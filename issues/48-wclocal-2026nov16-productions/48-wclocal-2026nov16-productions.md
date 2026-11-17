# Issue 48: productions WCLocal2026Nov16-Aurora and WCLocal2026Nov16-FermiGrid

GitHub: https://github.com/HaiwangYu/wire-cell-toolkit-ai-helper/issues/48. This issue is also the channel between the Claude Code agents (§9).

## 0. The request (Haiwang, 2026-11-16)

- Two productions:
  - **WCLocal2026Nov16-Aurora**, with the same inputs as aurora-r2 (Avinay's reco1);
  - **WCLocal2026Nov16-FermiGrid**, with the same inputs as fg1 (MC BNB CV, MC nueCC, beam-off), plus beam-on data from Run 1 and Run 3.
- Software: **WCT 0.38.0** and **larwirecell `sbnd-wc-flatcaf`**, the branch the recent productions and the PR #547 validation used (§1).
- **Before the full run**, a smoke/validation run on the real-data samples (nueCC-48 + NCπ0-19) must reproduce the PR #547 results on the same data.
- Check whether we can **start from the kept step-1 output (`ql`)**, and how much time that saves.
- **Two vertexing modes, both kept:** `dv2_split_move` and `dv2_snap`, both with the `aurora_space` model.
- Estimate the output size, the disk usable, and the wall clock (queue + running) for both sites.
- **Do not delete** aurora-r1, aurora-r2 or fg1.

**Decisions (Haiwang, 2026-11-16):**

| question | decision |
|---|---|
| larwirecell | `sbnd-wc-flatcaf` `ad5d9421`. `dev-v10_14_02_02` is 3 commits behind and lacks the `input_file` stamping, labeler `truth_detail` and `WCLS_INPUT_FILE`, which the 0.38.0 production job needs |
| "snap" | **`vertex_method=dv2_snap`** with `aurora_space` (the same model as split-move, placed at the nearest PR-graph vertex) |
| step-1 reuse | **Test, then reuse.** Rerun step 1 with 0.38.0 on a sample and compare with the kept tars array by array. If identical, run step 2 only; otherwise run from reco1 |
| two results | **One merged CAF per file with two Wire-Cell trees**: `recTreeWireCell` (`dv2_split_move`) and `recTreeWireCell_dv2snap` (`dv2_snap`) |
| beam-on | The same sets as before: Run 1 open-data FixedDev (1,817 files, 89,946 events) and Run 3 run3bnb (2,208 files, 109,487 events) |

## 1. Software pins

| component | pin |
|---|---|
| wire-cell-toolkit | **0.38.0**: tag `0.38.0` → `c935e30d` (= master `647b2733` + `version.txt`). Contains #544, #547 and #548 |
| larwirecell | `HaiwangYu/larwirecell` **`sbnd-wc-flatcaf` `ad5d9421`** (= `dev-v10_14_02_02` `189ad260` + `3b546511`, `73c79bc4`, `ad5d9421`) |
| wire-cell-data | master with `dv2max/sbnd/aurora_space` (wire-cell-data #8, merge `99c6497f`; `bundle.json` sha256 `51588842…`), plus the XGB/SCN weights the sites already add |
| DV2 Python | Python 3.9.15, numpy 2.0.2, torch 2.6.0 (scn product), scipy 1.13.1, **lightgbm 4.6.0 built for SL7** (Aurora: `products/dv2-extra-py39`; sbndbuild03: `pyenv-dv2`). **FermiGrid: must ship to the worker nodes** (§7, R1) |
| workflow | `HaiwangYu/sbnd-wirecell-production`: a new commit with the two-pass step 2 and the two-tree merge (§4) |
| sbndcode / container | v10_14_02_03 e26:prof (Aurora: Flare UPS; FNAL: CVMFS), SL7 image as in aurora-r2 / fg1 |
| env | `GODEBUG=asyncpreemptoff=1` in every step-2 run (ai-helper #45: the Go/ROOT SIGURG crash; Aurora's earlier step-2 crashes may be this class) |

**Step-2 TLAs:**
- **Both passes:** `dl_vtx_dump=true`, `flat_tree=true`, `truth_match=<sim>`, `dv2_bundle=dv2max/sbnd/aurora_space/bundle.json`.
- **The `dv2_split_move` pass** also has `dl_vtx_dump_space=true`, as aurora-r2 had: the training data.
- **The `dv2_snap` pass:** `dl_vtx_dump_space=false`. Its DL inputs are the same as the split-move pass's, and the space dump is per-event data, so a second copy is not needed.

## 2. Inputs (match aurora-r2 and fg1)

**Aurora** (= aurora-r2 = aurora-r1 inputs, Flare, `$Y=/lus/flare/projects/neutrinoGPU/yuhw`):

| sample | source | units | events |
|---|---|---|---|
| BNB CV | `abhat/sbnd/gen2-wct0319-bnb-1m-*`, `$Y/production-prep/bnb1m/full/pairs-all.tsv` minus the EMPTY units | 11,888 | 627,205 |
| nueCC | `abhat/sbnd/gen2-sbnd-ccnue-configL-300k-…`, aurora-r2 pair list | 61,252 | 268,865 |
| NC Δ-rad | `abhat/sbnd/gen2-sbnd-ncdeltarad-train-configL-…`, aurora-r2 pair list | 17,604 | 26,745 |
| **total** | | 90,744 | **922,815** |

**FermiGrid** (official Gen2 SAM; lists in `/pnfs/sbnd/persistent/users/yuhw/prod-fermigrid/fg1/lists/`):

| sample | as | pairs | events |
|---|---|---|---|
| MC BNB CV | fg1 | 37,742 | 500,000 |
| MC nueCC | fg1 | 11,445 | 100,003 |
| beam-off | fg1 | 1,096 | 49,970 |
| beam-on Run 1 | open-data FixedDev (ai-helper #40), sbndbuild03 | 1,817 | 89,946 |
| beam-on Run 3 | run3bnb (prod #5) | 2,208 | 109,487 |
| **total** | | 54,308 | **849,406** |

Every pair has its flat CAF (MC: child; data: sibling). Data needs FrameShift, as before.

## 3. Starting from the kept step-1 tars

| site | tars | state |
|---|---|---|
| Aurora | aurora-r1 `<unit>/ql/all/qlpctree.tar.gz` (toolkit `d06a47d7` + larwirecell `ad5d9421`), hardlinked by aurora-r2 | kept. Precedent: aurora-r2 = `seed-from-step1.py` + `WC_STEP1_SEEDED=1` |
| FNAL | fg1 / run3bnb on scratch: `<id>.qlpctree[.<slice>].tar.gz` (toolkit `4b6853d4` + `ad5d9421`); open data on persistent (toolkit `f6fd2209` + larwirecell `3b54651`) | on scratch, so evictable (none evicted on 2026-11-09). **No step-2-only grid mode exists yet** |

**Test (phase P2).** Rerun step 1 with 0.38.0 + `ad5d9421` on a sample and compare `qlpctree.tar.gz` with the kept tar, by datapath and array content (the #41 V1b method).
- Sample: per site and per sample, at least 5 units; for FNAL, all five samples, including open data, because of its older pins.
- **Reuse only if all arrays are identical.** Set metadata may differ only in `input_file`.
- Toolkit changes since the tars' builds that touch step 1 are the MABC Bee refactor (#548: Bee byte-identical), the #544 review fixes (Bee event split, per-event names, `truth_detail` argument) and master's #540 / #541. None should change the tar, but this is exactly what the test establishes.

**Savings if reused** (step 1 is most of the CPU):

| sample | step 1 / step 2 CPU per event (earlier productions) | step 1's share of one 2-step pass |
|---|---|---|
| Aurora BNB | 31 s / ~4.4 s | ~88 % |
| Aurora nueCC | 39 s / ~30–34 s | ~55 % |
| Aurora NC | 50 s / ~19 s | ~72 % |
| FG CV (grid) | ~37 s / ~7 s (of 44 s total) | ~84 % |
| FG nueCC (grid) | ~40 s / ~35 s (of 75 s) | ~53 % |

With two step-2 passes, reuse saves about **60 % of the CPU** overall (BNB/CV-dominated).

## 4. Two vertex modes, one CAF

- **Step 2 twice per step-1 tar:** `pr/` (`dv2_split_move`) and `pr-dv2snap/` (`dv2_snap`), each with its `tracking-pr.root`.
- **Merge:** `merge-caf.py` gains `--wc-tree-name` / a second input. The merged CAF has `recTreeWireCell` (split-move, the default and the name existing readers use) and `recTreeWireCell_dv2snap`, each aligned to `recTree` by RSE and with its own `valid`.
- **Validation:** `validate-merge.py` checks both trees.
- **Schema:** the same fixed schema for both trees, regenerated for 0.38.0 (new md5; #39 gate G5).

## 5. Phases and gates

| phase | what | where | gate |
|---|---|---|---|
| P0 | build/deploy 0.38.0 + larwirecell `ad5d9421`; DV2 Python env; doctests; compiled-config md5 for both modes (split-move = master's default) | Aurora (`prod_aurora`), sbndbuild03 + grid tarball (`porting_sbndbuild03`) | doctests pass (clus 512, pyutil 17, root 17, 33 + 20); the same config md5s on both sites |
| P1 | **smoke on real data**: nueCC-48 + NCπ0-19, step 2 in both modes from the same step-1 tars as issue 47 task A (FNAL) / prod #7 (Aurora) | both sites; FNAL also once through the grid `job.sh` | **`dv2_split_move` `tracking-pr.root` identical to issue 47 task A's `aurora_space` arm in every tree** (apart from `wct_version`); both sites agree by input digest (68/68); `dv2_snap` runs clean (rc 0, no DV2 fallback) and its changes vs split-move are listed |
| P2 | step-1 reuse test (§3) | both sites | identical tars → reuse; else run from reco1 |
| P3 | tooling: two step-2 passes, the two-tree merge, FG step-2-only job mode (if P2 passes) or full mode with the DV2 env on the grid | both sites | `validate-merge.py` PASS on the P1 data and on 2 MC pairs per sample |
| P4 | pilot about 1 % per sample | both sites | status OK ≥ 99 %; size and cost measured; this table updated |
| P5 | full run | both sites | everything merged and validated; failures listed; the catalog updated |

Start rules:
- P0–P4 start now.
- P5 starts after P4 passes. The agent posts its final estimate first, and Haiwang can stop it.
- **Nothing in aurora-r1, aurora-r2, fg1, run3bnb or the open data is deleted or overwritten.**
  - Aurora seeds by hardlink into a new tree.
  - FNAL reads the old tars, never moves them.
  - New outputs go under new directories: `…/WCLocal2026Nov16/…`.

## 6. Estimates (to be replaced by the P4 measurements)

**Assumptions:**
- Per-event sizes and costs are from aurora-r1/r2 and fg1 (prod #1–#5).
- `aurora_space` step 2 ≈ 0.8× the old `original` step 2: no dual chain (−28 %, ai-helper #43), DV2 call +13 % CPU (#47).
- Both passes cost about the same.

### Disk

| | step-2 only (tars reused) | from reco1 |
|---|---|---|
| **Aurora** (Flare): 2 × `tracking-pr` + 1 CAF with 2 trees | BNB 627k × 2.4 MB ≈ **1.5 TB**; nueCC 269k × 4.6 MB ≈ **1.2 TB**; NC 27k × 4.6 MB ≈ **0.12 TB**; **≈ 2.9 TB** | + new qlpctree (~1.4–2 MB/event) ≈ **+1.5 TB → ~4.4 TB** |
| **FNAL** persistent: merged CAFs with 2 trees | CV 0.50 + nueCC 0.13 + beam-off 0.01 + beam-on 0.07 ≈ **0.7 TB** | same |
| **FNAL** scratch: 2 × `tracking-pr` | ≈ **0.9 TB** | + qlpctree ~1.9 MB/event ≈ **+1.6 TB → 2.5 TB** |

**Space available:**
- Flare project: ~240–260 TB free as of 2026-11-05. `prod_aurora` re-checks it.
- FNAL dCache quotas: **not recorded anywhere**. `porting_sbndbuild03` checks persistent and scratch for the user/group before P4.
- fg1 already holds 578 GB persistent + ~2.2 TB scratch.

### CPU and wall clock

| | step-2 only (×2 modes) | from reco1 (step 1 + 2 × step 2) |
|---|---|---|
| **Aurora** node-hours | ~180–220 (aurora-r2's one step-2 pass = 109; ~0.8× per pass, × 2, + per-unit overhead) | ~450 (+ aurora-r1's step-1 share, ~250) |
| **Aurora** wall clock | 8-node capacity jobs, 2 at once (16 nodes): ~12–14 h running + queue (median 2.4 h per 8-node job; 16-node jobs waited much longer) → **~1–1.5 days** | ~28 h running → **~2–3 days** |
| **FermiGrid** core-hours | ~5–6k | ~13–14k (fg1: 8.9k for 650k events with one step 2) |
| **FermiGrid** wall clock | after the step-2-only tooling (~0.5–1 day): **< 1 day** of grid time (fg1 took ~1.5 days at ≤ 2,000 jobs per sample) | **~2–3 days** of grid time + ~0.5 day of tooling |

### FermiGrid, measured in the P4 pilot (`porting_sbndbuild03`, 2026-11-16)

From 546 pilot pairs (8,540 events), both passes + merges + validations (`porting_sbndbuild03/results.md` P4).

| P5 still to run | pairs | events | CPU (core-h) | tracking-pr tars | merged CAFs |
|---|---|---|---|---|---|
| MC CV | 37,342 + 22 from reco1 | 495,013 | ~2,130 | 0.56 TB | 0.50 TB |
| MC nueCC | 11,306 + 24 | 99,015 | ~1,800 | 0.21 TB | 0.15 TB |
| beam-off | 1,043 + 42 | 49,473 | ~170 | 0.02 TB | 0.01 TB |
| run3bnb | 2,181 + 4 | 108,386 | ~320 | 0.09 TB | 0.03 TB |
| opendata | 1,797 + 1 | 89,032 | ~310 | 0.08 TB | 0.03 TB |
| **total** | **53,762** | **840,919** | **~4,700** (~5,700 slot-h with job overhead) | **0.95 TB** | **0.72 TB** |

- **Disk:**
  - scratch: +1.7 TB (tars + CAFs + 0.01 TB of logs);
  - persistent: +0.72 TB for the CAF copy. The user pnfs quota has 864 of 4,656 GiB used.
- **Wall clock:** 8,455 jobs of ~45–60 min. At the slot counts fg1 and run3bnb got, ~0.5–1 day of grid time. Then a recovery pass at 8 GB for the ~0.2 % of pairs killed at the 4 GB limit (1 of 546 in the pilot).

Allocation (Aurora): suballocation 17986 `neutrinoGPU::WireCell_aurora` (2,000 node-hours, users yuhw/abhat/xning). Its balance is not recorded; `prod_aurora` checks it in P0.

## 7. Risks

- **R1, the DV2 Python env on the grid:** torch from the CVMFS scn product, plus lightgbm 4.6.0 built for SL7, shipped in the job tarball, and the bundle (165 MB) staged to the workers. Untested on FermiGrid. Without it every job fails at configure, since #543 fails hard.
- **R2, scratch eviction:** the fg1 / run3bnb tars are on scratch. Count what is left before relying on them; fall back to reco1 for missing ones.
- **R3, step-1 differences:** if P2 finds a difference, the plan becomes "from reco1" (the estimates above).
- **R4, crashes:**
  - SIGURG (#45): `GODEBUG=asyncpreemptoff=1`;
  - Aurora pids cap (8,192 per node; ~77 units per node);
  - `ClusteringDeghost` memory runaways;
  - the `CreateSteinerGraph` 6.4 GB memory kills on the grid.
- **R5, queue waits:** Aurora 16-node jobs waited about 38 h (median), so use 8-node jobs.

## 8. Roles

| agent | role |
|---|---|
| `prod_aurora` | WCLocal2026Nov16-Aurora: P0–P5 on Aurora |
| `porting_sbndbuild03` | 2026-11-16 20:10 CST: **P4 pilot passed** (545/546 OK; 1 pair killed at the 4 GB limit, OK locally at 5.35 GB → 8 GB recovery pass); P5 tarball `53a90eb` (all BDT weight files; = pilot output on 2 emulated pairs); final estimate posted (§6); **P5 submitted** | P5 jobs; then recovery pass, CAF copy to persistent |
| `prod_polaris` | coordination, this doc, the cross-site comparisons, reports to Haiwang |

## 9. Agent protocol (as in #47)

- Comments on issue 48 start with `[from <agent>]`; address a request as `@<agent>`.
- Each agent's files go in `issues/48-wclocal-2026nov16-productions/<agent>/`: scripts, tables, logs, no data. Force-add figures/PDFs (`git add -f`; the repo ignores them).
- Each agent keeps its line in §10 current.
- Owner decisions go to Haiwang. Agents never delete earlier productions.

## 10. Status

| agent | state | waiting for |
|---|---|---|
| `prod_aurora` | 2026-11-17 02:55 UTC: P0–P4 done (pilot 908/908 OK, `prod_aurora/p4.md`; estimate ≈ 2.3 TB, 90–110 node-h); **P5 submitted** (8-node capacity): BNB 9097095, NC 9097098 (afterany BNB), nueCC 9097132; full tree hardlink-seeded (90,744 units). 0.38.1 test fix `24be7fb0` pushed to the fork branch `fix-0.38-werror-tests`, verified under the release flags | P5 jobs; `prod_polaris` for the 0.38.1 PR |
| `porting_sbndbuild03` | 2026-11-16 17:10 CST: P0, P1 done; **P2 done: 25/25 step-1 tars identical → step-2-only**; P3 grid test 4/4 OK, grid = local in every tree; **P4 pilot submitted** (546 pairs, 73 jobs, `porting_sbndbuild03/results.md`) | the pilot; `prod_aurora` on branch `wclocal-nov16` |
| `prod_polaris` | 2026-11-17 02:45 UTC: config md5s agree on one recipe (Aurora reproduced porting's 4); schemas kept (`af9c87c8` / `d4396a34`, both sites); both pilots passed, P5 starting; 0.38.1 test fix requested from `prod_aurora` | P5 progress; the 0.38.1 fix branch |

## Log

- 2026-11-16 (`prod_polaris`): request, decisions, survey of aurora-r1/r2 and fg1, plan v1, issue opened.
- 2026-11-16 (`porting_sbndbuild03`): P0 + P1 on sbndbuild03 done; existing schemas fit 0.38.0 (proposal: keep them, one per tree); workflow branch `wclocal-nov16` (two passes, two-tree merge, step-2-only grid mode); P2 started.
- 2026-11-16 (`porting_sbndbuild03`): P2 done (25/25 identical; open data differs only in `input_file` metadata) → FermiGrid runs step 2 only for 54,215 pairs (93 from reco1); grid test 4/4 OK; P4 pilot submitted 17:00 CST.
- 2026-11-16 (`porting_sbndbuild03`): P4 pilot 545/546 OK; tarball fix `53a90eb` (legacy BDT weight files, unused but logged, now rc 91 under `d05cf47`); §6 FermiGrid estimate measured; P5 submitted.
- 2026-11-17 (`prod_polaris`): md5s and schemas closed; both pilots passed (FG 545/546, Aurora 908/908); P5 estimates: Aurora ~2.3 TB / 90–110 node-h / ~1 day; FG +1.7 TB scratch + 0.72 TB persistent / ~4.7k core-h / 0.5–1 day.
