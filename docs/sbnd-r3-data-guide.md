# SBND Wire-Cell "img-clus-match-tag-pr" round-3 datasets — where they are and what they are

For colleagues who want to *use* the outputs. Tracking issue: [ai-helper #26](https://github.com/HaiwangYu/wire-cell-toolkit-ai-helper/issues/26).
Everything is under `/exp/sbnd/data/users/yuhw/production-prep/` on the SBND data disk (group `sbnd`, read in place — please do not copy 200 GB around). **Validation output, not a production release**: no stability guarantee; the version pins are in §5.

_Last updated 2026-09-11 01:30 CDT — MC BNB CV, MC nueCC and beam-on done; beam-off running._

## 1. Status

| sample | events | status | output dir | size |
|---|---|---|---|---|
| **MC BNB CV** (BNB ν + cosmics, GENIE CV) | **13,216** / 13,217 | **done** 2026-09-10 | `r3-mc-cv-2026-09-09/run/` | 73 GB |
| **MC nueCC** (intrinsic νe CC, filtered) | **8,877** / 8,877 | **done** 2026-09-10 19:58 | `r3-nuecc-2026-09-10/run/` | 60 GB |
| **beam-on data** (BNB light trigger, Run 1, runs 18255/18259) | **10,000** / 10,000 | **done** 2026-09-11 01:19 | `r3-beam-on-2026-09-10/run/` | 15 GB |
| **beam-off data** (off-beam light trigger, Run 1) | 10,000 | **running** (started 2026-09-11 01:23) | `r3-beam-off-2026-09-11/run/` | ~15 GB expected |

The one missing MC CV event (run 471 subrun 18 event 33) crashes the clustering deterministically in both this chain and Xin's standalone chain; it is an open toolkit defect (#26 §5a), not a data problem.

## 2. What the inputs are

| sample | source | selection |
|---|---|---|
| MC BNB CV | SAM `aurora_SBND2026A_gen2_BNBLight_prodgenie_corsika_proton_rockbox0p1_sbnd_CV_v10_14_02_03_reco1_sbnd` (749,339 files, 9.9 M events; `/pnfs/sbn/data_add/sbn_nd/aurora/mc/v10_14_02_03/…/Gen2_2026/CV/reco1/`) | 1,000 of those files (the same list as the earlier #16 campaign, `lists/files-1000.lst`; membership verified with samweb), all 13,217 events |
| MC nueCC | SAM `aurora_SBND2026A_gen2_BNBLight_prodgenie_corsika_proton_rockbox0p1_sbnd_EX_nuecc_v10_14_02_05_reco1_sbnd` (14,231 files, 124 k events; `…/v10_14_02_05/…/Gen2_Exclusive_2026/nuecc/reco1/`) | 1,000 of those files (same as #19, `lists/files-1000.lst`), all 8,877 events |
| beam-on | SAM `data_MCP2025C_Fall25-Run1_BNB_FixedDev_bnblight_v10_14_02_reco1_sbnd` (runs 18255, 18259; 1,820 files) | 220 random files (seeded), merged + **FrameShift** added, first 10,000 events in art order — 7,270 from run 18255, 3,667 from 18259 (cut at 10k) |
| beam-off | SAM `data_SBND2026A_gen2_InTime-Run1_v10_14_02_02_reco1_sbnd` (49,020 files, 2.2 M events, Run 1) | 240 random files (seeded), merged + FrameShift, first 10,000 events — 94 runs |

Data inputs are staged as frameshifted 1,000-event artROOT chunks in `r3-data-stage-2026-09-09/{beam-on,beam-off}/chunkNN.root` (+ `lists/` with the exact file selections and SAM definition names). The `*.manifest` files there list every event: `<file> <nskip> <run> <subrun> <event>`. **Gen2 data must have the `FrameShift` product before Wire-Cell sees it** — the staged chunks do; the raw reco1 files on `/pnfs` do not.

## 3. What the chain is

One LArSoft job per event (`lar -c wcls-img-clus-matching-xin.fcl` for MC, `…-xin-data.fcl` for data) running the Wire-Cell toolkit end to end inside `larwirecell`:

signal-processed reco1 wires (`dnnsp`) → 3D imaging → clustering → optical-flash / charge matching (Q/L) → the full pattern-recognition chain (Steiner, TGM / STM / FC cosmic taggers, neutrino tagger, DL vertex, ν<sub>μ</sub>/ν<sub>e</sub> BDTs, track fitting, kinematics) — the same algorithms and the **same operating point** as Xin Qian's standalone 2-step production, verified bit-identical on 308 data events and on every 10–18-event pilot of these samples (#24, #26). DL vertex: uBooNE-trained SCN net (`uboone/scn_vtx/t48k-m16-l5-lr5d-res0.5-CP24.pth`); BDTs: the 41 uBooNE `*.xml` weights. Data and MC differ only by the per-TPC point shift, the Q/L light scale, the FrameShift, and product labels (#26 audit).

## 4. What the outputs are — per event, named by `(run, subrun, event)`

```
<sample>/run/
  tracking-pr/tracking-pr_r<run>_s<sub>_e<evt>.root   reconstruction summary (ROOT trees, see below)
  bee/bee_r<run>_s<sub>_e<evt>.zip                     Bee event display bundle (JSON layers)
  summary-merged.csv  (or summary.csv)                 one row per event: rc, wall_s, peak_rss_kb, sizes, audit, rse_check
  logs/                                                 per-worker logs; fail_*.log / audit_*.txt for the bad ones
```

**`tracking-pr.root`** — a *candidate* event (a neutrino candidate was reconstructed) has 8 trees: `Trun`, `T_bad_ch`, `T_cluster`, `T_proj`, `T_proj_data`, `T_rec_charge`, `T_tagger`, `T_kine`. A non-candidate has only `Trun`, `T_bad_ch`, `T_cluster`, `T_proj`.
- `T_kine` (34 branches): `kine_reco_Enu`, per-particle kinematics, `kine_pio_*`, …
- `T_tagger` (1,229 branches): every cosmic/neutrino tagger flag and BDT input, plus the outputs `numu_score`, `nue_score`, `cosmict_flag_*`, `numu_cc_flag`, …
- `T_rec_charge`: the reconstructed 3D charge points — `x y z q nq chi2 ndf pu pv pw pt reduced_chi2 flag_vertex flag_shower rr cluster_id real_cluster_id sub_cluster_id particle_id` (cm, e⁻).
- `Trun`: run/subrun/event and the trigger/timing words.

**Bee zip** — `data/<i>/<i>-<layer>.json`, one index per event (single-event zips here, so `i=0`). Layers: `img-global`, `clustering-apa{0,1}-face0`, `clustering-global`, `clustering-pr-global` (post-PR clusters), `shower_track-global`, `track_fit-global`, `vertices-global`, `mc` (the reconstructed neutrino summary; on MC also the truth tree), `op` (flashes), `channel-deadarea-*`, `tagger_{tgm,stm,fc,lm}` (tagger verdicts per cluster); MC only: `truth_*`, `sed-*` (energy deposits). Upload a zip at <https://www.phy.bnl.gov/twister/bee/> to view. Pre-uploaded 10-event samplers are linked from #26.

No nugraph `.h5` this round (switched off; it was an unvalidated side output).

### Reading them without getting bitten
1. **Select candidates on `kine_reco_Enu > 0`** (or on the presence of `T_kine`), never on file size.
2. **`T_tagger` / `T_kine` / `T_rec_charge` carry no run/subrun/event** — only `Trun` does. If you `TChain` them you lose event identity; join on the filename instead.
3. **`nue_score` is a discretized BDT output** saturating at −15.0000 / −4.3009 / +4.3009; −15 means background-like, not "not evaluated".
4. Population numbers to sanity-check against (this round): MC CV candidates 45.4 %, `nue_score > 0` 0.59 %; MC nueCC candidates 93.6 %, `nue_score > 0` 53.2 %; beam-on candidates 44.4 %, `nue_score > 0` 0.35 %.

## 5. Version pins

| | |
|---|---|
| wire-cell-toolkit | `master-2026-09-08+yuhw` @ `0ad64223` (PR [WireCell/wire-cell-toolkit#530](https://github.com/WireCell/wire-cell-toolkit/pull/530)) |
| larwirecell (SBND fork, `WireCellAIML` labeler) | MRB tree `larsoft-wct036/v10_14_02/srcs/larwirecell`, installed to `/exp/sbnd/app/users/yuhw/opt` |
| job config | `wcp-porting-validation` `sbnd/wcls-img-clus-matching-xin{,-data}.fcl` + `.jsonnet`, operating point `sbnd/pr-operating-point.jsonnet` @ `e100a631` |
| sbndcode | `v10_14_02_03` (e26, SL7 container) |
| Xin's reference | `ref/prod-2026-09-08` (prod0908); our chain reproduces it bit-for-bit on data (#24) |

## 6. Change log
- 2026-09-11 01:30 — beam-on done (10,000/10,000, no failures); beam-off launched.
- 2026-09-10 20:25 — nueCC done (8,877/8,877, no failures); beam-on launched.
- 2026-09-10 15:05 — MC input SAM definitions named (our 1,000-file lists are subsets of the two `aurora_SBND2026A_gen2_BNBLight_…` reco1 definitions).
- 2026-09-10 14:35 — first version: MC CV done, nueCC running, data staged (beam-on re-selected from FixedDev, beam-off from SBND2026A InTime).
