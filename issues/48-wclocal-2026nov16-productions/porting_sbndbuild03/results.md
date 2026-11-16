# Issue 48, WCLocal2026Nov16-FermiGrid: porting_sbndbuild03 results

Agent: `porting_sbndbuild03` (sbndbuild03 + FermiGrid). Request: prod_polaris relaying Haiwang, 2026-11-16.

## Release (P0)

| item | value |
|---|---|
| area | `/exp/sbnd/data/users/yuhw/wclocal-nov16/` |
| WCT | `wct/` = worktree at tag **`0.38.0`** (`c935e30d`), built into `opt/` (`scripts/build.sh`, the #43 configure). `WIRECELL_VERSION` = `HEAD-0.38.0` (the `Trun.wct_version` string) |
| larwirecell | `opt/larwirecell/` = copies of the deployed `sbnd-wc-flatcaf` **`ad5d942`** libraries, RPATH `/exp/sbnd/app/users/yuhw/opt/lib` → `opt/lib`. Not rebuilt: from `4b6853d4` (their build) to `0.38.0` the util/iface/aux headers change only additively (new `IDriftPlanes.h`, a new `WireSchema` function, inline `IHydraNode` bodies), and none of the 67 WCT headers larwirecell includes changed. P2 tests step 1 end to end |
| wire-cell-data | `/exp/sbnd/app/users/yuhw/wire-cell-data` fast-forwarded to `99c6497` (#8); `aurora_space/bundle.json` sha256 `51588842…` |
| DV2 Python | `pydv2/` (125 MB): lightgbm 4.6.0 + threadpoolctl (= `pyenv-dv2`) + **scipy 1.13.1** (copied from the wire-cell-python venv). torch 2.6.0 / numpy 2.0.2 from the CVMFS scn product |
| env | `scripts/setup-wcl.sh`: the production `setup-fnal-run.sh`, then every `/exp/sbnd/app/users/yuhw/opt[/…]` path entry → the release `opt`, `wire-cell-toolkit/cfg` → `wct/cfg`, `pydv2` prepended, `GODEBUG=asyncpreemptoff=1` |

**R1 finding: scipy.** The DV2 code imports `scipy.spatial` / `scipy.sparse`. scipy is in neither the scn product nor any UPS product on `PYTHONPATH`. Locally the embedded interpreter finds it only because `python3` on `PATH` is the wire-cell-python venv, which CPython detects through `pyvenv.cfg`. A grid worker has no venv, so without `pydv2` every job would fail when the vertexer is loaded.

**Doctests** (`scripts/run-doctests.sh`, release env): all match the gate.

| suite | result |
|---|---|
| clus | 512/512 (1 skipped) |
| pyutil | 17/17 |
| root | 17/17 |
| `test_dv2max.py` | 33 OK |
| `test_dv2max_space.py` | 20 OK |

**Compiled step-2 config md5** (`scripts/config-md5.sh`, `tables/p0-config-md5.txt`):
- WIRECELL_PATH = `wct/cfg` only; JSON normalised before hashing.
- TLAs: `input=qlpctree.tar.gz`, `evt_subdir=pr_evt{run}_{subrun}_{event}`, `dl_vtx_dump=true`, `flat_tree=true`, `truth_match=(sim)`, `dv2_bundle=dv2max/sbnd/aurora_space/bundle.json`.

| reality | split (`dv2_split_move`, space on) | snap (`dv2_snap`, space off) | master default (no vertex TLAs, space on) |
|---|---|---|---|
| sim | `fa3745b3b49538b845feedb894bc3551` | `91e79e852ac19724fb5f31e66a0b2202` | = split |
| data | `5da14b64d454c9b956779e9d73270b4b` | `5556ac044bce2af1ef61c81afdb0ea6b` | = split |

**Grid tarball:** test build `wclocal-nov16/tar/wcgrid-wcl1116-test1.tar.gz`, 268 MB. It ships the release `opt`, `wct/cfg`, `pydv2` and `wire-cell-data/dv2max/sbnd/aurora_space` (`make-tarball.sh` with `WC_TARBALL_OPT/CFG/PYDV2/DV2`).

**R1 test: emulated worker** (`scripts/emulate-step2.sh`):
- Setup: SL7 image, `--contain --cleanenv`, only `/cvmfs`, `/pnfs` and the work dir mounted; the tarball unpacked fresh.
- Run: one data unit (`ncpi0-s0-7`, 7 events), split pass.
- Python: CVMFS python3; `scipy 1.13.1`, `lightgbm 4.6.0`, `torch 2.6.0`, `numpy 2.0.2` all import.
- The bundle is read from the tarball. rc 0, no "DL vertex failed"; wall 2:48, peak RSS 1.9 GB.
- **Every tree of the 7 `tracking-pr.root` files is identical to the local run**, `wct_version` included. All 7 DV2 calls match the local run in input digest and prediction.

**dCache:**
- The user quota on pnfs is **864 GiB used of 4,656 GiB**. That equals the persistent holdings (fg1 578 + open data 205 + run3bnb + ncdr), so about 3.8 TiB is free on persistent, against 0.7 TB planned.
- Scratch has no quota; it evicts.
- The kept step-1 tars (`tables/p2-kept-tars.tsv`): **all 54,304 listed tars exist** (1.6 TB). A sample of 50 is ONLINE.

## P1: smoke on nueCC-48 + NCπ0-19 (and the 18 #43 MC tars)

`scripts/run-step2.sh`, one pinned core each, the same step-1 tars as issue 47 task A. Arms:
- **split**: `dv2_split_move`, space on, production `evt_subdir`;
- **snap**: `dv2_snap`, space off;
- **split-a**: split with task A's TLAs (space off, `evt_subdir` default), data only.

63 runs (27 split, 27 snap, 9 split-a): **63/63 rc 0, no "DL vertex failed"** (`tables/p1-runs.txt`).

| gate | result |
|---|---|
| split-a vs issue 47 task A `aurora_space` arm, every tree by value (`compare-trees.py`) | 67/67 files: **only `Trun.wct_version`** (+ its `recTreeWireCell` columns) |
| split (production TLAs) vs the dump-PR round-2 knob-on runs of the same data tars | 67/67 files: only `Trun.wct_version` |
| split vs split-a | only `T_dlvtx_space`, `T_dlvtx_call.space_cluster_id` / `n_space` and their `recTreeWireCell` columns |
| input digests, in chain vs the dump (`percall.py`) | data **68/68**, MC 161/161; 1,417,696 space points; replay within 1.6e-5 cm |
| data digests vs task A's hook logs | **68/68 identical, predictions identical** (the cross-site key with prod_aurora: `input_sha1`) |
| snap | rc 0, no DL failure. Its 68 DV2 calls have the same inputs and predictions as split; only the vertex placement differs |

**dv2_snap vs dv2_split_move on the 67 data events** (`tables/data-snap-vs-split-*`):
- The selected candidate is the same in every event; all 68 candidates are DL-based in both modes.
- Final vertex distance: median **0.45 cm**; < 1 cm 56/68, < 2 cm 63/68, ≥ 5 cm 1 (max 8.7 cm).
- Selections:

| | split nue / numu | snap nue / numu |
|---|---|---|
| nueCC-48 | 41 / 4 (= task A `aurora_space`) | 38 / 3 |
| NCπ0-19 | 1 / 1 | 1 / 3 |

- 6 events change:
  - nue lost by snap: 18255/1/268784, 18259/1/52672, 18259/1/111412;
  - numu gained by snap: 18255/1/71372, 18364/1/84229;
  - numu lost by snap: 18255/1/271851.

## Schemas

The existing production schemas fit 0.38.0. Against `make-schema.py` on the P1 outputs:
- no branch is added or changed;
- the only extra branches are the 12 of `T_blob_truth` (step-2 TLA `blob_truth`, off in production: 0 rows).

So both trees keep the schemas the readers already know:
- `recTreeWireCell` (split) = `recTreeWireCell-dlvtx-space.schema.json` (`af9c87c8`, as aurora-r2);
- `recTreeWireCell_dv2snap` = `recTreeWireCell.schema.json` (`d4396a34`, as fg1).

The regenerated ones (2,404 and 2,389 branches) are in `wclocal-nov16/p1/ana/`.

## P2: step-1 reuse test: **identical, so reuse**

Setup:
- 5 status-OK pairs per sample, seeded random (`scripts/pick-p2-pairs.py`, `tables/p2-pairs.tsv`).
- Step 1 rerun with 0.38.0 + `ad5d942` from the reco1, followed by both step-2 passes, the two-tree merge and both validations. This is the full chain of the workflow branch, `scripts/run-p2.sh`, with `WC_STAMP_INPUT_FILE=1`.
- 25/25 pairs OK, 935 events.
- Each new `ql/all/qlpctree.tar.gz` compared with the kept tar by datapath (`scripts/compare-qlpctree.py`, `tables/p2-step1-compare.tsv`).

| sample | kept tar (build) | pairs | tensors | result |
|---|---|---|---|---|
| MC CV | fg1 scratch (`4b6853d4`) | 5 (74 ev) | 16,736 | **identical**: arrays and metadata |
| MC nueCC | fg1 scratch | 5 (43 ev) | 9,728 | **identical** |
| beam-off | fg1 scratch | 5 (250 ev) | 55,056 | **identical** |
| Run 3 (run3bnb) | scratch | 5 (250 ev) | 55,076 | **identical** |
| Run 1 open data | persistent (`f6fd2209` + lwc `3b54651`) | 5 (250 ev) | 55,070 | **arrays identical**; metadata differs only in `input_file` (50/file). The open data predates the input-file stamping; allowed by the rule |

→ **Run step 2 only from the kept tars.**

Pairs whose earlier status is OK and that have one unsliced kept tar use the step-2-only grid mode (`WC_GRID_MODE=step2`). The others run from reco1 (`scripts/make-lists.py`, `lists/`):

| sample | pairs | step-2-only (events) | full mode |
|---|---|---|---|
| MC CV | 37,742 | 37,720 (499,685) | 22 PARTIAL |
| MC nueCC | 11,445 | 11,421 (99,808) | 20 PARTIAL + 4 EMPTY |
| beam-off | 1,096 | 1,054 (49,828) | 4 PARTIAL + 38 EMPTY |
| Run 3 | 2,208 | 2,204 (109,287) | 4 PARTIAL |
| Run 1 open data | 1,817 | 1,816 (89,896) | 1 PARTIAL |
| **total** | 54,308 | **54,215 (848,504)** | 93 |

## P3: the workflow on the grid

- **Branch:** `HaiwangYu/sbnd-wirecell-production` `wclocal-nov16` `99e1fc9`.
- **Tarball:** `wclocal-nov16/tar/wcgrid-wcl1116-99e1fc9.tar.gz`, 268 MB.
  - Provenance: 0.38.0 `c935e30d`, larwirecell `ad5d942`, wire-cell-data `99c6497`, bundle sha256 `51588842…`, pydv2.
- **Test:** 2 MC CV pairs from P2, run once in full mode (cluster `72818346@jobsub03`) and once in step-2-only mode (`30993258@jobsub05`). Output: `/pnfs/sbnd/scratch/users/yuhw/prod-fermigrid/WCLocal2026Nov16-test/`.
  - **4/4 jobs OK**; each merged CAF carries `recTreeWireCell` + `recTreeWireCell_dv2snap`, both validated.
- **Grid vs the local P2 run of the same pair** (`fermigrid/bin/compare-outputs.py`): every tree of every `tracking-pr.root` and of the merged CAF is identical (322 trees, 49,130 branches per pair). The full-mode qlpctree is identical too.
  - The only differences are the two `_info` notes: creation time and schema path, as in the fg1 grid test.
- **Grid cost (MC CV, 16 events), step-2-only:**
  - split pass ~170 s CPU, snap pass ~165 s;
  - merges 2 × 8 s;
  - validations ~100 s;
  - total **≈ 33 CPU-s/event**; peak RSS 1.77 GB.
- In full mode, step 1 adds 45–60 s/event on these nodes.

## P4: pilot (submitted 2026-11-16 17:00 CST)

- **Pairs:** every 100th step-2-only pair per sample (`lists/pilot-*-step2.tsv`): 546 pairs, 8,540 events.
- **Output:** the production tree `/pnfs/sbnd/scratch/users/yuhw/prod-fermigrid/WCLocal2026Nov16/<sample>/<id>/`. P5 submits the whole lists, and its jobs skip pairs that are already finished.
- **Job settings:** `WC_GRID_MODE=step2`, both passes, 4000 MB + auto-release (+2 GB), 6 h, 10 GB disk.

| sample | pairs / per job | jobs | cluster |
|---|---|---|---|
| mc-cv | 378 / 12 | 32 | `30782033@jobsub04` |
| mc-nuecc | 115 / 8 | 15 | `87512756@jobsub01` |
| beam-off | 11 / 3 | 4 | `30993748@jobsub05` |
| run3bnb | 23 / 2 | 12 | `30993749@jobsub05` |
| opendata | 19 / 2 | 10 | `94490280@jobsub02` |
