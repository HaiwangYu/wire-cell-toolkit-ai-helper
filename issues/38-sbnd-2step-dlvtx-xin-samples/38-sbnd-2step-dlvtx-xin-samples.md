# Issue 38: our larwirecell 2-step chain with `dl_vtx_dump=true` over the #30 samples, on sbndbuild03

GitHub: https://github.com/HaiwangYu/wire-cell-toolkit-ai-helper/issues/38.

Builds on:
- #33: **our** larwirecell 2-step chain. Step 1 is `lar -c wcls-img-clus-matching{,-data}.fcl`, which writes `qlpctree.tar.gz`. Step 2 is standalone `wire-cell -c pgrapher/experiment/sbnd/wct-pr.jsonnet` on that tar. This is not Xin's sbnd-reco1 2-step chain.
- #35: the DL-vertex dump. `dl_vtx_dump=true` adds `T_dlvtx_call` / `T_dlvtx_cloud` to `tracking-pr.root` and changes nothing else.
- #30: the samples, staged on sbndbuild03 under `production-prep/xin-round3-samples/`.

**Ask (Haiwang, 2026-10-06):**
1. Pull toolkit `HaiwangYu/wire-cell-toolkit:sbnd-dlvtx-35`. Build WCT and larwirecell as needed.
2. Merge `WireCell/wcp-porting-validation:main`. Discard our local commit if it conflicts, since that repo was developed on Aurora.
3. Validate the compiled JSON per toolkit `cfg/pgrapher/experiment/sbnd/docs/deploy-validation-2026-10-01.md`. Check the compiled configs carefully. No output-file comparison is needed this time.
4. Re-run our 2-step chain with `dl_vtx_dump=on` on the #30 samples.
5. Use at most half of sbndbuild03's CPU and memory.

## Choices made (stated, not asked)

| item | choice | why |
|---|---|---|
| step 1 fcl | `wcls-img-clus-matching.fcl` (MC), `wcls-img-clus-matching-data.fcl` (beam-off) | the production step 1 of #33: hit-rebuilt flashes + light gate |
| step 2 | `wct-pr.jsonnet --tla-str reality=sim/data --tla-code dl_vtx_dump=true` | as #35's bulk run |
| work unit | MC: one `lar` per reco1 file (about 13 events), then one `wire-cell` on its tar. Beam-off: the one 1,000-event file in 50 chunks of 20 (`--nskip`) | #35 `step1-bulk.pbs` layout. Event numbers are unique within every input file, so the tar's set ident (the event number, #33 open item) cannot collide |
| half-machine cap | every process under `taskset -c 32-63`; at most 28 units at once; no new unit while our `lar`/`wire-cell` RSS exceeds 50 GB; OMP/MKL threads = 1 | sbndbuild03 has 64 cores and 125 GB; the cap holds even if torch spawns threads |
| nugraph HDF5 | left as the in-tree step 1 has it (on) | not asked to change the config |
| output | `production-prep/r5-dlvtx-xin-samples/{mc-cv,mc-nuecc,beam-off}/<unit>/{ql,pr}/` | |

## Pins

| repo | ref | note |
|---|---|---|
| wire-cell-toolkit | `sbnd-dlvtx-35` `78f81c64` (fork) | master `0319ea67` merged + the DL dump |
| larwirecell (MRB tree) | `dev-v10_14_02_02` `189ad26` | fast-forwarded from `a02a1a4`: adds `wclsOpHitSource` (`f8177c7`), `wclsTruthInformationAttacher` (`4961f76`), labeler RNG re-seed (`189ad26`) |
| wcp-porting-validation | `main` `072505ce` | our local `e100a631` (nugraph switch, superseded by the 1-step to 2-step move) discarded; kept as local tag `r3-validated-1step-cfg` |
| wire-cell-data | `9e2f4b8` + untracked `uboone/weights/XGB_nue_seed2_0923.xml` | DL weights `uboone/scn_vtx/t48k-m16-l5-lr5d-res0.5-CP24.pth` md5 `9cc1413e…`; `XGB_nue_seed2_0923.xml` md5 `2bdb5cec…` |

## Plan

