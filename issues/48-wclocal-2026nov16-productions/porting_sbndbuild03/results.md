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
