# prod_aurora: Track 2 results (2026-11-15 UTC)

Go-ahead: issue comment 6889547625 (Haiwang via `prod_polaris`).
- Nothing was committed to wire-cell-data, and no PR was opened from Sne's branch.
- The production default and the production install `$Y/opt` are unchanged.
- Queue: debug only. Total ≈ 1.0 node-h (7 jobs, listed below).

## 1. Same build

| item | porting_sbndbuild03 | prod_aurora (Aurora) |
|---|---|---|
| commit | `ddbc0488f23fac76ea4b3c2b889032125111b8e5` | the same (worktree `$Y/wct-dv2test` → `$Y/opt-dv2test`, job 9091020) |
| compiled step-2 config, `r7_cloud` | `d390e20f1ba4dac28167775d3ec371b5` | **`d390e20f1ba4dac28167775d3ec371b5`** |
| compiled step-2 config, `aurora_space` | `a5c3df18a7c6a39b66148042f6f0052b` | **`a5c3df18a7c6a39b66148042f6f0052b`** |
| bundle `bundle.json` sha256 | `51588842…8a74` | **`51588842984919b5d8146f007287a5e7841be6bbc709263b10cdb39046ff8a74`**; `SHA256SUMS` 5/5 OK |

- The md5s come from porting's `config-md5.sh`.
- Without the `vertex_method` and `dv2_bundle` TLAs, which is how production `aurora/bin/step2.sh` runs, the config is also `a5c3df18…`. So the unchanged production step 2 runs aurora_space on this build.
- The bundle is a read-only copy from Polaris, found through `WIRECELL_PATH`.

Doctests, run with the run setup:
- `clus` 512 passed, 0 failed, 1 skipped;
- `pyutil` 17 passed, 0 failed.

Python in SL7:
- Python 3.9.15, numpy 2.0.2, torch 2.6.0 (from the scn product);
- scipy 1.13.1 (manylinux2014 wheel);
- lightgbm 4.6.0. The PyPI wheel needs glibc 2.27, so `lib_lightgbm.so` was built from the 4.6.0 sdist with UPS gcc 12.1 (job 9091003; `scripts/build-lightgbm.pbs`).
- All of these are in `products/dv2-extra-py39/site`, added only by `scripts/setup-dv2test.sh`.

## 2. In-chain on Sne's hold-out (500 units)

**Units:** `tables/holdout500-units.tsv`, a seeded draw from `aurora/holdout_r2/holdout_units.tsv`:
- 150 of 360 BNB units (one BNB hold-out unit has no step-1 tar: `e588-8e0c-a689-da26`, PARTIAL);
- 350 of 1,856 νe units.

**Inputs:** the aurora-r2 step-1 tars on Flare (`production-prep/dlspace/<sample>/node<k>/<unit>/ql/all/qlpctree.tar.gz`).

**Run:** production `step2.sh`, MC, with `DLVTX_SPACE=true` and one `DV2_HOOK_LOG` per unit. Debug job 9091099, 1 node × 64 units in parallel, 29 min.
- 500/500 units rc 0, 9,430 events, 0 "DL vertex failed".
- 7 units first crashed (rc 134 ×4, rc 139 ×3; the known random step-2 crash class) and passed on their one retry.
- How the retry happened: I edited the driver script while the job was running, bash re-read it, and the unit loop ran a second time. That second pass skipped the finished units, so it behaved exactly like the planned single retry.

**Join:** `scripts/ana_calls.py`.
- Every `T_dlvtx_call` row's input sha1 is rebuilt from the dump: the cloud from `T_dlvtx_cloud` per (nu_index, call_index, pass), plus the `T_dlvtx_space` rows of its `space_cluster_id` clusters.
- That digest is joined to the hook record: **5,277 / 5,277 calls**, 0 hook records left over.
- The in-chain pick is moved to the label frame: x − sign(x) · 0.29 cm.