| milestone | content | gate |
|---|---|---|
| M0 | this doc + issue | – |
| M1 | sources synced; clean WCT configure + install in SL7; build-tree RPATH stripped; larwirecell rebuilt and hand-copied to `opt` | procedure doc §1, §1a, §2 gates |
| M2 | config proof on compiled JSON, `scripts/cfg-proof.py` | C1–C10 below all PASS |
| M3 | smoke: 1 MC CV file + 5 beam-off events through both steps; replay of the recorded DL calls | rc 0; `T_dlvtx_*` and `T_truth_*` present; beam-off `frame_apply_at_caf` non-zero |
| M4 | production: MC CV (154 files, 2,017 events), MC nueCC (225 files, 2,001 events), beam-off (1,000 events) | every unit rc 0 or its failure explained |
| M5 | summary: resources, sizes, DL-dump counts; where the data is | log (b) |

## Config proof (`scripts/cfg-proof.py`)

It runs inside SL7 with `sbnd/setup-ap.sh`, so `WIRECELL_PATH` is the one a `lar` job of this chain sees. Three toolkit cfg trees are compared:
- `old` = `51b5a1fc`, master before the 2026-10-01 fast-forward;
- `master` = `0319ea67`;
- `dlvtx` = `sbnd-dlvtx-35`, the tree deployed.

The 8 jobs are step 1, step 2, and the obsolete 1-step flash and hits, each for sim and data. The step-1 and 1-step extVars come from `fhicl-dump` of the fcls themselves.

| check | what | source |
|---|---|---|
| C1 | old to master: step 1 byte-identical; step 2 and the 1-step jobs move by exactly `main_vertex_swap_apply` and `nu_particle_links` | deploy note §2 |
| C2 | master to dlvtx with the dump off: all 8 byte-identical | #35 log (f) |
| C3 | dump on vs off: adds only `SCEFieldTH3:sbnd_dualmap_fwd`; changes only `dl_vtx_dump` and `sce_field` | #35 log (f) |
| C4 | step 2 with an overlay `clus.jsonnet` (swap off, particle links off) equals old step 2, except an explicit `main_vertex_swap_apply:false` | deploy note §3.4 |
| C5 | the old-flash-rule step 1 differs from step 1 only in `SBNDOpFlashFinder` `prompt_min_*` | deploy note §3.3 |
| C6 | runtime `WIRECELL_PATH` vs a minimal path: identical, so no cfg file is shadowed | ours |
| C7 | every component type is registered (`make_<type>_factory`) by a plugin the job loads | ours |
| C8 | every data file the JSON names resolves; flags any other root holding a different file of that name | ours |
| C9 | data vs sim: every differing key, for review | ours |
| C10 | step 2 operating-point snapshot | ours |

Results: log (a).

## Log

- 2026-10-06: scope; issue #38 opened; sources synced (pins above).

### (a) 2026-10-06: M1 build, M2 config proof, M3 smoke

**M1 build** (procedure `docs/sbnd-1step-build-run-validate.md` §1, §1a, §2):
- **WCT:** `rm -rf build`, `configure-wct.sh`, `./wcb -p --notests install -j16` in SL7: `BUILD_RC=0`, 10.7 min. Previous `opt/lib` kept in `opt/lib-backup-0ad64223-20261006`.
- **Gate §1:** 19 libs incl. Mcs; `__libc_single_threaded` undefined 0; spdlog `v1_14_1`; `NEEDED fmt` 0; `miniz.h` present and current. The binary knows the new keys `dl_vtx_dump`, `main_vertex_swap_apply`, `nu_particle_links`, `sce_field`, `prompt_min_pe`, `reset_shower_ids_per_event`.
- **§1a RPATH:** the fresh install again carried `DT_RPATH` into `wire-cell-toolkit/build/<pkg>` (the old one started with `opt/lib`). 20 files were patched (backup `production-prep/opt-rpath-backup-20261006`). Gate with `build/` hidden: 0 `not found` and 0 WireCell libs outside `opt`, for all WCT libs, `wire-cell`, `wcsonnet` and the larwirecell libs.
- **larwirecell:** fast-forwarded `a02a1a4` to `189ad26`, sources touched, `make -j16`: `MAKE_RC=0`.
  - Three libs changed and were deployed to `opt/larwirecell/.../lib`:
    - `libWireCellLarsoft.so` adds `wclsOpHitSource` and `wclsTruthInformationAttacher`;
    - `libWireCellAIML.so` adds the RNG re-seed;
    - `libWireCellQLMatch.so` changed through WCT headers.
  - The other 8 are byte-identical. Backup in `lib-backup-a02a1a4-20261006`.
  - `FrameShiftInfo` is compiled in, so `HAVE_SBND_FRAMESHIFTINFO` is set.

