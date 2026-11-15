# porting_sbndbuild03: model copy and code review (2026-11-15 UTC)

## 1. Model copied to sbndbuild03

Destination: `/exp/sbnd/data/users/yuhw/production-prep/dv2max-aurora-space/` (172 MB + bundle 161 MB).
Read-only on Polaris; nothing under `snehadri` was changed.

| path | from |
|---|---|
| `run/` | `$R` = `.../dv2max/runs/aurora_space`: `models/pass{1,2}/f0/seed0/{final.pt,config.yaml,meta.json}`, `ranker_refit/*` (6 files), `config.yaml`, `eval_holdout/*` (3), `preds/fold0_dv2max.csv` |
| `cache/calibration.json` | `.../cache/aurora_space/calibration.json` (x shift 0.29 cm, q ratio 0.2474) |
| `aurora/holdout_r2/` | `.../aurora/holdout_r2/` (4 files) |
| `bundle/aurora_space/` | **Sne's bundle**, `/lus/eagle/projects/neutrinoGPU/snehadri/wct/src/wire-cell-data/dv2max/sbnd/aurora_space/` (see §2) |
| `SHA256SUMS.prefix` | first 16 hex of every file |

sha256 checks:
- pass-1 `final.pt` `a2b53531b7b70700`, pass-2 `final.pt` `8c1ed9326f127d3f`, ranker `e536850272bb3e86`: **all match**.
- The bundle's own `SHA256SUMS`: all 5 files OK.

## 2. Correction to §2 of the issue doc: the in-chain space-point code exists

Sne has a WCT branch **`dsnehadri/dv2max-aurora-space` `a17e6423`**, pushed to his GitHub fork, no PR yet.
It is 6 commits on the PR #543 head `f3767016`:

