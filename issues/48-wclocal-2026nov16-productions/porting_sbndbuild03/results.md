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

### P4 result (finished 2026-11-16 19:35 CST)

All 73 jobs ended; 546/546 pairs have a `.done`. Per pair: `tables/p4-pilot-pairs.tsv`; per sample: `tables/p4-pilot-summary.tsv` (`scripts/pilot-summary.py`).

| sample | pairs | OK | Wire-Cell events / CAF events | CPU s/event | pair wall s/event | tracking-pr kB/event | merged CAF kB/event |
|---|---|---|---|---|---|---|---|
| mc-cv | 378 | 377 | 4,975 / 4,987 | 15.5 | 18.7 | 1,132 | 1,019 |
| mc-nuecc | 115 | 115 | 988 / 988 | 65.0 | 73.7 | 2,116 | 1,494 |
| beam-off | 11 | 11 | 550 / 550 | 12.5 | 17.6 | 348 | 183 |
| run3bnb | 23 | 23 | 1,101 / 1,101 | 10.5 | 12.5 | 814 | 290 |
| opendata | 19 | 19 | 914 / 914 | 12.6 | 17.6 | 849 | 299 |
| **total** | **546** | **545 (99.8 %)** | **8,528 / 8,540** | 20.1 | 24.1 | 1,124 | 849 |

CPU and wall: both step-2 passes, both merges and both validations, per pair.

- **Gate (status OK ≥ 99 %): passed**, 545/546.
  - Every validation PASS (1,092 of 1,092).
  - No `DL vertex failed`.
  - Only one pair needed retries: the PARTIAL one.
- **The PARTIAL pair** `mc-cv/reco1-detsim-g4-gen-Gen2_2026-571e-af6d-07bc-4c85` (14 events): step 2 was killed (rc 137) on its 3rd event in both passes and both tries, each time at 4,181 MB, in `determine_overall_main_vertex_DL` after 49,781 DV2 space points.
  - So the CAF has 2 of the 14 events in each tree. The other 12 have no Wire-Cell entry, and both validations still PASS.
  - Rerun on sbndbuild03 (`run-step2.sh`, `wclocal-nov16/p4mem/`): both passes rc 0 on all 14 events, peak RSS 5.35 GB (split) and 5.33 GB (snap).
  - **Cause:** the 4 GB slot memory limit, not a code fault.
  - Peak RSS of the other 545 pairs: 473 below 2 GB, 545 below 4 GB, max 3.67 GB.
  - **For P5:** keep 4000 MB, then a recovery pass at 8000 MB for the pairs that are not OK, written to `<sample>-mem8g/` so nothing gets overwritten (`scripts/submit-p5.sh recover`).
- **One job was held once** for a while (the watcher saw `HELD 1`; reason not recorded). It was released and all its pairs finished.
- **Time:** submitted 17:00. The first pairs finished at 17:03, and 482/546 (88 %) by 18:00. The last nueCC jobs (8 pairs of ~74 s/event each) took until 19:35. P5 uses 4 nueCC pairs per job.

#### Missing weight files in the pilot tarball (output unaffected)

- **Problem:** `prod_aurora` found that a missing BDT weight file only WARNs, and made `step2.sh` (`d05cf47`) exit rc 91 on it.
  - The pilot tarball (`99e1fc9`) has `XGB_nue_seed2_0923.xml` and the 15 sub-BDTs the XGB nue score uses.
  - It lacks 15 legacy TMVA sub-BDT files that `UbooneNueBDTScorer` resolves but never evaluates (`mipid`, `gap`, `hol_lol`, `cme_anc`, `mgo_mgt`, `br1`, `br3`, `br4_tro`, `stem_dir_br2`, `stl_lem_brm`, `mipquality`, `pio_1`, `stw_spt`, `vis_1`, `vis_2`): no `cal_*_bdt` call site for any of them.
  - Every pilot `wct.log` (1,094) has the 15 "weight file not found" lines.
- **Effect: none.** The grid test pairs (same tarball, same 15 lines) are identical to the local runs, which had every file, in every tree: `T_tagger` included, 322 trees, 49,130 branches.
- **Fix:** workflow `53a90eb` (pushed to `wclocal-nov16`). `make-tarball.sh` now ships every `uboone/weights` file the shipped SBND cfg names (36), and refuses to build if one is missing.
- **P5 tarball:** `wclocal-nov16/tar/wcgrid-wcl1116-53a90eb.tar.gz` (290 MB). It also carries `d05cf47`'s rc-91 guard.
- **Check of the P5 tarball:** two pilot pairs rerun on an emulated worker (`emulate-worker.sh`, apptainer with only /cvmfs and /pnfs, `wclocal-nov16/emu53a/`): one nueCC pair (8 events) and one opendata pair (50 events).
  - Both OK, with 0 "weight file not found" lines.
  - Against their pilot grid outputs (`compare-outputs.py`):
    - nueCC: identical in every tree (175 trees, 39,910 branches); only the two `_info` TNamed differ.
    - opendata: identical in every tree (668 trees, 101,183 branches); only the two `_info` TNamed differ.