**M2 config proof: ALL PASS (43 checks)**, `production-prep/r5-dlvtx-xin-samples/cfg-proof/report.txt`. Compiled hashes (md5, first 12):

| job | old `51b5a1fc` | master `0319ea67` = dlvtx (dump off) | dlvtx, dump on |
|---|---|---|---|
| step 1 sim / data | `ab6cceaee873` / `118521ffcdcb` | same | – |
| step 2 sim / data | `06633b330910` / `54ade89edbab` | `06c0cbbbbfa2` / `c15477ed8dcb` | `87b7c48c0307` / `99fdef8b7464` |
| 1-step flash sim / data | `a9d2e1ee966c` / `80d054fa866d` | `087e75ab8fd8` / `d0be25e4f82d` | – |
| 1-step hits sim / data | `29bc37c41ece` / `30ab048cc59e` | `11b55d2ecb9c` / `56139e87d709` | – |

- **C1:** step 1 byte-identical old to master. Step 2 and both 1-step jobs move by exactly two keys: `TaggerCheckNeutrino:pr.main_vertex_swap_apply` and `UbooneTaggerOutputVisitor:pr.nu_particle_links`, absent to true. This is the note's changes 2 and 3. Change 1, the flash prompt-time rule, is a C++ default and cannot show in JSON.
- **C2:** all 8 jobs byte-identical between master and `sbnd-dlvtx-35` with the dump off.
- **C3:** the dump adds `SCEFieldTH3:sbnd_dualmap_fwd` (`SCEoffsets_SBND_E500_dualmap_CV_voxelTH3.root` from sbnd_data v01_42_00, `TrueFwd_*`, sign 1). It sets `TaggerCheckNeutrino:pr.dl_vtx_dump=true` and `SbndPrMagnifyTrackingVisitor:pr.sce_field`. Nothing else changes.
- **C4:** with the overlay `clus.jsonnet` (swap off, particle links off), step 2 equals old step 2 except an explicit `main_vertex_swap_apply:false`, for sim and data.
- **C5:** the old-flash-rule step 1 differs from step 1 only in `SBNDOpFlashFinder:tpc{0,1}.prompt_min_{pe,hits,opdets}=0`.
- **C6:** the runtime `WIRECELL_PATH` compiles all 8 jobs identically to a minimal path, so no cfg file is shadowed.
- **C7:** every component type is registered by a loaded plugin. One subtlety: `ChannelSelector` is not in any fcl's plugin list. It is registered by `libWireCellSigProc`, which loads as a `NEEDED` dependency of `libWireCellLarsoft`.
- **C8:** all 43 input data files resolve, and no other root holds a different file of the same name. They are:
  - the geometry, charge error, semi-analytical model, opdet geometry and track-fitting json;
  - the SCE map;
  - the DL weights `t48k-…-CP24.pth` (md5 `9cc1413e053c`);
  - 36 BDT xmls, incl. `XGB_nue_seed2_0923.xml` (md5 `2bdb5cec111b`).
- **C9, data vs sim:** step 1 differs in exactly what #26 listed:
  - the four `simtpc2d`/`sptpc2d` tags;
  - per-TPC `pos_offset` and the `y_cor/z_cor` coords;
  - `QLMatching data=true, QtoL=0.86`;
  - the labeler's `reality`.

  Step 2 differs only in `pos_offset` and the Bee/tagger coords. FrameShift has no config key: `wclsOpHitSource` reads art label `frameshift` and silently uses 0 if it is absent, so it is checked in the smoke log instead.
