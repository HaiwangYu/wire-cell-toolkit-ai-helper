# SBND 2-step chain with the DL-vertex dump: the four #26 samples (campaign r6)

What was run, with which software, on which inputs, where the outputs are, and how to read and check the DL-vertex dump. **This document is updated as each sample finishes** (status in §1, change log in §8).

Tracking issue: [ai-helper #38](https://github.com/HaiwangYu/wire-cell-toolkit-ai-helper/issues/38), log (c) onward ([doc](../issues/38-sbnd-2step-dlvtx-xin-samples/38-sbnd-2step-dlvtx-xin-samples.md)). Machine: `sbndbuild03.fnal.gov`.

## 1. Status

| sample | events in | units | status | events with `tracking-pr.root` |
|---|---|---|---|---|
| MC BNB CV | 13,113 | 990 files + 2 side units | **done** 2026-10-07 20:58 | see §1 note |
| MC nueCC | 8,877 | 999 files | running since 2026-10-07 20:58 | – |
| beam-on | 10,000 | 502 chunks of ≤ 20 | queued | – |
| beam-off | 10,000 | 508 chunks of ≤ 20 | queued | – |

MC BNB CV notes:
- 13,112 of 13,113 events ran. All 991 regular units have both steps at rc 0, with 0 `DL vertex failed`.
- One file, `f0686`, holds run 471 / subrun 18 / event 33, the known deterministic step-1 crash (#26 §5a). Its other 13 events ran as the side units `f0686a` / `f0686b`. Event 33 is lost, as in round 3.
- One step-2 segfault (`f0587`) re-ran cleanly. This is the intermittent crash in `TrackFitting::update_association` (#38 log (b)).

## 2. Software

| component | version | where |
|---|---|---|
| wire-cell-toolkit | branch `sbnd-dlvtx-35`, **`21562551`** (master `0319ea67` + the DL dump, WireCell PR 536 with its review fixes) | `github.com/HaiwangYu/wire-cell-toolkit`; checkout `/exp/sbnd/app/users/yuhw/wire-cell-toolkit`, installed to `/exp/sbnd/app/users/yuhw/opt` |
| larwirecell | branch `dev-v10_14_02_02`, **`189ad26`** (adds `wclsOpHitSource`, `wclsTruthInformationAttacher`, the labeler RNG re-seed) | `github.com/HaiwangYu/larwirecell`; MRB tree `/exp/sbnd/app/users/yuhw/larsoft-wct036/v10_14_02/srcs/larwirecell`, libs in `opt/larwirecell/v10_01_28/slf7.x86_64.e26.prof/lib` |
| wcp-porting-validation | `main`, **`072505ce`** (the step-1 fcls `sbnd/wcls-img-clus-matching{,-data}.fcl`) | `github.com/WireCell/wcp-porting-validation`; `/exp/sbnd/app/users/yuhw/wcp-porting-img` |
| wire-cell-data | `9e2f4b8` + `uboone/weights/XGB_nue_seed2_0923.xml` (md5 `2bdb5cec…`) | `/exp/sbnd/app/users/yuhw/wire-cell-data` |
| DL-vertex weights | `uboone/scn_vtx/t48k-m16-l5-lr5d-res0.5-CP24.pth`, md5 `9cc1413e053c09534edc2d37cdfdc1d4` | wire-cell-data |
| DL runtime | uBooNE UPS `scn v01_00_00` (torch, sparseconvnet; python 3.9.15) + toolkit `pyutil/python/SCN_Vertex.py` installed in `opt/python` | `sbnd/setup-dlvtx.sh` |
| LArSoft environment | `sbndcode v10_14_02_03 -q e26:prof`, in the SL7 apptainer | `sbnd/setup-ap.sh` |

The compiled configs were proven before the run (#38 log (c), `scripts/cfg-proof.py`, all 43 checks):
- With the dump off, all 8 SBND jobs are byte-identical to master `0319ea67`.
- The dump adds only `SCEFieldTH3:sbnd_dualmap_fwd` and the `dl_vtx_dump` / `sce_field` keys.

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
| MC BNB CV | `aurora_SBND2026A_gen2_BNBLight_prodgenie_corsika_proton_rockbox0p1_sbnd_CV_v10_14_02_03_reco1_sbnd` | `/exp/sbnd/data/users/yuhw/production-prep/r3-mc-cv-2026-09-09/lists/mc.manifest` (1,000 files on `/pnfs/sbn/data_add/sbn_nd/aurora/mc/v10_14_02_03/…/Gen2_2026/CV/reco1/`) | `r6-dlvtx-r26-samples/lists/mc-cv.units.tsv` (990), `mc-cv.fix-471-18-33.tsv` (2) |
| MC nueCC | `aurora_SBND2026A_gen2_BNBLight_prodgenie_corsika_proton_rockbox0p1_sbnd_EX_nuecc_v10_14_02_05_reco1_sbnd` | `/exp/sbnd/data/users/yuhw/production-prep/r3-nuecc-2026-09-10/lists/nuecc.manifest` (999 files, `…/v10_14_02_05/…/Gen2_Exclusive_2026/nuecc/reco1/`) | `lists/mc-nuecc.units.tsv` |
| beam-on | `data_MCP2025C_Fall25-Run1_BNB_FixedDev_bnblight_v10_14_02_reco1_sbnd` (runs 18255, 18259) | `/exp/sbnd/data/users/yuhw/production-prep/r3-beam-on-2026-09-10/lists/beam-on.manifest`; files staged, merged and **frameshifted** in `r3-data-stage-2026-09-09/beam-on/chunk*.root` | `lists/beam-on.units.tsv` |
| beam-off | `data_SBND2026A_gen2_InTime-Run1_v10_14_02_02_reco1_sbnd` | `/exp/sbnd/data/users/yuhw/production-prep/r3-beam-off-2026-09-11/lists/beam-off.manifest`; staged and frameshifted in `r3-data-stage-2026-09-09/beam-off/chunk*.root` | `lists/beam-off.units.tsv` |

- `lists/` is `/exp/sbnd/data/users/yuhw/production-prep/r6-dlvtx-r26-samples/lists/`. Each `*.units.tsv` row is `unit  file  nskip  nevents`.
- MC: one unit per reco1 file, with the event count #26 used. Data: 20-event slices of the staged chunks in art FileIndex order.
- **10 MC CV files (104 events) of #26 no longer exist** on `/pnfs`, and SAM no longer knows them. They are listed in `lists/mc-cv.missing.txt`. MC CV is therefore 13,113 events, not 13,217.
- The SBND2026A `gen2_BNB-Run1` set is blinded and is not used.

## 5. Outputs

```
/exp/sbnd/data/users/yuhw/production-prep/r6-dlvtx-r26-samples/
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
  cfg-proof/                compiled configs and report of the config proof
  validation/               standalone-inference replays (§7)
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
| **this campaign**, MC CV units `f0000`–`f0099`, 1,212 events (build `21562551`; `validation/replay-mccv-f0000-f0099.{txt,json}`) | 1,172 (586 prod + 586 off) | 697 | 475 (worst 2.7e-6) | **0** |

## 8. Change log

- 2026-10-07 21:10 — created. MC CV done; MC nueCC running; beam-on/off queued. Replay of MC CV `f0000`–`f0099`: 1,172 calls, 0 mismatch.
