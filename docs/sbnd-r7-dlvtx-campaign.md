# SBND 2-step chain with the DL-vertex dump: the four #26 samples, run r7

The record of production run **r7**: what ran, with which software, on which inputs, where the outputs are, how to read and check the DL-vertex dump, and what went wrong. **Kept current while the run lasts:** status in §1, change log in §11.

- Tracking issue: [ai-helper #38](https://github.com/HaiwangYu/wire-cell-toolkit-ai-helper/issues/38), logs (d) onward ([doc](../issues/38-sbnd-2step-dlvtx-xin-samples/38-sbnd-2step-dlvtx-xin-samples.md)).
- Machine: `sbndbuild03.fnal.gov`, at most half of it (cores 32–63, ≤ 50 GB of our RSS). **Jobs: ≤ 14 in the day (08:00–20:00 local), ≤ 28 at night**, since 2026-10-08 09:18.
- Output: `/exp/sbnd/data/users/yuhw/production-prep/r7-r26-master-b7bd2a1a/`.

## 1. Status: **complete** (2026-10-08 14:14 CDT)

| sample | events in | units | status | events with `tracking-pr.root` | disk |
|---|---|---|---|---|---|
| MC BNB CV | 13,113 | 990 files + 2 side units | **done** 2026-10-08 02:22 (4.0 h) | **13,112**; only run 471 / subrun 18 / event 33 missing (§9) | 106 GB |
| MC nueCC | 8,877 | 999 files | **done** 2026-10-08 06:58 (4.6 h) | **8,877** | 84 GB |
| beam-on | 10,000 | 502 slices of ≤ 20 | **done** 2026-10-08 10:10 (3.2 h, 14 jobs from 09:18) | **10,000 / 10,000** | 43 GB |
| beam-off | 10,000 | 508 slices of ≤ 20 | **done** 2026-10-08 14:14 (4.1 h at 14 jobs) | **10,000 / 10,000** | 43 GB |

**41,989 of 41,990 events** have a valid `tracking-pr.root`; the one missing is MC CV run 471 / subrun 18 / event 33 (§9). Every unit ended with both steps at rc 0, 0 `DL vertex failed`, and no stub files; the intermittent step-2 crash (§9) was recovered by retries in every case. Run time: 2026-10-07 22:23 → 2026-10-08 14:14 (15.9 h). Disk: 233 GB in total.

| result (all candidates) | MC BNB CV | MC nueCC | beam-on | beam-off |
|---|---|---|---|---|
| neutrino candidates (`T_kine` present) | 6,155 (47.0 %) | 8,426 (94.9 %) | 4,604 (46.0 %) | 971 (9.7 %) |
| DL calls: production / OFF pass | 6,140 / 6,140 | 8,730 / 8,730 | 4,521 / 4,521 | 601 / 601 |
| DL accepted: production / OFF pass | 5,909 / 3,323 | 8,525 / 6,913 | 4,340 / 2,170 | 539 / 49 |
| production pick replaced by the OFF-pass hint (`dual_transferred`) | 3,054 | 2,982 | 2,457 | 516 |
| final vertex vs SCE-shifted truth: median, < 1 cm | 0.84 cm, 52 % | 0.75 cm, 55 % | – (data) | – (data) |
| events with `T_truth_nu` | 13,112 | 8,877 | 0 (data) | 0 (data) |
| step 1 / step 2 CPU per event | 24.0 s / 3.5 s | 27.6 s / 19.1 s | 18.9 s / 3.6 s | 17.1 s / 2.3 s |
| max RSS, step 1 / step 2 | 2.8 GB / 2.7 GB | 3.1 GB / 3.0 GB | 2.9 GB / 2.4 GB | 3.2 GB / 4.8 GB |

Per-sample details: `<sample>/summary.md` (counts, resources, sizes), `<sample>/dlvtx-stats.txt` (DL decisions), `<sample>/events.tsv` (one row per event).

## 2. Software

| component | version | where |
|---|---|---|
| wire-cell-toolkit | **master `b7bd2a1a`** (2026-10-07). Includes PR 536 (the DL dump), Xin's `match_isFC` in `T_tagger` (`0bb05b3c`), and his note `cfg/pgrapher/experiment/sbnd/docs/match-isfc-in-tagger-tree.md` | `github.com/WireCell/wire-cell-toolkit`; checkout `/exp/sbnd/app/users/yuhw/wire-cell-toolkit`, installed to `/exp/sbnd/app/users/yuhw/opt` |
| larwirecell | `dev-v10_14_02_02` **`189ad26`** (`wclsOpHitSource`, `wclsTruthInformationAttacher`, labeler RNG re-seed) | `github.com/HaiwangYu/larwirecell`; MRB tree `/exp/sbnd/app/users/yuhw/larsoft-wct036/v10_14_02/srcs/larwirecell`, libs in `opt/larwirecell/v10_01_28/slf7.x86_64.e26.prof/lib` |
| wcp-porting-validation | `main` **`072505ce`** (step-1 fcls `sbnd/wcls-img-clus-matching{,-data}.fcl`) | `github.com/WireCell/wcp-porting-validation`; `/exp/sbnd/app/users/yuhw/wcp-porting-img` |
| wire-cell-data | `9e2f4b8` + `uboone/weights/XGB_nue_seed2_0923.xml` (md5 `2bdb5cec…`) | `/exp/sbnd/app/users/yuhw/wire-cell-data` |
| DL-vertex weights | `uboone/scn_vtx/t48k-m16-l5-lr5d-res0.5-CP24.pth`, md5 `9cc1413e053c09534edc2d37cdfdc1d4` | wire-cell-data |
| DL runtime | uBooNE UPS `scn v01_00_00` (torch, sparseconvnet; python 3.9.15) + toolkit `pyutil/python/SCN_Vertex.py` in `opt/python` | `sbnd/setup-dlvtx.sh` |
| LArSoft environment | `sbndcode v10_14_02_03 -q e26:prof`, SL7 apptainer | `sbnd/setup-ap.sh` |

**Checks before the start** (#38 log (d)):
- **Build gates** (procedure `docs/sbnd-1step-build-run-validate.md` §1, §1a, §2) pass: 19 libs, no host-glibc symbols, spdlog `v1_14_1`, the build-tree RPATH stripped, all libs resolving from `opt`. larwirecell was not rebuilt, because none of the headers it includes changed.
- **Config proof** (`cfg-proof/report.txt`, `issues/38-*/scripts/cfg-proof.py`): all 43 checks pass.
  - All 8 SBND jobs (step 1, step 2, 1-step flash and hits; sim and data) compile byte-identically to master `0319ea67`. Xin's changes are C++ or default-off.
  - The dump adds only `SCEFieldTH3:sbnd_dualmap_fwd` and the `dl_vtx_dump` / `sce_field` keys.
  - No cfg or data file is shadowed on the runtime path, and every component type is registered by a loaded plugin.
- **Validation against Xin's references** on NCpi0-19 and nueCC-48: §8.

**New in `tracking-pr.root` with this toolkit:** `T_tagger.match_isFC` (Float_t 0/1, per neutrino candidate). It is the containment flag the numu and nue BDTs read; before, it was computed but never written.

## 3. The chain

Our larwirecell 2-step chain (#33). This is not Xin's sbnd-reco1 2-step.
```
step 1  lar --nskip k -n N -c wcls-img-clus-matching.fcl       -s <reco1.root> --no-output             (MC)
        lar --nskip k -n N -c wcls-img-clus-matching-data.fcl  -s <reco1_frameshift.root> --no-output  (data)
        -> qlpctree.tar.gz (imaging, clustering, Q/L matching with hit-rebuilt flashes + light gate,
           all-APA clustering, MC truth tables), mabc.zip (Bee), nugraph.h5
step 2  wire-cell -c pgrapher/experiment/sbnd/wct-pr.jsonnet --tla-str input=qlpctree.tar.gz \
           --tla-str reality=sim|data --tla-code dl_vtx_dump=true
        -> pr_evt<E>/tracking-pr.root (PR, taggers, BDT scores, T_truth_* on MC, T_dlvtx_call / T_dlvtx_cloud),
           mabc-pr.zip (Bee)
```
**Driver:** `issues/38-*/scripts/run-2step-pool.sh` (one unit = one `lar` step 1, then one `wire-cell` step 2 on its tar) and `run-all.sh` (the samples in sequence).

The pool:
- runs the DL environment (§7);
- refuses step 2 unless `SCN_Vertex`, `torch` and `sparseconvnet` import;
- records `dl_fail` per unit;
- retries every failed unit once;
- waits while there is no Kerberos ticket or the machine has < 15 GB available;
- **limits concurrency by time of day**: `DAY_MAXPAR` (default half of `MAXPAR`, here 14) from `DAY_START` to `DAY_END` (default 08–20 local time, every day), `MAXPAR` (28) otherwise. The limit is re-read before every launch; running units are never killed, so a drop takes effect as units finish. A number written to `<sample>/maxpar.override` overrides both, live (delete the file to return to the schedule). Each change is logged in `pool.log` as `concurrency limit now N`.

## 4. Inputs

Exactly #26's events, from its per-event manifests (`<file> <nskip> <run> <subrun> <event>`).

| sample | SAM definition | #26 manifest (sbndbuild03) | unit list |
|---|---|---|---|
| MC BNB CV | `aurora_SBND2026A_gen2_BNBLight_prodgenie_corsika_proton_rockbox0p1_sbnd_CV_v10_14_02_03_reco1_sbnd` | `/exp/sbnd/data/users/yuhw/production-prep/r3-mc-cv-2026-09-09/lists/mc.manifest` (1,000 files, `/pnfs/sbn/data_add/sbn_nd/aurora/mc/v10_14_02_03/…/Gen2_2026/CV/reco1/`) | `lists/mc-cv.units.tsv` (990), `lists/mc-cv.fix-471-18-33.tsv` (2) |
| MC nueCC | `aurora_SBND2026A_gen2_BNBLight_prodgenie_corsika_proton_rockbox0p1_sbnd_EX_nuecc_v10_14_02_05_reco1_sbnd` | `/exp/sbnd/data/users/yuhw/production-prep/r3-nuecc-2026-09-10/lists/nuecc.manifest` (999 files, `…/v10_14_02_05/…/Gen2_Exclusive_2026/nuecc/reco1/`) | `lists/mc-nuecc.units.tsv` |
| beam-on | `data_MCP2025C_Fall25-Run1_BNB_FixedDev_bnblight_v10_14_02_reco1_sbnd` (runs 18255, 18259) | `/exp/sbnd/data/users/yuhw/production-prep/r3-beam-on-2026-09-10/lists/beam-on.manifest`; staged, merged, **frameshifted** in `r3-data-stage-2026-09-09/beam-on/chunk*.root` | `lists/beam-on.units.tsv` |
| beam-off | `data_SBND2026A_gen2_InTime-Run1_v10_14_02_02_reco1_sbnd` | `/exp/sbnd/data/users/yuhw/production-prep/r3-beam-off-2026-09-11/lists/beam-off.manifest`; staged, frameshifted in `r3-data-stage-2026-09-09/beam-off/chunk*.root` | `lists/beam-off.units.tsv` |

- `lists/` is `r7-r26-master-b7bd2a1a/lists/`. Each `*.units.tsv` row is `unit  file  nskip  nevents`.
- MC: one unit per reco1 file, with #26's event count. Data: 20-event slices of the staged chunks, in art FileIndex order. No unit repeats an event number, so the tar's set ident is unique.
- **10 MC CV files (104 events) of #26 no longer exist** on `/pnfs`, and SAM no longer knows them (`lists/mc-cv.missing.txt`). MC CV is therefore 13,113 events, not 13,217.
- FrameShift is applied on data: `frame_apply_at_caf` is 1806–2148 ns on beam-on and 257–2376 ns on beam-off in the smoke logs. It is 0 on MC.
- The staged data chunks (`r3-data-stage-2026-09-09`, 86 GB) must be kept until beam-off is done.
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
                 pr-try1/                      the failed step-2 attempt of a retried unit, kept for the crash study
  <sample>/units.tsv        unit -> input file, nskip, n
  <sample>/events.tsv       per event: unit, ident, run/subrun/event, candidate, DL calls / accepted, cloud points, truth rows, scores, Enu
  <sample>/summary.md       counts, resources, sizes
  <sample>/dlvtx-stats.txt  DL decision statistics
  <sample>/pool.log         one line per unit and pass: ql_rc, pr_rc, dl_fail
  mc-cv-fix/                the two f0686 side units (events 1-30 and 34-50 of that file)
  crash-*.log.gz            logs of step-2 crashes
  cfg-proof/                compiled configs and the config-proof report
  validation/               the comparison with Xin (§8) and the standalone-inference replays (§7)
  run-all.log, memwatch.log the run's timeline and the per-minute resource sampler
```
`<sample>` is `mc-cv`, `mc-nuecc`, `beam-on` or `beam-off`.

`tracking-pr.root` holds `Trun`, `T_kine`, `T_tagger` (with the new `match_isFC`), `T_cluster`, `T_rec_charge`, `T_bad_ch`, `T_proj`, `T_proj_data`, `T_bundle`, `T_flash` and `T_segment`. MC adds `T_truth_nu` / `T_truth_pf`, and the dump adds the two trees of §6. A file without `Trun` would be a stub left by a crashed step 2; `summarize.py` reports these, and r7 has none.

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
| `truth_n`, `truth_all_{nu_idx,pdg,ccnc,E,edep,t,x,y,z,reco_x,reco_y,reco_z}` | MC: every interaction of the event as vectors, so the reader can choose the one that belongs to each candidate (an event can also hold a rockbox interaction) |

### `T_dlvtx_cloud`: one row per network-input point

`runNo`, `subRunNo`, `eventNo`, `nu_index`, `call_index`, `pass` (as above), `ipoint` (0 .. `n_points`-1, the order the network received), `is_vertex` (1 for the leading vertex block), and `x`, `y`, `z`, `q`.

These are the **exact float32 values** the network received, which is what training needs. The final fit points in `T_rec_charge` are not the network input: they come after the refit around the chosen vertex.

To join the two trees, select the cloud rows with the same (`runNo`, `subRunNo`, `eventNo`, `nu_index`, `call_index`):
```python
import ROOT
f = ROOT.TFile.Open('.../pr_evt<E>/tracking-pr.root')
calls = {(c.nu_index, c.call_index): c for c in f.T_dlvtx_call}   # careful: PyROOT reuses the entry object; copy fields you need
pts = {}
for p in f.T_dlvtx_cloud:
    pts.setdefault((p.nu_index, p.call_index), []).append((p.x, p.y, p.z, p.q))
```
### Which vertex is the training target

`T_dlvtx_call` carries several vertices. Only the `truth_*` ones are labels; the others are reconstruction outputs at different stages of the decision:

| vertex | what it is |
|---|---|
| `payload` (top-K voxels) | the network's raw output for this call |
| `trad_*` | the traditional (non-DL) main vertex before the DL step |
| `rerank_*` | this call's own pick after the rerank and score gate, before the dual-chain snap |
| `hint_*` | production rows only: the OFF pass's final vertex, handed over as the snap hint |
| `dl_*` | the DL vertex actually accepted, after snap and veto (if `accepted`) |
| `final_*` | the candidate's final main vertex after the refit; what ends up in the PR output |
| `truth_*` | MC: the true neutrino interaction vertex (GENIE `MCTruth` `Nu()` start), **no SCE** |
| `truth_reco_*` | MC: the same vertex moved by the SBND TrueFwd SCE map (`SCEoffsets_SBND_E500_dualmap_CV_voxelTH3.root`, sbnd_data v01_42_00): **true + SCE displacement**, i.e. where the charge of that point appears in the reconstruction |
| `truth_all_*` | MC: every interaction of the event, raw and SCE-shifted (`truth_all_reco_*`) |

**Use `truth_reco_x/y/z` as the target** (requires `truth_valid == 1` and `truth_sce_applied == 1`). The network input (`T_dlvtx_cloud`) is in the reconstructed frame, which includes SCE, so the label must be in that frame too. Measured on r7 nueCC (2,680 events, 2,385 candidates selected as below): the final vertex lies a median **0.60 cm** from `truth_reco_*` (61 % < 1 cm) but 1.28 cm from the raw `truth_*` (42 % < 1 cm). The median signed offset to `truth_reco_*` is (−0.01, −0.00, +0.06) cm, so there is no residual frame shift (the cluster t0 correction puts x on the truth).

**Match the truth to the candidate.** `truth_*` / `truth_reco_*` are the event's **max-edep** interaction, the same for every candidate of the event. Events often hold more than one interaction (rockbox / dirt neutrinos; in the r7 nueCC check, most selected rows had `truth_n > 1`), and an event can have several candidates. So:
- keep a candidate only if the label belongs to it, e.g. its production cloud has a point within ~3 cm of `truth_reco_*` (what `dlvtx-truth-eval.py` does);
- or choose, per candidate, the `truth_all_reco_*` entry closest to its cloud, with `truth_all_edep > 0`;
- and require the raw vertex inside the active volume (|x| < 200, |y| < 200, 0 < z < 500 cm).

Both clouds of a candidate (`pass` 0, exclusion on; `pass` 1, exclusion off) take the same label. Data files have no truth.

To select training data, #35 log (e) uses: the truth vertex in the active volume, the candidate whose production cloud contains it, and `pass` 0 or 1 for the two clouds (`issues/35-*/scripts/dlvtx-truth-eval.py`).

## 7. Validating the dump: WCT-integrated vs standalone inference

**The idea.** The network output recorded in production (`payload`) must be reproduced by calling the same Python entry point on the recorded cloud, outside WCT. That entry point is `SCN_Vertex.SCN_Vertex` from toolkit `pyutil/python/SCN_Vertex.py`, which `WCPPyUtil::SCN_Vertex` imports. The check uses the same weights file and the same `top_k`. If it passes, the dumped cloud is exactly the network input, and a model trained or evaluated standalone on `T_dlvtx_cloud` sees what production sees.

**Tool:** `issues/35-sbnd-dl-vertex-train-infer/scripts/dlvtx-replay.py`, run on sbndbuild03 in SL7 with the production environment:
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
- **Pitfall:** without `setup-dlvtx.sh` (or when it is sourced in a fresh `bash -c` without re-sourcing `setup-ap.sh`), production logs `DL vertex failed: … No module named 'SCN_Vertex'`, falls back to the traditional vertex, and still exits 0. The pool records the count per unit in `pr/dl_fail`. It is 0 for every unit of r7.

**Companion tools:**
- `dlvtx-stats.py`: DL decision statistics per pass, and on MC the distances of the traditional, DL and final vertices to the SCE-shifted truth.
- `dlvtx-call-diff.py`: per-call detail when a replay is not exact.

**Results:**

| sample (r7, master `b7bd2a1a`) | calls | exact | equivalent | MISMATCH |
|---|---|---|---|---|
| MC CV units `f0000`–`f0099`, 1,212 events (`validation/replay/mccv-f0000-f0099.{txt,json}`) | 1,172 | 697 | 475 (worst 2.7e-6) | **0** |
| MC nueCC units `f0000`–`f0099` (`validation/replay/nuecc-f0000-f0099.{txt,json}`) | 1,758 | 724 | 1,034 (worst 6.1e-6) | **0** |
| beam-on units `k00_*`, `k01_*` (`validation/replay/beamon-k00-k01.{txt,json}`) | 1,790 | 1,181 | 609 (worst 1.5e-6) | **0** |
| beam-off units `k00_*`, `k01_*` (`validation/replay/beamoff-k00-k01.{txt,json}`) | 220 | 208 | 12 (worst 2.7e-7) | **0** |
| **total, r7** | **4,940** | 2,810 | 2,130 | **0** |
| for reference: #35 on Aurora (MC-9, NCpi0-19, nueCC-48, gen2 CV 1006) | > 2,000 | – | – | 0 |

## 8. Validation against Xin's references

**References.** Xin's toolkit `469ae3be` is the same code as `b7bd2a1a`, run on wcgpu1. Files: `/nashome/y/yuhw/sbnd-data/sbnd_xin/work-{ncpi0,nuecc48}-d133pr/pr_evt<E>/tracking-pr.root`, 19 NCpi0 + 48 nueCC data events. They are his PR stage only, run on his existing 2026-09-25 (`m0925`) charge-light matching products.

**Ours.** The full r7 chain (dump on) on the same events, from Lynn's frameshifted files, in `validation/`.
- Every branch of every tree is compared per event (`evt-branch-diff.py`, NaN = NaN).
- A branch whose largest relative difference is ≤ 1e-6 counts as float noise.

| comparison | NCpi0 (19) | nueCC (48) |
|---|---|---|
| ours (production step 1) vs Xin | 9 float noise only, 10 also flash timing | 30 float noise only, 12 also flash timing, 6 with physics differences |
| ours with the **old flash rule** in step 1 vs Xin | **19 float noise only** | **42 float noise only**, 4 with physics differences (2 not compared: crashed chunk) |
| our production vs our old-flash run (same machine) | – | 30 bit-identical, 13 flash timing only, 3 changed by the flash rule |

- **Float noise:** `T_rec_charge` `q`, `reduced_chi2` and fit points at ~1e-13 relative. This is the cross-machine residual recorded in `docs/sbnd-1step-build-run-validate.md` §7.
- **Flash timing** (`T_flash.time_us`, `T_cluster.cluster_t0_us` / `flash_time_us`): master's new `SBNDOpFlashFinder` prompt-time rule (`4afd5cac`, deploy note change 1) is in our step 1. Xin's products predate it.
  - With the old rule (`prompt_min_* = 0`, deploy note §3.3) all of it vanishes.
  - Events 81597 and 350186, whose candidate cluster changed, then also match Xin. 131357 changes with the rule too.
- **Still different with the old rule:** nueCC 90055 (`ssm_offvtx_energy`, 3e-4 rel), 239794 (`hol_2_ncount` 2 → 1), 131357 (Enu 1e-4 rel, one segment) and 433451 (vertex moved ~mm, Enu 3 %).
  - Our two runs agree on 90055, 239794 and 433451, so the difference is systematic, not run-to-run.
  - It is consistent with cross-machine float differences seeding discrete choices.
  - Pinning it further needs Xin's `m0925` step-1 products on this machine. **Open.**

## 9. Known failures

**Deterministic: MC CV run 471 / subrun 18 / event 33** (#26 §5a). Step 1 dies on it every time: nanoflann recursion in `clustering_connect1`, a silent stack overflow. Its file (`f0686`) fails in the main pool. The other 13 events run as side units in `mc-cv-fix/`. Event 33 is the only event of the campaign without output, as in round 3.

**Intermittent: the step-2 (PR) crash.** It is not tied to an event: the same tar crashes on some runs and not on others, and the completed runs agree bit-for-bit.

| sample | units crashed on the first pass | recovered by the retry | ≈ rate |
|---|---|---|---|
| MC BNB CV | 1 (`f0068`) | 1 | 1 per 13,000 events |
| MC nueCC | 16 (14 × SIGSEGV, 1 × rc 11, 1 × abort) | 15 + 1 on a third attempt (`f0882`) | 1 per 550 events |
| beam-on | 4 (`k05_030`, `k05_042`, `k06_046`, `k07_006`; all SIGSEGV) | 4 (`k06_046` on the third run) | 1 per 2,500 events |
| beam-off | 0 | – | – |

- **Crash sites move:** `TrackFitting::update_association` (`TrackFitting.cxx:3702`, `:3734`), `TrackFitting.cxx:1028`, and `Steiner::Grapher::find_peak_point_indices` (`SteinerGrapher.cxx:1027`).
- **Common signature:**
  - peak RSS ~4.5 GB, against a median of 1.5 GB;
  - often, just before the crash, a failed DL Python call (`new(): invalid arguments`, `unknown parameter type`);
  - a much higher rate on the larger nueCC events.
- Together this points to a **runaway allocation in the PR stage**, reached via `improve_vertex` → `do_multi_tracking`, rather than random memory corruption.
- **Reproducer:** `validation/oldflash/nuecc48/c2/ql/qlpctree.tar.gz` with production step 2 crashed in 3 of 4 runs.
- **Logs:** `crash-*.log.gz` and `<sample>/<unit>/pr-try1/wct.log.gz`.
- Not filed upstream; for us to fix later.

**Machine outage, run r6:** sbndbuild03 went down around 16:00 on 2026-10-07, with machine-wide memory exhaustion (MemAvailable 2 GB) from other users. That is why the pool now waits while the machine has < 15 GB available.

## 10. History of this campaign

| run | toolkit | samples | outcome |
|---|---|---|---|
| r5 | `sbnd-dlvtx-35` `78f81c64` | the #30 samples (MC CV 2,017, nueCC 2,001, beam-off 1,000), by mistake | done 5,018 / 5,018; kept in `r5-dlvtx-xin-samples/` (40 GB) pending a decision |
| r6 | `sbnd-dlvtx-35` `21562551` (PR 536 review fixes) | the #26 samples | stopped 2026-10-07 after MC CV and 125 nueCC units, when Xin's update reached master. Outputs deleted (~119 GB); lists, logs and config proof kept in `r6-dlvtx-r26-samples/` |
| **r7** | **master `b7bd2a1a`** | the #26 samples | this document |

## 11. Change log

- 2026-10-08 14:14 — **run complete.** beam-off done: 10,000 / 10,000 events, 971 candidates (9.7 %), 0 step-2 crashes. Replay `k00`–`k01`: 220 calls, 0 mismatch. Campaign total 41,989 / 41,990 events, 233 GB.

- 2026-10-08 — §6: which vertex to use as the training target (`truth_reco_*`, SCE-shifted), with the r7 nueCC frame check.

- 2026-10-08 10:40 — beam-on done: 10,000 / 10,000 events, 4,604 candidates (46.0 %); 4 first-pass step-2 crashes, all recovered. Replay `k00`–`k01`: 1,790 calls, 0 mismatch. beam-off running.

- 2026-10-08 09:18 — **daytime limit:** at most 14 jobs from 08:00 to 20:00, 28 at night, at Haiwang's request (people use the node in the day). The beam-on pool was stopped at 09:10, its 27 running units were allowed to finish, and beam-on resumed at 09:18 (411 / 502 units done) with the new `run-2step-pool.sh`.

- 2026-10-08 07:51 — document rewritten for r7 (was `sbnd-r6-dlvtx-campaign.md`, now a pointer here). beam-on at 183 / 502 units, all clean.
- 2026-10-08 07:30 — MC nueCC done: 8,877 / 8,877 events. 16 first-pass step-2 crashes, all recovered. Replay of `f0000`–`f0099`: 1,758 calls, 0 mismatch. beam-on started 06:58.
- 2026-10-08 02:22 — MC BNB CV done: 13,112 / 13,113 events. Replay of `f0000`–`f0099`: 1,172 calls, 0 mismatch.
- 2026-10-07 22:23 — r7 started on master `b7bd2a1a`, after the validation of §8. Run r6 stopped and its outputs deleted (§10).
- 2026-10-07 21:10 — first version of this record, for run r6.
