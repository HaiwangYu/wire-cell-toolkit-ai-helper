# porting_sbndbuild03: P1, P2, P4, P5 results (2026-11-15 UTC)

Go-ahead: issue comment 6889547625 (Haiwang via `prod_polaris`). P3 skipped. Nothing committed to wire-cell-data, no PR from Sne's branch, the production default unchanged.

## P1 — the test build

| item | value |
|---|---|
| branch | `HaiwangYu/wire-cell-toolkit:dv2max-aurora-space-test` (no PR) |
| commit | `ddbc0488` = (master `7710c43b` + `55177882`) + `dsnehadri/dv2max-aurora-space` `a17e6423` |
| conflicts | `sbnd-pr-stage`, `wct-pr`, `wcls-img-clus-matching-pr-lib` (both sides add TLAs; kept both); then `sbnd-pr-stage` again (Sne's default `aurora_space` kept) |
| build | `/exp/sbnd/data/users/yuhw/opt-aur-test` (`scripts/build.sh`: SL7, cvmfs e26, the #43 configure), 7.5 min |
| compiled step-2 config md5 (`scripts/config-md5.sh`) | `r7_cloud` `d390e20f1ba4dac28167775d3ec371b5`, `aurora_space` `a5c3df18a7c6a39b66148042f6f0052b` |
| bundle `bundle.json` sha256 | `51588842984919b5d8146f007287a5e7841be6bbc709263b10cdb39046ff8a74` |

## P2 — tests, master vs the merges (`scripts/run-doctests.sh`, `tables/p2-tests.csv`)

| tree | clus doctest | pyutil doctest | root doctest | `test_dv2max.py` | `test_dv2max_space.py` |
|---|---|---|---|---|---|
| master `7710c43b` | 503/503 | 12/12 | (not built) | 33 OK | — |
| #544 on master `5aa05cf1` | 507/507 | 12/12 | 14/14 | 33 OK | — |
| test `ddbc0488` | **512/512** | **17/17** | 14/14 | 33 OK | **20 OK** (incl. the golden space calls) |

- No failures anywhere.
- Sne's Polaris failures (clus 8, pyutil 1, `aurora/wct/tests.out`) don't happen here, so they come from his environment, not the code.

## P4 — in-chain check, `r7_cloud` vs `aurora_space` (the #43 method)

### Inputs: not in aurora-r2 training

- The 27 #43 step-1 tars: 8 MC CV and 10 MC nueCC reco1 files, plus data nueCC-48 and NCπ0-19 slices.
- **Run numbers:**
  - #43 MC: CV runs 521–7556, nueCC runs 201–281 (`tables/p43-mc-rse.tsv`, from `T_truth_nu`).
  - aurora-r2: BNB 2,100,001–5,000,811 and nueCC 6,700,075–6,734,886 (all 27,196 events of `holdout_r2/holdout_events.tsv`). No run below 100,000.
- **File ids:** none of the 18 #43 reco1 ids appears in the aurora-r2 lists (`dlvtx/aurora-r2/lists/*-units.tsv`, `*-merged-cafs.txt`; 73,136 units).
- **Samples:**
  - #43 MC: official `Gen2_2026/CV` (v10_14_02_03) and `Gen2_Exclusive_2026/nuecc` (v10_14_02_05).
  - aurora-r2: Avinay's `gen2-wct0319` and `gen2-sbnd-ccnue-configL-300k`.

### Runs

- Test build, `vertex_method dv2_split_move`, production step-2 TLAs, plus `dl_vtx_dump_space`.
- 54 runs (27 inputs × 2 bundles): all rc 0, no "DL vertex failed".
- One core per job (taskset) with `GODEBUG=asyncpreemptoff=1` (#45).

### Per call: in-chain vs dump vs standalone (`scripts/percall.py`, `tables/percall-{aur,r7c}.csv`)

| | `aurora_space` | `r7_cloud` |
|---|---|---|
| DL-vertex calls | 229 | 229 |
| input digest rebuilt from the dump (cloud **+ space**) == the digest the in-chain call logged | **229 / 229** | 229 / 229 |
| `n_space` (`T_dlvtx_call`) == space rows rebuilt from `T_dlvtx_space` | 229 / 229 | — |
| space points passed to the network | 1,417,696 | — |
| standalone replay vs in-chain prediction | max 1.6e-5 cm (186 within 1e-5), score diff max 3.0e-8 | max 1.6e-5 cm, 228 with a prediction |

So the space points the network gets in the chain are exactly the `T_dlvtx_space` rows (the training-data writer's), and the in-chain prediction is the standalone one.
- The 1e-5 cm differences are the call-order effect Sne documents ("Repeatability", ~1e-5 cm, 1e-7 in score).
- Sne got 334/339 bit-identical on Polaris; here none are, the same effect at the same size.

### Vertex vs truth (`scripts/perevent.py` → `tables/perevent.csv`, `scripts/summarize.py` → `tables/summary.json`)

Rule (#35/#43):
- per event, the candidate whose DL cloud has a point within 3 cm of the SCE-shifted truth vertex;
- d = |final − truth_reco|;
- only events where every arm has that candidate.

`original` and `v2_r7c` are #43's v2 runs (`opt-pr543v2`) on the same tars.

| events | `original` | `r7_cloud` (test) | **`aurora_space` (test)** | `r7_cloud` (#43 v2) |
|---|---|---|---|---|
| all MC, n = 141 | 0.645 | 0.837 [0.767, 0.889] | **0.957 [0.910, 0.980]** | 0.837 |
| CV, n = 42 | 0.595 | 0.810 | **0.881** | 0.810 |
| nueCC, n = 99 | 0.667 | 0.848 | **0.990** | 0.848 |
| median d, all MC | 0.563 cm | 0.468 cm | **0.334 cm** | 0.468 cm |
| < 2 cm, all MC | 0.752 | 0.915 | **0.979** | 0.915 |

The table shows the fraction with d < 1 cm and 95 % Wilson intervals.
- **aurora_space vs r7_cloud:** 20 events gained (< 1 cm), 3 lost. The 3 lost are all CV: 0.94 → 3.06, 0.48 → 1.02, 0.21 → 1.93 cm.
- **Regression:** `r7_cloud` on the test build is identical to #43 v2, event by event (0 gained, 0 lost). It also agrees with Sne's Polaris in-chain number on r7 fold-0 events (`aurora/wct/report_inchain.md`: r7c 0.847, aur 0.936).

### Selections (MC truth class in the AV; `T_tagger` cuts of #43)

| truth (n) | `original` nue / numu | `r7_cloud` nue / numu | `aurora_space` nue / numu |
|---|---|---|---|
| nueCC (101) | 42 / 23 | 51 / 27 | 50 / 29 |
| numuCC (30) | 0 / 23 | 0 / 22 | 0 / 21 |
| NC (22) | 0 / 2 | 1 / 2 | 0 / 1 |

### Data, nueCC-48 + NCπ0-19 (67 events, 68 calls)

| | generic | nue | numu |
|---|---|---|---|
| `r7_cloud` | 67 | 42 | 6 |
| `aurora_space` | 67 | 42 (no change) | 5 (+1 −2) |

- **Changed events, all numu:**
  - 18255/1/268067: numu 1.277 → 0.519;
  - 18255/1/71372: 1.342 → 0.512;
  - 18255/1/271851: 0.542 → 1.094.
- **The nue selection** is unchanged event by event.

### Cost (27 runs each, same inputs)

| | `r7_cloud` | `aurora_space` |
|---|---|---|
| DV2 call, median / p90 | 0.69 s / 1.0 s | 2.4 s / 6.7 s |
| DV2 total, 229 calls | 164 s | 753 s |
| step-2 CPU total | 3,657 s | 4,150 s (+13 %) |
| peak RSS, median / max | 1,695 / 2,663 MB | 1,984 / 2,800 MB |

## P5 — PR #544 updated on master

| item | result |
|---|---|
| merge | `5aa05cf1` = `b6278234` + master `7710c43b`; the same 3 cfg files, both sides kept. **Pushed** to `HaiwangYu/wire-cell-toolkit:sbnd-wc-flatcaf` (fast-forward `b6278234..5aa05cf1`) |
| doctests | clus 507/507, pyutil 12/12, root 14/14, `test_dv2max.py` 33 OK |
| compiled configs vs `b6278234` (`scripts/p5-config-compare.sh`) | step 2 with `vertex_method=original` (sim, data) and step 1 `wcls-img-clus-matching.jsonnet` (sim, data): **identical** |
| step 2, 27 #43 tars × {`original`, `r7_cloud`}, every tree by value vs #43 v2 (`scripts/compare-trees.py`, `tables/trees-p544-*-summary.csv`) | 54/54 rc 0. Differences, all explained (below) |

The differences:
- `Trun.wct_version` (all).
- #544 review item 8: a segment shared by two showers takes the shower of its T_kine row.
  - `T_segment.shower_id` (5–6 events), `T_overlap.particle_id` (4–5), and downstream `T_pf.kine_index` (3).
  - In 1 event (nueCC 3750 evt 2701), also `T_match` and `T_overlap.in_pf`, the same event as its `particle_id` change.
  - The base of #43 v2, `4b6853d4`, predates the fix.
- `r7_cloud` only: `T_rec_charge` rows 879/880 swapped in nueCC 3750 evt 1844, identical values. This is the point-order swap #43 already recorded (§ re-review).

The test-branch `r7_cloud` run shows the same item-8 differences vs #43 v2 (`tables/trees-test-r7c-vs-v2-summary.csv`), plus the new `T_dlvtx_space` / `n_space` / `space_cluster_id`.

## Locations (sbndbuild03)

- builds: `/exp/sbnd/data/users/yuhw/{opt-aur-test, opt-p544}`; worktrees `wct-aur-test`, `wct-p544`, `wct-master-p2`
- runs: `/exp/sbnd/data/users/yuhw/production-prep/issue47/{runs,runs-p544}/<arm>/<unit>/`
- bundle copy: `/exp/sbnd/data/users/yuhw/production-prep/dv2max-aurora-space/bundle/aurora_space/` (on `WIRECELL_PATH` through `issue47/wcdata`)