### P5 (`scripts/submit-p5.sh`)

- **step2:** the whole `pairs-<s>-step2.tsv` lists. Pilot pairs are skipped. CV 12, nueCC 4, beam-off 3, run3bnb 2, opendata 2 pairs per job.
- **full:** the 93 from-reco1 pairs, 1 per job, 4000 MB, 8 h, 15 GB.
- **recover:** the pairs that are not OK, at 8000 MB, into `<sample>-mem8g/`.

Submitted 2026-11-16 20:18–20:45 CST, tarball `wcgrid-wcl1116-53a90eb` (`lists/p5-submit.log`):

| sample | step2: pairs / per job / jobs / cluster | full: pairs / jobs / cluster |
|---|---|---|
| mc-cv | 37,720 / 12 / 3,144 / `87513916@jobsub01` | 22 / 22 / `30783238@jobsub05` |
| mc-nuecc | 11,421 / 4 / 2,856 / `30994651@jobsub05` | 24 / 24 / `72819628@jobsub03` |
| beam-off | 1,054 / 3 / 352 / `72819616@jobsub03` | 42 / 42 / `72819630@jobsub03` |
| run3bnb | 2,204 / 2 / 1,102 / `87513923@jobsub01` | 4 / 4 / `30783252@jobsub05` |
| opendata | 1,816 / 2 / 908 / `72819620@jobsub03` | 1 / 1 / `94491395@jobsub02` |
| **total** | 54,215 pairs, 8,362 jobs (546 pilot pairs skipped) | 93 pairs, 93 jobs |

### P5 result (2026-11-17)

All P5 jobs finished by 07:12 CST except one, the beam-off job that holds the timeout pair below. No pair ended FAIL. Pairs not OK on the first try, with the cause and the final state, are in `tables/p5-not-ok-pairs.tsv`.

| | OK | PARTIAL | EMPTY | not finished |
|---|---|---|---|---|
| step-2-only (54,215, pilot included) | 54,202 | 12 | — | 1 |
| from reco1 (93) | 17 | 34 | 42 | — |

After the recovery passes below:

| sample | events | with Wire-Cell output | missing |
|---|---|---|---|
| mc-cv | 495,013 | 494,981 | 32 |
| mc-nuecc | 99,015 | 98,997 | 18 |
| beam-off | 49,466 | 49,414 | 52 |
| run3bnb | 108,386 | 108,384 | 2 |
| opendata | 89,032 | 89,032 | 0 |
| **P5** | **840,912** | **840,808 (99.988 %)** | **104** |

The P5 estimate counted 840,919 events. Two beam-off pairs (`…-ace50bde-…`, `…-c0f6c867-…`) list 5 and 2 events, but their reco1 files and their CAFs have 0 entries (uproot), so the true total is 840,912.

The 104 missing events by cause:

| cause | pairs | events | what was done |
|---|---|---|---|
| step 2 timeout | 2 | 52 | second recovery pass (below), running |
| step 2 segfault, same event on every try | 5 | 28 | none: a WCT 0.38.0 crash, see below |
| step 1 `lar` crash on one event, which is skipped | 24 (from reco1) | 24 | none |

#### Recovery at 8 GB (`submit-p5.sh recover|recover-full`, 2026-11-17 07:13–07:40 CST)

16 pairs, step 2 killed at the 4 GB slot limit (rc 137). Clusters: `72821678`, `30785958`, `30785963`, `30785970`, `72822680` (step 2) and `94493772`, `87516538`, `87516540`, `31000751` (from reco1). All 16 jobs finished by 08:35, and all 16 pairs are **OK**: 565/565 events, both validations PASS. Peak RSS was 4.4–8.1 GB; the 8,058 MB peak (opendata `…-bd2335b4-…`) is within the 2 GB auto-release grace. Outputs are in `<sample>-mem8g/<id>/`. The first-try outputs are kept, and the catalog takes the `-mem8g` pair when its `.done` says OK.

#### The 7 step-2 segfault / timeout pairs, rerun locally (`p5diag/`)

Each pair was rerun on sbndbuild03 with the split pass, pinned to one CPU each and without a step limit:

| pair | grid | local | RSS | where |
|---|---|---|---|---|
| CV `d8bb-e799-f307-1327` | rc 139, both passes | rc 139 after 3.6 min | 4.2 GB | event 4803/48/12 (corrected 2026-11-17; first written as 18 from an unrelated `ident=` log match): `find_other_vertex` → `Graphed::descriptor_valid` (PRGraph.cxx:362), from `bad_reconstruction` in `nue_tagger` |
| CV `d7e5-a516-3477-e682` | rc 139, split pass only | rc 139 after 3.7 min | 4.5 GB | event 8169/41/12: `VertexIndexCmp` on a dead `Vertex` in `std::set::insert`, `id_pi0_with_vertex` (NeutrinoShowerClustering.cxx:8154) |
| nueCC `2c2d-7fef-91ef-6f3a` | rc 139, both passes | rc 139 after 7.2 min | 4.5 GB | event 230/90/10679: `boost::remove_edge` on a freed edge list, `break_segment_into_two` (PRGraph.cxx:315) ← `break_segments` ← `find_other_segments` |
| nueCC `2ce6-000e-14f2-234d` | rc 139, both passes | rc 139 after 5.7 min | 4.5 GB | event 206/11/5680: the same stack as `2c2d` |
| nueCC `b61a-f473-a953-2776` | rc 139, both passes | rc 139 after 6.9 min | 4.5 GB | event 259/49/7138: string copy from a bad pointer in TrackFitting.cxx:8281/10375, `examine_vertices_1` |
| nueCC `2008-a445-041f-88fc` | rc 124 (step-2 limit 3,000 s), both tries | **rc 0** in 18 min | 2.2 GB | the grid nodes are slower; no crash |
| beam-off `91943619-ac86-1782-8c5d-135492225a77` | rc 124 then held, every try | **rc 0** in 75 min (50 events) | 4.6 GB | the first event (858 clusters, 112,914 DV2 space points) takes most of it |

- **Segfaults:** all 5 are deterministic. In every grid log (both tries, both passes) and in the local run, the crash comes at the same event (`ident`). All are in the 0.38.0 pattern-recognition graph code (`Clus::PR`). The stacks look like use of a freed vertex/edge after a graph change. The pass stops there, so the rest of the file has no tracking-pr output: 28 events from 5 crashing ones. The old chain (fg1, WCT `4b6853d4`) did reconstruct all 14 events of CV `d8bb`. Logs with the full stacks: `wclocal-nov16/p5diag/<id>/wct.log.gz`. Not rerun: a skip-the-event rerun of step 2 does not exist in the workflow, and these are code bugs for the WCT developers.
- **Timeouts:** both finish without the limit. Rerun on the grid at 8 GB with a 4 h step-2 limit (`WC_TIMEOUT_STEP2_BASE=14400`; workflow `f452d76` makes `submit.sh` pass it through), into `<sample>-mem8g/`: `submit-p5.sh recover-slow`, clusters `72823730@jobsub03` (nueCC) and `31002649@jobsub05` (beam-off), 2026-11-17 08:55 CST.
- The original beam-off timeout try (job `72819616.75`, restarted at 6 GB) ended **FAIL step2** at 08:54 CST: 4 tries, each at the limit (the log labels them rc 137 "(timeout)"). It wrote logs and no `.done`; the rerun above replaces it.

#### Copy of the merged CAFs to persistent (2026-11-17)

- **Plan:** `scripts/caf-copy-plan.py` → `wclocal-nov16/lists/caf-copy-plan.tsv`, one CAF per pair. A pair takes `<sample>-mem8g/<id>/` when its `.done` says OK, otherwise `<sample>/<id>/`. The 42 EMPTY pairs have no CAF, and the 2 rerun pairs wait for their jobs. That leaves 54,264 files (16 from `-mem8g`).
- **Copy:** `scripts/caf-copy.sh copy` (NFS `cp`, 8 at a time, on sbndbuild03 from 09:01 CST) into `/pnfs/sbnd/persistent/users/yuhw/prod-fermigrid/WCLocal2026Nov16/<sample>/<id>/`. The script refuses any other destination.
- **Verify:** `scripts/caf-copy.sh verify` compares size and dCache's ADLER32 of each copy with its source.
  - sbndbuild03 crashed during the verify (it hangs on SSH since about 10:40 CST): 41,563 had been checked by then, all OK.
  - The other 12,702 were checked on sbndgpvm02, all OK.
  - Combined, deduplicated table: `lists/caf-copy-verify-all.tsv`, **54,264 / 54,264 OK, 720.0 GB**.
  - The persistent tree holds exactly the planned files: no extra, partial or 0-byte ones.
- **Lost with sbndbuild03:** only scratch files in its `/tmp`, all of which can be regenerated. The pair tally was already saved as `lists/final-pairs-first-try.tsv`.

#### Catalog (`scripts/make-catalog.py`)

Per sample it writes `pairs-`, `status-`, `events-<s>.tsv.gz`, `<s>.merged-caf.txt`, and `.tracking-pr-scratch.txt` / `.qlpctree-scratch.txt`.
- A CAF read over dCache NFS takes about 2 s on sbndgpvm02, so not every CAF is read.
- For an OK pair, run/subrun/event come from the fg1 or run3bnb events list, provided that list has as many events as the pair's CAF. The flat CAF `recTree` is the official one, unchanged.
- Read from the CAF itself: open data (it has no earlier events list), every non-OK pair, any count mismatch, and 150 random OK pairs as a check.
- Python 3.14's default `forkserver` start method re-runs the unguarded script in every worker, which hangs the pool. The script uses `fork`.