| commit | what |
|---|---|
| `1e42a41c` | `BeeClusterPoints` + the touch test, cherry-picked from our `sbnd-dlvtx-space-44` (both files blob-identical to `55177882`) |
| `190b4d60` | pyutil: space-point input, bundle format `dv2max-bundle-v2` |
| `7bad7a83` | clus/pyutil: each DL-vertex call collects its space points (`PatternAlgorithms::dv2_collect_space`) and passes them to `DV2_Vertex(..., space, cluster_id)` = **#44 B2** |
| `b8e0fb70` | cfg/sbnd: aurora_space bundle sha256, space-point scope (`dv2_space_pcname '3d'`, `dv2_space_coords` = the Bee layer's) |
| `fb8454d4` | pyutil: space-point golden fixture and validation results |
| `a17e6423` | cfg/sbnd: **aurora_space becomes the default bundle** (r7_cloud stays selectable) |

How it works (read from the diff):
- `TaggerCheckNeutrino::configure` reads the bundle's `space` section from the `DV2_Load` report. `touch_cm > 0` turns space points on; a cloud-only bundle (`r7_cloud`) runs the old call unchanged.
- At each call, `dv2_collect_space` takes the in-scope clusters of the grouping, in increasing cluster id, keeps every cluster with a Bee point within 1 cm of the cloud, and passes all its Bee points with the Bee charge. These are the same functions and order as the `T_dlvtx_space` writer.
- The Python side (`vertexer.py`, `DV2_Vertex.py`) builds the event like `r7/prep_r7_space_cache.add_space`: space points first (raw q, cluster ids by size), then the cloud (dQ × `q_ratio`), and cloud only when there are no space points.

**Sne's bundle** (`bundle.json` sha256 `51588842…`, built 2026-11-14 by `make_bundle.py`):
- `source.pass1.final_pt_sha256` = `a2b53531…`, `source.pass2.final_pt_sha256` = `8c1ed932…`: the same `final.pt` files as issue doc §1. The bundle `.pt` files are the fp32 SWA state dicts taken from them (different sha256, `193ef28d…` / `bd42b0c3…`).
- The ranker is the re-fit (`e5368502…`), with `isotonic_fold0.json` `0ad6bd7f…`.
- The constants match `calibration.json`: x shift 0.29 cm, touch 1 cm, match 1 cm, q ratio 0.2474433, link 3 cm.

So Sne answered Q1–Q3 of the Slack draft himself: these are the files, he ships the re-fit, and he built the bundle.
The bundle is only on Polaris, not in wire-cell-data.

**Sne's own validation on Polaris** (`aurora/wct/`, 2026-11-14):

| check | result |
|---|---|
| toolkit entry point vs offline, all 30,000 hold-out calls (CPU fp32, 1 thread) | < 1 cm: 0.9290 vs 0.9286 offline; 98.7 % of picks within 0.1 cm |
| in-chain space points vs `T_dlvtx_space` (test build = his branch + our `55177882`) | input digest equal 339 / 339 calls |
| standalone replay of the 339 in-chain calls | 334 bit-identical, all within 1.6e-5 cm |
| regression, `original` and `r7_cloud` vs PR #543 reference, 372 events | identical where both finish (336 / 337) |
| in-chain final vertex < 1 cm, 327 r7 fold-0 events | original 0.581, r7_cloud 0.847, **aurora_space 0.936** (+0.089: gained 36, lost 7) |
| CPU per call | median 1.7 s in-chain (r7_cloud 0.53 s) |

Unclear in his logs:
- `tests.out`: `clus_doctest` 8 failed of 508 and `pyutil_doctest` 1 failed of 17. I can't tell whether these fail on master too.
- `leakcheck.out`: some reps have rc=1 on both his build and the reference build.

## 3. Answer: can master + PR #544 run space-point inference in WCT?

**No, as the issue doc says, but for a narrower reason.** Everything needed is written; it's on a branch that isn't in either ref yet.

| item | master `7710c43b` | PR #544 `b6278234` | where it is |
|---|---|---|---|
| DV2-MAX (`r7_cloud`) | yes (PR #543) | **no**: #544 is based on `b7bd2a1a`, before #543 | |
| space input to `DV2_Vertex` (#44 B2) | no | no | Sne's branch `7bad7a83` |
| bundle format v2 + space-aware event builder | no | no | Sne's branch `190b4d60` |
| `BeeClusterPoints` / touch test | no | no | Sne's branch and our `55177882` (same blobs) |
| `T_dlvtx_space` dump | no | no | our `55177882` only |
| `aurora_space` bundle | no | no | Polaris only (wire-cell-data not committed) |

Merges (`git merge-tree`, nothing committed):
- Sne's branch into master: **clean**.
- PR #544 into master: **conflicts** in `sbnd-pr-stage.jsonnet`, `wct-pr.jsonnet`, `wcls-img-clus-matching-pr-lib.jsonnet`. Both sides only add TLAs (#543: `vertex_method`/`dv2_bundle`; #544: `flat_tree`/`truth_match`/`blob_truth`), so the fix is to keep both. GitHub shows #544 as CONFLICTING.
- PR #544 into master + Sne's branch: the same 3 files, same kind.

## 4. Gaps and proposed path

Gaps, in order:
1. PR #544 has to be updated on master (3 trivial cfg conflicts). It is needed anyway, independent of aurora.
2. Sne's branch needs a PR to WireCell (his to open), or a merge into ours.
3. The bundle needs to go into wire-cell-data (`dv2max/sbnd/aurora_space/`, 165 MB).
4. The `T_dlvtx_space` dump (`55177882`) is still only on our fork. It's only needed for training dumps and for checking the in-chain inputs.
5. Owner decision: should `aurora_space` be the SBND default (Sne's `a17e6423`)? CPU per call is about 3× r7_cloud's.

Proposed path, all on sbndbuild03:

| step | what | cost |
|---|---|---|
| P1 | build master + `dsnehadri/dv2max-aurora-space` (clean merge) + `55177882` (3 cfg conflicts, keep both) in a scratch worktree; local bundle via `WIRECELL_PATH` | ~1 h. **The app area is at 56 / 60 GiB**: needs ~10 GB freed first, or a build dir on `/exp/sbnd/data` |
| P2 | pyutil space tests + golden fixture; clus/pyutil doctests on master vs the branch, to see whether Sne's 9 failures are pre-existing | ~15 min |
| P3 | standalone vs our offline: run `validate_space.py` on a sample of hold-out calls, compare with `refit_test_fold0.csv`. The inputs are Sne's cache on Eagle; I'd copy a sample only, e.g. 2,000 calls | ~4 CPU-h for 2,000 calls (6.8 CPU-s mean per call); the full 30,000 calls is ~57 CPU-h, ~2 h on 30 cores |
| P4 | in-chain, method of #43: the #43 sbndbuild03 events, step 2 with `r7_cloud` vs `aurora_space`; call by call, in-chain vs standalone replay and space input vs `T_dlvtx_space`; then vertex vs truth | ~2–3 h on ≤ 30 % of the machine |
| P5 | update #544 on master (resolve the 3 cfg files), rerun the #544 checks | ~1 h + review |
| P6 | if P2–P4 pass: the draft asking Sne to review #544 (and to open his own PR) | — |

P1–P4 are builds and tests only (no code written by us). P5 changes PR #544 and needs the go-ahead.

## 5. Waiting for

Haiwang:
- go-ahead for P1–P4 (and where to free ~10 GB, or to build under `/exp/sbnd/data`);
- whether to do P5;
- whether aurora_space should be the default.
