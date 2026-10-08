# SBND 2-step chain with the DL-vertex dump: the four #26 samples (campaign r7, on master `b7bd2a1a`)

What was run, with which software, on which inputs, where the outputs are, and how to read and check the DL-vertex dump. **This document is updated as each sample finishes** (status in §1, change log in §9).

Tracking issue: [ai-helper #38](https://github.com/HaiwangYu/wire-cell-toolkit-ai-helper/issues/38), log (d) onward ([doc](../issues/38-sbnd-2step-dlvtx-xin-samples/38-sbnd-2step-dlvtx-xin-samples.md)). Machine: `sbndbuild03.fnal.gov`.

## 1. Status

Run r7 started 2026-10-07 22:23 CDT on toolkit master `b7bd2a1a`. It replaces run r6 (`sbnd-dlvtx-35` `21562551`), which was stopped and whose outputs were deleted, at Haiwang's request, once Xin's `match_isFC` update reached master (§8).

| sample | events in | units | status | events with `tracking-pr.root` |
|---|---|---|---|---|
| MC BNB CV | 13,113 | 990 files + 2 side units (`mc-cv-fix/`) | **done** 2026-10-08 02:22 (4.0 h) | **13,112** (13,099 + 13 side); only run 471 / subrun 18 / event 33 missing |
| MC nueCC | 8,877 | 999 files | **done** 2026-10-08 06:58 (4.6 h; last unit 07:07) | **8,877 / 8,877** |
| beam-on | 10,000 | 502 chunks of ≤ 20 | running since 2026-10-08 06:58 | – |
| beam-off | 10,000 | 508 chunks of ≤ 20 | queued | – |

Known before the start:
- MC CV `f0686` holds run 471 / subrun 18 / event 33, the deterministic step-1 crash (#26 §5a). Its other 13 events run as the side units `f0686a` / `f0686b` in `mc-cv-fix/`. Event 33 is lost, as in round 3.
MC BNB CV result (`mc-cv/summary.md`, `mc-cv/dlvtx-stats.txt`):
- 989 of 990 regular units have both steps at rc 0, plus both side units. Every unit has 0 `DL vertex failed`, and no stub files remain.
- One step-2 crash (`f0068`, `TrackFitting.cxx:1028`, peak RSS 4.4 GB) was recovered by the retry pass.
- 6,155 neutrino candidates (47.0 %). DL calls: 6,140 production + 6,140 OFF pass. DL accepted: 5,909 production, 3,323 OFF pass.
- Final vertex vs the SCE-shifted truth, over all candidates: median 0.84 cm, 52 % < 1 cm.
- Per event: step 1 24.0 s CPU, step 2 3.5 s CPU. 106 GB on disk.

MC nueCC result (`mc-nuecc/summary.md`, `mc-nuecc/dlvtx-stats.txt`):
- All 999 units have both steps at rc 0, with 0 `DL vertex failed` and no stubs: 8,877 / 8,877 events.
- **16 units crashed in step 2 on the first pass:** 14 × rc 139, 1 × rc 11, 1 × abort rc 6. The retry pass recovered 15. `f0882` failed twice and succeeded on a third, manual attempt (`mc-nuecc-retry3.tsv`).
  - That is one first-pass crash per ~550 events, against ~1 per 13,000 on MC CV: the crash favours the larger nueCC events.
  - Signature: peak RSS ~4.5 GB (median 1.5 GB); several runs had a failed DL Python call (`new(): invalid arguments`, `unknown parameter type`) just before the crash. This looks like a runaway allocation in the PR stage.
- 8,426 neutrino candidates (94.9 %). DL calls: 8,730 production + 8,730 OFF pass. DL accepted: 8,525 production, 6,913 OFF pass.
- Final vertex vs the SCE-shifted truth: median 0.75 cm, 55 % < 1 cm.
- Per event: step 1 27.6 s CPU, step 2 19.1 s CPU. 84 GB on disk.

- An intermittent step-2 crash (`TrackFitting::update_association`, `SteinerGrapher`) hits a few units. The pool retries every failed unit once; details in §8.

## 2. Software

| component | version | where |
|---|---|---|
| wire-cell-toolkit | **master `b7bd2a1a`** (2026-10-07: includes PR 536, the DL dump, merged; Xin's `match_isFC` in `T_tagger`, `0bb05b3c`; and his note `cfg/pgrapher/experiment/sbnd/docs/match-isfc-in-tagger-tree.md`) | `github.com/HaiwangYu/wire-cell-toolkit`; checkout `/exp/sbnd/app/users/yuhw/wire-cell-toolkit`, installed to `/exp/sbnd/app/users/yuhw/opt` |
| larwirecell | branch `dev-v10_14_02_02`, **`189ad26`** (adds `wclsOpHitSource`, `wclsTruthInformationAttacher`, the labeler RNG re-seed) | `github.com/HaiwangYu/larwirecell`; MRB tree `/exp/sbnd/app/users/yuhw/larsoft-wct036/v10_14_02/srcs/larwirecell`, libs in `opt/larwirecell/v10_01_28/slf7.x86_64.e26.prof/lib` |
| wcp-porting-validation | `main`, **`072505ce`** (the step-1 fcls `sbnd/wcls-img-clus-matching{,-data}.fcl`) | `github.com/WireCell/wcp-porting-validation`; `/exp/sbnd/app/users/yuhw/wcp-porting-img` |
| wire-cell-data | `9e2f4b8` + `uboone/weights/XGB_nue_seed2_0923.xml` (md5 `2bdb5cec…`) | `/exp/sbnd/app/users/yuhw/wire-cell-data` |
| DL-vertex weights | `uboone/scn_vtx/t48k-m16-l5-lr5d-res0.5-CP24.pth`, md5 `9cc1413e053c09534edc2d37cdfdc1d4` | wire-cell-data |
| DL runtime | uBooNE UPS `scn v01_00_00` (torch, sparseconvnet; python 3.9.15) + toolkit `pyutil/python/SCN_Vertex.py` installed in `opt/python` | `sbnd/setup-dlvtx.sh` |
| LArSoft environment | `sbndcode v10_14_02_03 -q e26:prof`, in the SL7 apptainer | `sbnd/setup-ap.sh` |

The compiled configs were proven before the run (`r7-r26-master-b7bd2a1a/cfg-proof/report.txt`, all 43 checks):
- All 8 SBND jobs compile byte-identically to master `0319ea67` and to `21562551`; Xin's changes are C++ or default-off.
- The dump adds only `SCEFieldTH3:sbnd_dualmap_fwd` and the `dl_vtx_dump` / `sce_field` keys.
- larwirecell was not rebuilt, because none of the headers it includes changed.

New in `tracking-pr.root` with this toolkit: `T_tagger.match_isFC` (Float_t 0/1, per neutrino candidate). It is the containment flag the numu and nue BDTs read; previously it was computed but never written.

## 3. The chain

Our larwirecell 2-step chain (#33). This is not Xin's sbnd-reco1 2-step.
```
step 1  lar --nskip k -n N -c wcls-img-clus-matching.fcl       -s <reco1.root> --no-output   (MC)
        lar --nskip k -n N -c wcls-img-clus-matching-data.fcl  -s <reco1_frameshift.root> --no-output   (data)
        -> qlpctree.tar.gz (imaging, clustering, Q/L matching with hit-rebuilt flashes, all-APA clustering,
           MC truth tables), mabc.zip (Bee), nugraph.h5
step 2  wire-cell -c pgrapher/experiment/sbnd/wct-pr.jsonnet --tla-str input=qlpctree.tar.gz \
           --tla-str reality=sim|data --tla-code dl_vtx_dump=true
        -> pr_evt<E>/tracking-pr.root (PR, taggers, BDT scores, T_truth_* on MC, T_dlvtx_call / T_dlvtx_cloud),
           mabc-pr.zip (Bee)
```
Driver: `issues/38-*/scripts/run-2step-pool.sh` and `run-all.sh`. One work unit is one `lar` step 1 followed by one `wire-cell` step 2 on its tar.

## 4. Inputs

Exactly #26's events, from its per-event manifests (`<file> <nskip> <run> <subrun> <event>`).

| sample | SAM definition | #26 manifest (sbndbuild03) | unit list for this run |
|---|---|---|---|
| MC BNB CV | `aurora_SBND2026A_gen2_BNBLight_prodgenie_corsika_proton_rockbox0p1_sbnd_CV_v10_14_02_03_reco1_sbnd` | `/exp/sbnd/data/users/yuhw/production-prep/r3-mc-cv-2026-09-09/lists/mc.manifest` (1,000 files on `/pnfs/sbn/data_add/sbn_nd/aurora/mc/v10_14_02_03/…/Gen2_2026/CV/reco1/`) | `r7-r26-master-b7bd2a1a/lists/mc-cv.units.tsv` (990), `mc-cv.fix-471-18-33.tsv` (2) |
| MC nueCC | `aurora_SBND2026A_gen2_BNBLight_prodgenie_corsika_proton_rockbox0p1_sbnd_EX_nuecc_v10_14_02_05_reco1_sbnd` | `/exp/sbnd/data/users/yuhw/production-prep/r3-nuecc-2026-09-10/lists/nuecc.manifest` (999 files, `…/v10_14_02_05/…/Gen2_Exclusive_2026/nuecc/reco1/`) | `lists/mc-nuecc.units.tsv` |
| beam-on | `data_MCP2025C_Fall25-Run1_BNB_FixedDev_bnblight_v10_14_02_reco1_sbnd` (runs 18255, 18259) | `/exp/sbnd/data/users/yuhw/production-prep/r3-beam-on-2026-09-10/lists/beam-on.manifest`; files staged, merged and **frameshifted** in `r3-data-stage-2026-09-09/beam-on/chunk*.root` | `lists/beam-on.units.tsv` |
| beam-off | `data_SBND2026A_gen2_InTime-Run1_v10_14_02_02_reco1_sbnd` | `/exp/sbnd/data/users/yuhw/production-prep/r3-beam-off-2026-09-11/lists/beam-off.manifest`; staged and frameshifted in `r3-data-stage-2026-09-09/beam-off/chunk*.root` | `lists/beam-off.units.tsv` |

- `lists/` is `/exp/sbnd/data/users/yuhw/production-prep/r7-r26-master-b7bd2a1a/lists/`. Each `*.units.tsv` row is `unit  file  nskip  nevents`.
- MC: one unit per reco1 file, with the event count #26 used. Data: 20-event slices of the staged chunks in art FileIndex order.
- **10 MC CV files (104 events) of #26 no longer exist** on `/pnfs`, and SAM no longer knows them. They are listed in `lists/mc-cv.missing.txt`. MC CV is therefore 13,113 events, not 13,217.
- The SBND2026A `gen2_BNB-Run1` set is blinded and is not used.

## 5. Outputs

```
/exp/sbnd/data/users/yuhw/production-prep/r7-r26-master-b7bd2a1a/
  <sample>/<unit>/ql/qlpctree.tar.gz          step-1 tar, every event of the unit (MC: truth_nu / truth_pf tables)
                    ql/mabc.zip                step-1 Bee (imaging, clustering, op; MC: sed-* truth deposits)
                    ql/nugraph.h5              labeler HDF5
                    ql/lar.log.gz, rc, time.txt
                 pr/pr_evt<E>/tracking-pr.root <- the main output, one per event (E = art event number)
                    pr/mabc-pr.zip             step-2 Bee (PR layers, taggers)
                    pr/wct.log.gz, rc, dl_fail, time.txt
                 pr-try1/                      a failed step-2 attempt kept for the record (retried units only)
  <sample>/units.tsv        unit -> input file, nskip, n
  <sample>/events.tsv       per event: unit, ident, run/subrun/event, candidate, DL calls / accepted, cloud points, truth rows, scores, Enu
  <sample>/summary.md       counts, resources, sizes
  <sample>/dlvtx-stats.txt  DL decision statistics (issue 35 dlvtx-stats.py)
  <sample>/pool.log         one line per unit: ql_rc, pr_rc, dl_fail
  mc-cv-fix/                the two f0686 side units (events 1-30, 34-50 of that file)
  cfg-proof/                compiled configs and report of the config proof
  validation/               the comparison with Xin's references (§8) and standalone-inference replays (§7)
```
`<sample>` is `mc-cv`, `mc-nuecc`, `beam-on` or `beam-off`. A `tracking-pr.root` without a `Trun` tree is a stub left by a crashed step 2, and `summarize.py` reports it. `tracking-pr.root` holds the usual trees: `Trun`, `T_kine`, `T_tagger`, `T_cluster`, `T_rec_charge`, `T_bad_ch`, `T_proj`, `T_proj_data`, `T_bundle`, `T_flash`, `T_segment`, plus `T_truth_nu` / `T_truth_pf` on MC. It also holds the two trees below.

## 6. The DL-vertex dump: `T_dlvtx_call` and `T_dlvtx_cloud`

**Where they come from.** Per neutrino candidate (flash bundle), `TaggerCheckNeutrino` calls the DL vertex network up to twice:
- the **OFF pass**, the dual-chain exclusion-free copy of the vertexing (`pass = 1`);
- the **production pass** (`pass = 0`).

Each call goes to `SCN_Vertex.SCN_Vertex` with a point cloud built from the PR graph after trajectory fitting. With `dl_vtx_dump=true` every call is recorded as it happened. Nothing recorded feeds back into the reconstruction: with the knob on, every other tree and the Bee output are unchanged (#35). Flow diagram: toolkit `cfg/pgrapher/experiment/sbnd/docs/sbnd-dl-vertex-flow.md`.

Units are cm and GeV. Positions are in the reco (cloud) frame: drift x after the cluster t0 correction, and on data y/z after the per-TPC position offsets. Both trees are written for every event; they are empty when the event made no call.

### `T_dlvtx_call`: one row per network call

Key: (`runNo`, `subRunNo`, `eventNo`, `nu_index`, `call_index`). `nu_index` is the candidate within the event; `call_index` is the call within the candidate.

| branches | meaning |
|---|---|
| `pass` | 0 = production; 1 = dual-chain OFF pass (snap mode, the production setting); 2 = the OFF graph's own top-K call in voxels/union mode (not used in production) |
| `status` | 0 ok; 1 the network threw (payload empty); 2 unexpected payload size |
| `top_k`, `rerank` | top-K requested (5 in production) and whether `dl_vtx_rerank` was on |
| `n_points`, `n_vertex_rows` | cloud size; the first `n_vertex_rows` points are PR-graph vertices, the rest are segment-interior fit points |
| `q_scale`, `q_offset` | the network's charge is q = dQ × `q_scale` + `q_offset` |
| `cloud_no_exclusion` | 1 if the cloud came from an exclusion-free refit of this pass's graph (an optional knob, off in production) |
| `payload` | the call's raw network output: [x, y, z, score] × K with rerank (legacy: [x, y, z]) |
| `payload_from_off`, `n_off_voxels` | voxels mode: the payload is the OFF pass's. Union mode: OFF voxels pooled into the decision after the record. Both are 0 in production (snap) |
| `trad_valid`, `trad_x/y/z`, `trad_row` | the traditional main vertex before the DL |
| `rerank_valid`, `rerank_x/y/z`, `rerank_row` | this call's own pick, the rerank winner that passed its score gate, **before** the dual-chain snap |
| `accepted`, `dl_x/y/z`, `dl_row` | whether the DL vertex was accepted (the main vertex was switched to it) after snap and veto, and where |
| `dual_transferred` | production row: the snap to the OFF pass's vertex replaced production's own pick |
| `two_end_veto` | the protected two-end-break vertex vetoed the DL choice |
| `hint_valid`, `hint_x/y/z` | production row: the OFF pass's final vertex given to this call as the snap hint |
| `final_valid`, `final_x/y/z` | the candidate's final main vertex, after the refit |
| `*_row` | index of that vertex inside the cloud's vertex block (0 .. `n_vertex_rows`-1), or -1 |
| `truth_valid`, `truth_sce_applied`, `truth_x/y/z`, `truth_reco_x/y/z` | MC: the max-edep interaction of the event, raw (`truth_*`) and shifted into the cloud frame by the TrueFwd SCE map (`truth_reco_*`). `truth_valid` needs edep > 0; `truth_sce_applied` = 1 when the SCE map was configured (always, with the knob) |
| `truth_n`, `truth_all_{nu_idx,pdg,ccnc,E,edep,t,x,y,z,reco_x,reco_y,reco_z}` | MC: every interaction of the event as vectors, so the reader can choose the one that belongs to each candidate (an event can hold a rockbox interaction too) |

### `T_dlvtx_cloud`: one row per network-input point

`runNo`, `subRunNo`, `eventNo`, `nu_index`, `call_index`, `pass` (as above), `ipoint` (0 .. `n_points`-1, the order the network received), `is_vertex` (1 for the leading vertex block), and `x`, `y`, `z`, `q`.

These are the **exact float32 values** the network received, which is what training needs. The final fit points in `T_rec_charge` are not the network input: they come after the refit around the chosen vertex.

Joining the two trees: select the cloud rows with the same (`runNo`, `subRunNo`, `eventNo`, `nu_index`, `call_index`).

```python
import ROOT
f = ROOT.TFile.Open('.../pr_evt<E>/tracking-pr.root')
calls = {(c.nu_index, c.call_index): c for c in f.T_dlvtx_call}   # careful: PyROOT reuses the entry object; copy fields you need
pts = {}
for p in f.T_dlvtx_cloud:
    pts.setdefault((p.nu_index, p.call_index), []).append((p.x, p.y, p.z, p.q))
```
To select training data, #35 log (e) uses: the truth vertex in the active volume, the candidate whose production cloud contains it, and `pass` 0 or 1 for the two clouds (`issues/35-*/scripts/dlvtx-truth-eval.py`).

## 7. Validating the dump: WCT-integrated vs standalone inference

**The idea.** The network output recorded in production (`payload`) must be reproduced by calling the same Python entry point on the recorded cloud, outside WCT. That entry point is `SCN_Vertex.SCN_Vertex` from toolkit `pyutil/python/SCN_Vertex.py`, which `WCPPyUtil::SCN_Vertex` imports. The check uses the same weights file and the same `top_k`. If it passes, the dumped cloud is exactly the network input, and a model trained or evaluated standalone on `T_dlvtx_cloud` sees what production sees.

**Tool:** `issues/35-sbnd-dl-vertex-train-infer/scripts/dlvtx-replay.py`, run on sbndbuild03 in SL7 with the production environment.
```bash
SBND=/exp/sbnd/app/users/yuhw/wcp-porting-img/sbnd
T=/exp/sbnd/data/users/yuhw/wire-cell-toolkit-ai-helper/issues/35-sbnd-dl-vertex-train-infer/scripts
SL7_SETUP=$SBND/setup-ap.sh /exp/sbnd/app/users/yuhw/claude-utilities/in-gpvm-sl7.sh bash -c "
  source $SBND/setup-ap.sh >/dev/null 2>&1      # re-source: setup-dlvtx.sh needs its path-prepend function
  source $SBND/setup-dlvtx.sh                   # scn product (torch, sparseconvnet) + opt/python (SCN_Vertex.py)
  python3 -c 'import SCN_Vertex, torch, sparseconvnet' || exit 1
  python3 $T/dlvtx-replay.py --json replay.json <dir>/*/pr/pr_evt*/tracking-pr.root"
```
- **Weights:** the default is the production `uboone/scn_vtx/t48k-m16-l5-lr5d-res0.5-CP24.pth`, resolved along `WIRECELL_PATH` the way `TaggerCheckNeutrino` resolves it. `--weights` overrides it, for testing another model on the same clouds.
- **Verdict per call:**
  - **exact:** bit-identical payload.
  - **equivalent:** identical voxel coordinates in the same order (the same ranking), every score within 1e-5. Scores move by 1–3 float32 ulps between the production process and a fresh one. The replay repeats bit-identically within one process, so this is the network's float non-determinism, not an input difference.
  - **MISMATCH:** anything else. The gate fails.
- Calls with `status` ≠ 0 and calls whose payload came from the OFF pass are counted and skipped.
- **Pitfall:** without `setup-dlvtx.sh` (or when sourced inside a fresh `bash -c` without re-sourcing `setup-ap.sh`), production itself logs `DL vertex failed: … No module named 'SCN_Vertex'`, falls back to the traditional vertex, and still exits 0. The pool records the count per unit in `pr/dl_fail`; it must be 0. It is 0 for every unit of this campaign so far.

**Companion tools:**
- `dlvtx-stats.py`: DL decision statistics per pass, and on MC the distances of the traditional, DL and final vertices to the SCE-shifted truth.
- `dlvtx-call-diff.py`: per-call detail when a replay is not exact.

**Results:**

| where | calls | exact | equivalent | MISMATCH |
|---|---|---|---|---|
| #35, Aurora: MC-9, NCpi0-19, nueCC-48, gen2 CV 1006, PR 536 review build | > 2,000 | – | – | 0 |
| #38 smoke on sbndbuild03 (#30 MC CV, nueCC, beam-off; build `78f81c64`) | 34 | 20 | 14 (worst 7.2e-7) | 0 |
| run r6 (deleted), MC CV units `f0000`–`f0099`, 1,212 events (build `21562551`) | 1,172 (586 prod + 586 off) | 697 | 475 (worst 2.7e-6) | **0** |
| **run r7**, MC CV units `f0000`–`f0099`, 1,212 events (master `b7bd2a1a`; `validation/replay/mccv-f0000-f0099.{txt,json}`) | 1,172 | 697 | 475 (worst 2.7e-6) | **0** |
| **run r7**, MC nueCC units `f0000`–`f0099` (`validation/replay/nuecc-f0000-f0099.{txt,json}`) | 1,758 | 724 | 1,034 (worst 6.1e-6) | **0** |

## 8. Validation against Xin's references (before the r7 start)

**References** (Xin, toolkit `469ae3be`, the same code as `b7bd2a1a`, on wcgpu1): `/nashome/y/yuhw/sbnd-data/sbnd_xin/work-{ncpi0,nuecc48}-d133pr/pr_evt<E>/tracking-pr.root`, 19 NCpi0 + 48 nueCC data events. They are his PR stage only, run on his existing 2026-09-25 (`m0925`) charge-light matching products.

**Ours:** the full 2-step chain at production settings (dump on) on the same events, from Lynn's frameshifted files. Output is in `r7-r26-master-b7bd2a1a/validation/`. Every branch of every tree is compared per event (`evt-branch-diff.py`, NaN = NaN). Branches whose largest relative difference is ≤ 1e-6 count as float noise.

| comparison | NCpi0 (19) | nueCC (48) |
|---|---|---|
| ours (production step 1) vs Xin | 9 float noise only, 10 also flash timing | 30 float noise only, 12 also flash timing, 6 with physics differences |
| ours with the **old flash rule** in step 1 vs Xin | **19 float noise only** | **42 float noise only**, 4 with physics differences (2 events not compared: crashed chunk) |
| ours production vs ours old-flash (same machine) | – | 30 bit-identical, 13 flash timing only, 3 changed by the flash rule |

- **Float noise:** `T_rec_charge` `q`, `reduced_chi2` and fit points at ~1e-13 relative. This is the cross-machine residual recorded in `docs/sbnd-1step-build-run-validate.md` §7.
- **Flash timing** (`T_flash.time_us`, `T_cluster.cluster_t0_us` / `flash_time_us`): master's new `SBNDOpFlashFinder` prompt-time rule (`4afd5cac`, deploy note change 1) is in our step 1. Xin's products predate it.
  - With the old rule (`prompt_min_* = 0`, deploy note §3.3) all of it vanishes.
  - Events 81597 and 350186, whose candidate cluster changed, then also match Xin. 131357 changes with the rule too.
- **Still different from Xin with the old rule:** nueCC 90055 (`ssm_offvtx_energy`, 3e-4 rel), 239794 (`hol_2_ncount` 2 → 1), 131357 (Enu 1e-4 rel, one segment) and 433451 (vertex moved ~mm, Enu 3 %).
  - Our two runs give the same result for 90055, 239794 and 433451, so the difference is systematic, not run-to-run.
  - It is consistent with cross-machine float differences (wcgpu1 vs sbndbuild03, including the DL network's float path) seeding discrete choices.
  - It cannot be pinned further without Xin's `m0925` step-1 products on this machine.
- **Intermittent step-2 crash:** nueCC chunk `c2` (events 269774 … 444187) crashed in 3 of 4 step-2 runs, at varying events.
  - The crash site moved: `TrackFitting::update_association` the first time, `Steiner::Grapher::find_peak_point_indices` (`SteinerGrapher.cxx:1027`) the second.
  - Once, before the crash, the DL network call failed with `Python function call failed: unknown parameter type`.
  - This points to heap corruption earlier in the PR. The runs that finished agree bit-for-bit.
  - Reproducer: `validation/oldflash/nuecc48/c2/ql/qlpctree.tar.gz` with production step 2. To fix ourselves later.

## 9. Change log

- 2026-10-08 07:30 — MC nueCC done: 8,877 / 8,877 events. 16 first-pass step-2 crashes, all recovered. Replay of `f0000`–`f0099`: 1,758 calls, 0 mismatch. beam-on running.

- 2026-10-08 02:22 — MC BNB CV done: 13,112 / 13,113 events. Replay of `f0000`–`f0099`: 1,172 calls, 0 mismatch. MC nueCC started.

- 2026-10-07 22:23 — **r7 started on master `b7bd2a1a`** (§1), after the validation of §8. Run r6 was stopped (MC CV done; nueCC 125 of 999 units in), and its outputs (~119 GB, `r6-dlvtx-r26-samples/{mc-cv,mc-nuecc,smoke,validation}`) were deleted at Haiwang's request. The r6 lists, logs and config proof are kept. Toolkit rebuilt; RPATH stripped; build and config-proof gates pass.
- 2026-10-07 21:10 — created (run r6). MC CV done; MC nueCC running; beam-on/off queued. Replay of MC CV `f0000`–`f0099`: 1,172 calls, 0 mismatch.