- **C10, step 2 operating point:** `nu_per_bundle`, `fit_exclusion`, `dl_vtx_rerank` (top 5, accept 10, scale 1000), `dl_vtx_dual_chain` with `snap` / transfer / 2 cm, `main_vertex_swap_apply`, `nu_particle_links`. This is the #35 production point.

**M3 smoke** (`r5-dlvtx-xin-samples/smoke/`): MC CV `f000` (18 events), MC nueCC `f000` (6), beam-off `c00` (5 events).
- **First try: the DL vertex failed silently in every candidate** (`No module named 'SCN_Vertex'`; rc 0 everywhere).
  - Without `sbnd/setup-dlvtx.sh` (uBooNE `scn` product + `opt/python`), the chain falls back to the traditional vertex.
  - Sourcing that script inside the wrapper's `bash -c` did nothing either. It calls `path-prepend`, a shell function from `setup-local-opt.sh` that the new shell does not inherit, and `source` still returned 0.
  - **Fix in `run-2step-pool.sh`:** re-source `setup-ap.sh` (idempotent; `WIRECELL_PATH` unchanged) and then `setup-dlvtx.sh`. Step 2 refuses to start unless `SCN_Vertex`, `torch` and `sparseconvnet` are importable. Every unit records its `DL vertex failed` count (`pr/dl_fail`).
- **After the fix:**

| species | events | rc | DL failed | candidates | DL calls prod / off | `T_truth_*` | step 1 CPU/evt | step 2 CPU/evt | max RSS |
|---|---|---|---|---|---|---|---|---|---|
| MC CV | 18 | 0 / 0 | 0 | 8 | 9 / 9 | 18/18 | 29.4 s | 3.2 s | 1.9 GB |
| MC nueCC | 6 | 0 / 0 | 0 | 6 | 7 / 7 | 6/6 | 27.3 s | 26.4 s | 1.8 GB |
| beam-off | 5 | 0 / 0 | 0 | 1 | 1 / 1 | none (data) | 25.2 s | 3.5 s | 1.8 GB |

- **FrameShift on data:** `wclsOpHitSource` logs `frame_apply_at_caf` 256–1297 ns on the five beam-off events, and `FlashTensorToOpticalPCs` applies it (`correct_flash_time=true`).
- **Replay** (`issues/35-*/scripts/dlvtx-replay.py`, here on sbndbuild03): 34 recorded calls re-run standalone, 20 bit-identical and 14 equivalent (worst 7.2e-7), **0 mismatch**.
- Output per event, roughly: tar 2–2.6 MB, step-1 Bee 1–6 MB, h5 1.5–1.8 MB, `tracking-pr.root` 0.1–0.4 MB, step-2 Bee 0.3–0.4 MB.

**M4 launched** 2026-10-06 23:38: `scripts/run-all.sh` runs MC CV, then MC nueCC, then beam-off.
- Each species has at most 28 units at once, all under `taskset -c 32-63`, with a 50 GB RSS guard.
- `memwatch.log` samples our process count and RSS every minute.

### (b) 2026-10-07: M4 production done -- 5,018 / 5,018 events, every unit rc 0, 0 DL failures

Wall: MC CV 23:38–00:18 (40 min), MC nueCC 00:18–01:23 (65 min), beam-off 01:23–01:39 (16 min), plus one retry (2.5 min).
The cap held. `memwatch.log` peaked at 29 of our processes (28 in the pool plus the crash diagnosis) and 47.9 GB RSS, all on cores 32–63.