**Compare:** `scripts/compare_refit.py`, against `ranker_refit/refit_test_fold0.csv`.
- Labels: `label_xyz` per key from Sne's export, read only from the calls tables (`scripts/labels_from_export.py`).
- Classes: from `cache/aurora_space/index.csv`, fold 0.
- Population: every refit key of a labelled event in the 500 units.
- **Pass 1 is never called in-chain:** `dv2_split_move` skips the dual-chain OFF pass. So the comparison is pass 0, the figure's pass. All 4,494 pass-0 keys were found in-chain.

### < 1 cm vs label, pass 0

| class | n | in-chain | offline (refit) | in-chain − offline [95 % CI, bootstrap over events] | figure (15,000 events) | figure value inside the in-chain Wilson 95 % CI? |
|---|---|---|---|---|---|---|
| all | 4,494 | **0.9232** | 0.9232 | 0.0000 [−0.0009, +0.0009] | 0.929 | |
| BNB | 3,066 | 0.9093 | 0.9093 | 0.0000 [−0.0013, +0.0013] | 0.908 | |
| νe sample | 1,428 | 0.9531 | 0.9531 | 0 | 0.950 | |
| **νe CC** | 1,421 | **0.9557** | 0.9557 | 0 | **0.951** | yes, [0.9437, 0.9652] |
| **νμ CC** | 2,447 | **0.9591** | 0.9591 | 0.0000 [−0.0016, +0.0016] | **0.955** | yes, [0.9505, 0.9663] |
| **NC** | 626 | **0.7093** | 0.7093 | 0 | **0.719** | yes, [0.6725, 0.7435] |

### Pick agreement, in-chain vs offline (label frame), 4,494 calls

