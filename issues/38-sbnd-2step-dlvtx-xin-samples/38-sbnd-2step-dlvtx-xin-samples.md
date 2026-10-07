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
| wire-cell-data | see `RUN-RECORD.txt` | DL weights `uboone/scn_vtx/t48k-m16-l5-lr5d-res0.5-CP24.pth` md5 `9cc1413e…`; `XGB_nue_seed2_0923.xml` md5 `2bdb5cec…` |

## Plan

| milestone | content | gate |
|---|---|---|
| M0 | this doc + issue | – |
| M1 | sources synced; clean WCT configure + install in SL7; larwirecell rebuilt and hand-copied to `opt` | build doc 8 post-build gate |
| M2 | config proof on compiled JSON, `scripts/cfg-proof.py` | C1–C10 below all PASS |
| M3 | smoke: 1 MC CV file + 5 beam-off events through both steps; replay of the recorded DL calls | rc 0; `T_dlvtx_*` and `T_truth_*` present; beam-off `frame_apply_at_caf` non-zero |
| M4 | production: MC CV (154 files, 2,017 events), MC nueCC (225 files, 2,001 events), beam-off (1,000 events) | every unit rc 0 or its failure explained |
| M5 | summary: resources, sizes, DL-dump counts; data guide | – |

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