| | MC BNB CV | MC nueCC | beam-off |
|---|---|---|---|
| units (all rc 0 both steps) | 154 | 225 (1 after a retry, below) | 50 |
| events: step-1 tar / valid `tracking-pr.root` | 2,017 / 2,017 | 2,001 / 2,001 | 1,000 / 1,000 |
| `DL vertex failed` | 0 | 0 | 0 |
| neutrino candidates (`T_kine`) | 965 (47.8 %) | 1,894 (94.7 %) | 96 (9.6 %) |
| events with `T_dlvtx_call` | 944 | 1,890 | 66 |
| DL calls prod / off | 960 / 960 | 1,961 / 1,961 | 66 / 66 |
| DL accepted prod / off | 930 / 545 | 1,915 / 1,574 | 55 / 3 |
| prod `dual_transferred` (OFF hint replaced prod's pick) | 460 | 659 | 55 |
| `T_dlvtx_cloud` points | 538,677 | 1,851,221 | 34,984 |
| events with `T_truth_nu` / `T_truth_pf` | 2,017 | 2,001 | 0 (data) |
| final vertex vs SCE-shifted truth: median, < 1 cm | 0.71 cm, 55 % | 0.71 cm, 55 % | – |
| step 1 CPU / event, max RSS | 24.7 s, 2.0 GB | 28.7 s, 2.2 GB | 18.5 s, 2.0 GB |
| step 2 CPU / event, max RSS | 4.0 s, 1.8 GB | 20.0 s, 2.7 GB | 2.5 s, 2.1 GB |
| per event: tar / step-1 Bee / h5 / `tracking-pr.root` / step-2 Bee (MB) | 1.78 / 5.18 / 1.25 / 0.17 / 0.27 | 1.95 / 5.89 / 1.44 / 0.35 / 0.37 | 2.06 / 0.77 / 1.35 / 0.05 / 0.28 |
| disk | 17 GB | 19 GB | 4.3 GB |

- The truth distances count every candidate with a DL call. #35's 65 % < 1 cm is on its training selection (truth in the active volume, the true interaction's candidate), so the two are not the same quantity.
- Statistics: `dlvtx-stats.py` (#35), in `<species>/dlvtx-stats.txt`. Per-unit and per-event tables: `<species>/{units-summary.tsv, events.tsv, summary.md}`.

**Finding: a non-deterministic step-2 segfault (MC nueCC `f001`, event 10603).**
- **First run:** rc 139, peak RSS 4.4 GB (typical 1.5 GB).
  - The segfault is in `TrackFitting::update_association` (`clus/src/TrackFitting.cxx:3734`), reached from `TaggerCheckNeutrino::visit` → `improve_vertex` → `do_multi_tracking` → `form_map_graph` (`:4655`), at a PLT call with a shallow stack.
  - The ROOT handler then crashed a second time inside `TTree::TTree`.
- **Same tar, same binary, re-run twice** (`crash-nuecc-f001-10603/rerun1`, and the retry in place): rc 0, all 10 events. The 6 events both runs completed are identical in every branch of every tree, `T_dlvtx_*` included.
- So it is an intermittent defect (uninitialised or out-of-bounds memory is the likely class), not a data-driven crash. The crashed log is kept in `mc-nuecc/f001/pr-crash139/wct.log.gz`.
- **Side effect:** the event processed just before the crash (9269) was left as a 479-byte `tracking-pr.root` stub, because the writer closes a file lazily. A crashed step 2 therefore loses one more event than it reports, and the whole tar must be re-run. `summarize.py` counts files without `Trun` as stubs.
- Not filed upstream; same standing as crash 471/18/33 (#26 §5a): to fix ourselves later.

**Where the data is** (`/exp/sbnd/data/users/yuhw/production-prep/r5-dlvtx-xin-samples/`):
```
{mc-cv,mc-nuecc,beam-off}/<unit>/ql/qlpctree.tar.gz   step-1 tar (all events of the unit; MC: truth_nu / truth_pf tables)
                                 ql/mabc.zip           step-1 Bee (imaging, clustering, op, sed-* on MC)
                                 ql/nugraph.h5         labeler HDF5
                                 pr/pr_evt<E>/tracking-pr.root   PR output + T_dlvtx_call / T_dlvtx_cloud (+ T_truth_* on MC)
                                 pr/mabc-pr.zip        step-2 Bee (PR layers, taggers)
{species}/units.tsv     unit -> reco1 file, nskip, n      (MC: f<NNN> = one #30 reco1 file; beam-off: c<NN> = events 20*NN .. 20*NN+19)
{species}/events.tsv    unit, event, run/subrun/event, candidate, DL calls/accepted, cloud points, truth rows, scores, Enu
```
The inputs are the #30 reco1 files under `production-prep/xin-round3-samples/`. Beam-off is the frameshifted 1,000-event file.

Milestones M0–M5 done.