| | value |
|---|---|
| within 0.1 cm | **98.82 %** (Sne's toolkit-vs-offline on all 30,000 calls: 98.7 %) |
| within 1 cm | 99.91 % |
| median / p99 | 0.00034 cm / 0.109 cm |
| > 1 cm (pick flips) | 4 calls, all νμ CC, scores 0.24–0.51 |

The 4 flips:
- in-chain gains 2: 25.96 → 0.16 cm and 1.96 → 0.45 cm;
- in-chain loses 2: 0.70 → 2.12 cm and 1.19 → 6.01 cm (the second was a miss either way).

So the net effect on efficiency is 0, and 49 of the 53 calls with picks more than 0.1 cm apart land on the same side of 1 cm.

Calibrated score |in-chain − offline|: median 0, max 0.20 (in a flip).

There are 104 more in-chain pass-0 calls on these events with no refit key. These are other neutrino candidates (nu_index 1: 68, nu_index 2: 1, and 35 nu_index-0 calls of events whose labelled call is another candidate). The export keeps only labelled calls.

CPU per call (hook `ms`): median 1.51 s, mean 2.27 s, p95 6.5 s.

## 3. Cross-check with porting on nueCC-48 + NCπ0-19

**Inputs (Aurora):** the issue-#7 step-1 tars, `production-prep/selected-r2/full/{nuecc/ql/c0–c4, ncsb/ql/c0–c1}`.
- Aurora step 1: toolkit `d06a47d7` + larwirecell `ad5d942`.
- porting used its #43 step-1 tars.

**Run:** step 2 with `reality=data`, debug job 9091133. 7/7 rc 0, 67 events, 68 calls, 0 DL failures.

Per call, joined on (run, subrun, event, nu_index, pass): `tables/data-cross-porting.csv` (`scripts/cross_porting.py`).

| | value |
|---|---|
| calls Aurora / porting / matched | 68 / 68 / 68 |
| **same input digest** (cloud + space) | **68 / 68** |
| pick distance, same digest (raw frame) | max 1.6e-6 cm |
| calibrated score, same digest | identical (max \|diff\| 0) |

So the two machines' step-1 outputs give byte-identical DV2 inputs for all 68 data calls, and the predictions agree.

## 4. Recomputation of porting's P4 headline numbers

Recomputed from `porting_sbndbuild03/tables/perevent.csv` with my own script (`scripts/recheck_porting_p4.py`, output `tables/recheck-porting-p4.json`). The rule is events where every arm has a d_vtx; Wilson 95 % CI.

| | porting | prod_aurora | |
|---|---|---|---|
| all MC < 1 cm, n = 141: `r7_cloud` / `aurora_space` | 0.837 [0.767, 0.889] / 0.957 [0.910, 0.980] | 0.837 [0.767, 0.889] / 0.957 [0.910, 0.980] | **agree** |
| CV (42) / nueCC (99), `aurora_space` | 0.881 / 0.990 | 0.881 / 0.990 | agree |
| `original` / `v2_r7c`, all MC | 0.645 / 0.837 | 0.645 / 0.837 | agree |
| median d, < 2 cm, all MC (`aurora_space`) | 0.334 cm, 0.979 | 0.334 cm, 0.979 | agree |
| `aurora_space` vs `r7_cloud`: gained / lost | 20 / 3 (all CV: 0.94 → 3.06, 0.48 → 1.02, 0.21 → 1.93) | 20 / 3, the same 3 events | agree |
| `r7_cloud` test vs #43 v2, events changed | 0 | 0 | agree |
| MC selections, truth nueCC (101) nue/numu: orig / r7c / aur | 42/23, 51/27, 50/29 | the same | agree |
| truth numuCC (30), NC (22) | 0/23, 0/22, 0/21; 0/2, 1/2, 0/1 | the same | agree |
| data generic / nue / numu: `r7_cloud` → `aurora_space` | 67/42/6 → 67/42/5 | 67/42/6 → 67/42/5 | agree |
| data changed events | 18255/1/268067, 71372 (numu 1 → 0), 271851 (0 → 1) | the same 3, same numu scores | agree |

porting's per-call tables (`percall-{aur,r7c}.csv`, 229 calls each):
- digest in hook 229/229 in both;
- aurora_space space-point counts dump = tree = hook, 229/229;
- standalone vs hook max 1.6e-5 cm.

**Agree.**

## 5. Conclusion for Track 2

- **In-chain = offline:** aurora_space in-chain on Aurora reproduces Sne's offline hold-out result on 4,494 hold-out calls. The < 1 cm efficiency is identical to the refit's in every class, and the picks agree within 0.1 cm for 98.8 % of calls.
- **Target met:** the figure's values (νe CC 0.951, νμ CC 0.955, NC 0.719) all lie inside this subset's 95 % CIs.
- **Cross-machine:** on data, Aurora and sbndbuild03 give identical inputs (68/68 digests) and identical predictions.

## Jobs (all debug, `neutrinoGPU::WireCell_aurora`)

| job | what | wall |
|---|---|---|
| 9091003 | lightgbm 4.6.0 build + import / bundle-load test | 0:03 |
| 9091020 | test build `ddbc0488` + doctests | 0:11 |
| 9091059 | smoke 1 (input path bug in my driver: `$Y` not exported) | 0:02 |
| 9091072 | smoke 2 (`DV2_HOOK_LOG`/`WC_EVT_SUBDIR` not passed into the container: `PASS_ENV`) | 0:03 |
| 9091079 | smoke 3, 4 units: pass | 0:03 |
| 9091099 | hold-out, 500 units | 0:29 |
| 9091133 | data nueCC-48 + NCπ0-19 | 0:08 |

## Files

- **`tables/`:** `holdout500-percall.csv` (per refit key: in-chain/offline distances to the label, pick distance, digest, scores), `holdout500-inchain-calls.csv` (every in-chain call), `holdout500-summary.json`, `data-inchain-calls.csv`, `data-cross-porting.csv`, `recheck-porting-p4.json`, and the unit lists.
- **`scripts/`:** the driver (`node-units.sh`, `run-units.pbs`, `setup-dv2test.sh`), the builds, and the analysis scripts.
- **Run outputs on Flare** (not committed): `production-prep/dv2max-aurora-space/runs/{holdout500,data}/`.
