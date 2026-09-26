# Issue 32: Aurora -- update WCT to master 2026-09-25 and validate the 1-step chain against Xin's wcgpu1 run

GitHub: https://github.com/HaiwangYu/wire-cell-toolkit-ai-helper/issues/32. Builds on #29
(the Aurora setup, scripts in `issues/29-aurora-production/scripts/`), #24 (what the
1-step vs 2-step comparison proves) and `docs/sbnd-1step-build-run-validate.md`.

**Ask (Haiwang, 2026-09-26):** pull `origin/master` (WireCell) into `polaris-build-fixes`,
rebuild WCT + larwirecell on Aurora, run the nueCC-48 and NCpi0-19 data samples, and check
(a) that the new run is identical to Xin's `m0925pr` run on wcgpu1 (copied to
`wcp-porting-validation/sbnd/sbnd_xin/work-{nuecc48,ncpi0}-m0925pr`) and (b) that it differs
from our previous Aurora run (#29) because the toolkit moved.

Work area `Y=/lus/flare/projects/neutrinoGPU/yuhw`; all container work in PBS jobs (no
userns on the UANs, #29 sec 1.2).

## What the reference is

Xin's arms are the standalone **2-step** chain on wcgpu1: stage A (`work-*-m0925/ql_evt<E>/pctree-evt<E>.tar.gz`,
reco1 reader + imaging + clustering + Q/L, not copied) and stage B (`work-*-m0925pr/pr_evt<E>/`, the
15-stage PR job, `reality=data dl=on`; copied: `tracking-pr.root`, `mabc-pr.zip` with 7 Bee layers,
`nusel-evt<E>.tsv`, `calib-pr-evt<E>.json`, `pctree-pr-evt<E>.tar.gz`, `.wct-cfg-evt<E>.json`, logs).
Event sets: nueCC 48 = `sbnd-gen2-data/nuecc-lynn/lynn-nuecc-rse.csv` (48/48), NCpi0 19 = our
`production-prep/ncsb-data-20260917-1313` events (19/19), both checked by RSE.

Our arm is the LArSoft **1-step** (`wcls-img-clus-matching-xin-data.fcl`), one `lar` process per
event, `production-prep/<tag>-<date>/evt<k>/{tracking-pr.root,mabc.zip}`.

## Caveat noted before running (Xin's docs, wcp-porting-validation `0e7b38f3`)

`sbnd_xin/docs/123` sec 17 (2026-09-25): standalone production flipped to **flashes rebuilt from
reco1 OpHits** (`wct-reco1-dump.jsonnet` `flash_source='hits'`, `SBNDOpFlashFinder`, toolkit `c2b578fe`);
sec 19 (2026-09-25): the **QLXTPC scenario-1 light gate** ON in the per-event Q/L job
(toolkit `7312f2b3`). Sec 17.4 and 19.5 say explicitly that the LArSoft 1-step chain still reads
`recob::OpFlash` via `wclsOpFlashSource` (no `wclsOpHitSource` in larwirecell; sec 16 is its design)
and runs no light gate: "the two chains run different light on purpose". So if the `m0925pr` arms
were produced at that production default, Q/L-dependent outputs cannot be identical by
construction. The PR operating point itself (pr() defaults since toolkit `7a85e5c5`) is shared, and
Xin's `two_chain_gate.py` (doc 120) checks that.

## Log

### 2026-09-26 (a) toolkit merge, config update, clean rebuild submitted

- WCT remotes now `origin` = `https://github.com/WireCell/wire-cell-toolkit.git`, `fork` =
  `git@github.com:HaiwangYu/wire-cell-toolkit.git`. `origin/master` `129362fe` is 91 commits past
  our merge base `67e2eba7`; our branch had one local commit `9195180d` (gcc-12 `-Werror` fixes in
  `CheckSTM_Michel.cxx`, `improvecluster_1.cxx`), which upstream made independently in `d2646110`.
  Trial merge in a scratch worktree: conflicts only in those two files. Merged with upstream's
  versions (`git checkout --theirs`), merge commit `2982785a`; `git diff origin/master` is empty,
  so **polaris-build-fixes == origin/master** (tag describe `0.35.0-1715-g2982785a`). Pushed to fork.
- Upstream commits that matter for this validation: `7a85e5c5` (pr() defaults = production
  operating point, 1-step chain promoted in-tree, 25-key drift closed), `c2b578fe` + `7312f2b3`
  (hit flashes, light gate -- standalone only, see caveat), `d3b398fc`.. many default-OFF knobs,
  `41fe5196`/`63e74946`/`45dfc10d` (byte-identical performance work).
- `wcp-porting-validation` fast-forwarded `2988d4d1` -> `0e7b38f3` (121 commits). `f04d8937`
  deleted `sbnd/pr-operating-point.jsonnet`; `sbnd/wcls-img-clus-matching-xin.jsonnet` is now a
  one-line `import 'pgrapher/experiment/sbnd/wcls-img-clus-matching-xin.jsonnet'` (resolved through
  `$WCT_SRC/cfg` on `WIRECELL_PATH`, `setup-aurora-ap.sh`). The fcls are unchanged. The in-tree
  jsonnet reads only `reality`, the four product-tag lists and the two opflash labels; the fcl's
  `pr_operating_point` / `enable_nugraph_h5` params are now unused extVars (harmless).
- `larwirecell` (`dev-v10_14_02_02` `a02a1a4`) is current with the fork; nothing to pull, but it
  must be rebuilt against the new WCT (ABI).
- Scripts (`issues/29-aurora-production/scripts/`): `build-wct-lwc.pbs` gets `CLEAN=1` (rm the
  waf build tree + `$OPT/{lib,include,bin,share}` before configure) and fetches tags from `origin`;
  `smoke.pbs` defaults `DO_RESYNC=0` and adds gate **G4b** = `two-chain-gate-aurora.sh` (Xin's
  `sbnd_xin/scripts/cfg/two_chain_gate.py` copied into the run dir with its five wcgpu1 paths
  repointed, run against `$WCT_SRC/cfg`); new `compare-xin.pbs` (vs Xin's `pr_evt<E>/` layout and,
  optionally, vs an older Aurora run).
- Old install preserved: `cp -a $Y/opt $Y/opt-9195180d-20260916` (1.7 GB, 797 files).
- Build: `qsub -q debug -v CLEAN=1 build-wct-lwc.pbs` -> job 8871075.

### 2026-09-26 (b) build done, data runs submitted

- Job 8871075 (`debug`, 1 node, 02:00-02:14 UTC): WCT at `2982785a` (`polaris-build-fixes-0.35.0-1715-g2982785`),
  configure 2m12s, clean build + install 3m37s at `-j96`, `WCB_RC=0`, 19 libs incl. Mcs,
  20 build-tree RPATHs stripped, `ldd_not_found=0`. larwirecell (`mrb z` + `mrb b -j96`, 3m00s)
  `MRB_RC=0`, deployed to `$OPT/larwirecell/v10_01_28/slf7.x86_64.e26.prof/lib`, `tree_wirecell_refs=0`.
  The three stderr lines (`srproxy v00.44` action parsing, `mrbSetEnv failed`, `sbnobj` version
  conflict) are the same known noise as in the 09-16 build logs; library timestamps confirm
  everything was rebuilt (`libWireCellClus.so` 02:11, larwirecell libs 02:14).
- Runs (data fcl `wcls-img-clus-matching-xin-data.fcl`, `smoke.pbs` with `DO_GATES=1`, one `lar`
  per event, `taskset` 2 cores, cold event first then the rest in parallel):
  - NCpi0-19: job 8871114 (`debug`), input `sbnd-gen2-data/nc-sideband-lynn/filtered-reco1/nc-sideband_filtered_frameshift.root`,
    `NEVT=18`, `TAG=ncsb-m0925`, log `aurora-build-logs/smoke-ncsb-m0925.out`.
  - nueCC-48: job 8871116 (`debug-scaling`), input `sbnd-gen2-data/nuecc-lynn/filtered-reco1/data_filtered_decoded_reco1-fe6033f3-..._eventidfiltered_frameshift.root`,
    `NEVT=47`, `TAG=nuecc48-m0925`, log `aurora-build-logs/smoke-nuecc48-m0925.out`.

### 2026-09-26 (c) both data runs clean; config gates say exactly what the caveat predicted

- Gates (both jobs): G1 build tree = run tree (`2982785a`), G2 no build-tree RPATH, G3 ok, G5
  sparseconvnet/torch 2.6.0+cu124 import ok, G6 spdlog/fmt ok.
  - **G4b two-chain gate: PASS** -- "both chains compile to the same PR operating point"
    (larsoft 226 components, local 42, 40 compared, 17 forgiven as structural). So the PR stage
    of our 1-step and of Xin's `wct-pr-perevt.jsonnet` run the same knobs from the same cfg tree.
  - G4 (old compile-both gate, still run): `2 differences`, both in `QLMatching:matching_joint`,
    `only in Xin: xtpc_sc1_light_gate = true`, `xtpc_sc1_overpred_max = 2.9` -- the doc-123 sec 19
    light gate, present in Xin's per-event Q/L job and absent from the 1-step chain (sec 19.5).
    This is the caveat, now measured at the config level.
- NCpi0-19 `production-prep/ncsb-m0925-20260926-0223`: 19/19 `rc=0`, `audit=ok`, 0 DL-vertex
  failures, **10 trees** in `tracking-pr.root` (8 before the update); cold event 213 s, the other
  18 in parallel 94 s wall (38-90 s each), peak RSS <= 2.0 GB.
- nueCC-48 `production-prep/nuecc48-m0925-20260926-0223`: 48/48 `rc=0`, `audit=ok`, 0 DL-vertex
  failures, 10 trees; cold event 213 s, 47 in parallel 323 s wall (57-145 s each, one at 320 s /
  2.54 GB), peak RSS otherwise <= 2.12 GB.
- Compare jobs: 8871176 (NCpi0 vs `work-ncpi0-m0925pr` and vs the 09-17 Aurora run
  `ncsb-data-20260917-1313`), 8871177 (nueCC-48 vs `work-nuecc48-m0925pr`; no earlier Aurora run of
  this sample exists).

### 2026-09-26 (d) comparison: NOT identical to Xin's m0925pr arms (0/19, 0/48); the cause is the light source, measured

Jobs 8871176 / 8871177 (`compare-xin.pbs`), reports in `production-prep/<run>/cmp-xin/`.

**Result vs Xin.** deep_compare exact match **0/19** (NCpi0) and **0/48** (nueCC-48): every event
differs in T_kine, T_tagger and the T_rec_charge point hash, most also in the T_rec_charge point
count. Every-branch census: 1134 (NCpi0) / 1171 (nueCC) differing (tree, branch) pairs; among
them, in **every** event, `T_cluster.flash_time_us`, `flash_pe`, `flash_id`, `matched_flash_gid`,
`T_tagger.flash_time_us/flash_pe/matched_flash_gid`, and **`Trun.nu_n_flashes` in 18/19 and 46/48
events** -- the number of flashes in the event itself is different. Bee (Xin's 7 layers): 0/19 and
0/48 identical.

**Where the two chains part.** Per-point comparison of Xin's `clustering-global` layer with our
`clustering-pr-global` layer (same content; the 1-step's own `clustering-global` is the pre-PR
grouping, 25 clusters vs 124):

| event | real clusters Xin / ours | points Xin / ours | (y, z, q) common | ours clusters x-shifted | shifts (cm) |
|---|---|---|---|---|---|
| 18625 | 131 / 124 | 27071 / 27014 | 26992 | 10 / 124 (576 pts) | 61.5, 1.1, 113.4, 11.7 |
| 56982 | 85 / 86 | 37873 / 37880 | 37873 | 5 / 85 (3996 pts) | 137.7, -23.5, -140.8 |
| 84229 | 69 / 69 | 18587 / 18587 | 18587 | 6 / 69 (120 pts) | 99.5, -15.7, -23.6, 158.9 |

The (y, z, q) point sets are the same to the last digit, i.e. **imaging and clustering are
identical**; a handful of clusters per event sit at a different x, i.e. they were matched to a
**different flash (different t0)**, and the PR stage then runs on a different picture. This is
exactly what doc sbnd_xin/123 describes for the `flash_source=hits` flip (clusters move to flashes
reco1 never had) and what sec 17.4 / 19.5 predict for the 1-step chain.

**Ruled out.**
- Toolkit mismatch: Xin's `tracking-pr.root` provenance (`SbndPrMagnifyTrackingVisitor:pr
  .provenance` in `.wct-cfg-evt<E>.json`) records `toolkit_git = 129362fe57a0...` -- the exact
  `origin/master` commit our branch now equals -- `wcp_git = e396d5b8-dirty` (= the
  "FLIP flash_source=hits into standalone production" commit), the same BDT / DL weights
  (`XGB_nue_seed2_0923.xml`, `numu_scalars_scores_0923.xml`, `t48k-m16-l5-lr5d-res0.5-CP24.pth`),
  the same `sbnd_track_fitting.json`.
- PR operating point: two-chain gate PASS (G4b), and a direct key-by-key diff of Xin's per-event
  PR config against our compiled 1-step config: 38 common components, 10 differing keys, all
  structural (Bee sink wiring, output filenames, `pipeline` +`PrDisplayDump:pr`, `save_deadarea`,
  `vertex_scoreboard` = a PrDisplayDump calib-json diagnostic).
- Q/L config: the only difference in the compiled Q/L job is the light gate
  (`xtpc_sc1_light_gate=true`, `xtpc_sc1_overpred_max=2.9` only in Xin's, G4).
- wire-cell-data: 1 commit behind upstream, a DUNE FM file only.

**Result vs our previous Aurora run** (NCpi0, toolkit `9195180d` -> `2982785a`): 0/19 identical, as
expected from a toolkit update -- but with the opposite signature: **no flash branch moves**
(`Trun` identical, `T_cluster` differs only in the flags `beam_flash`/`fc`/`lm`/`tgm`), the Bee
clustering layers are point-identical (0 x shifts), and the movement is in the PR tail (T_kine 31
branches, T_tagger 1081, T_rec_charge 19). nueCC-48 has no earlier Aurora run.

**Conclusion.** Our updated-master 1-step on Aurora runs the same toolkit commit, the same PR
operating point and the same imaging/clustering as Xin's wcgpu1 production, but Xin's standalone
chain has run hit-rebuilt flashes + the light gate since 2026-09-25 while the 1-step reads
`recob::OpFlash` and has no light gate. The expectation "identical to Xin's run" cannot be met by
construction on these arms. Two ways to close it: (1) an **off-path arm** of Xin's m0925 run
(`SBND_FLASH_SOURCE=reco1`, `SBND_XTPC_SC1_GATE=0`, i.e. the pre-09-25 production light; doc 123
sec 17.3 and 19 show that path reproduces the previous production 48/48), which should then be
exact vs ours; (2) implement `wclsOpHitSource` in larwirecell + `SBNDOpFlashFinder` in the 1-step
jsonnet (doc 123 sec 16 design) so the 1-step follows production light.

**Bee sets for review** (each pair in the same ascending event order, `bee-upload/bee-order.txt`;
Aurora = all 1-step layers, Xin = his 7 PR layers):

| sample | Aurora (new master) | Xin m0925pr (wcgpu1) |
|---|---|---|
| NCpi0-19 | https://www.phy.bnl.gov/twister/bee/set/64458bde-49c7-46d8-b57d-7caae3923c99/event/list/ | https://www.phy.bnl.gov/twister/bee/set/ebf1fe90-aefd-4439-a82b-91517b9fc933/event/list/ |
| nueCC-48 | https://www.phy.bnl.gov/twister/bee/set/8cedc770-bc0d-4f2b-922c-3e7b79cdfafd/event/list/ | https://www.phy.bnl.gov/twister/bee/set/bab92eaf-0822-4942-a5d6-63d194a10a24/event/list/ |

Previous Aurora NCpi0 run (toolkit 9195180d) for the before/after look: Bee 863b9ee0-d159-4b91-b633-e27f3883b207 (#29).

### 2026-09-26 (e) path 2 chosen: the hit-flash light in the 1-step chain, keeping the OpFlash chain

Haiwang: "implement equivalent path using OpHitSource and keep the option to run current
OpFlash based chain", reference `wire-cell-sbnd-reco1/src/SBNDReco1OpHitSource.cxx`; that package
(bare-ROOT mirror dictionaries of `recob::*`) must not be loaded in the LArSoft chain.

Implementation (doc sbnd_xin/123 sec 16, items 1-4):

1. **larwirecell `wclsOpHitSource`** (`larwirecell/Components/OpHitSource.{h,cxx}`, commit `f8177c7`
   on `dev-v10_14_02_02`): `IArtEventVisitor` + `ITensorSetSource` like `wclsOpFlashSource`; reads
   `recob::OpHit` (`art_tag`, default `ophitpmt`), keeps the `channels` list, emits the tensor
   `"ophits"` f8 `[nhit, 9]` = {OpChannel, time, width, area, amplitude, PE, start, -1, fast/total}
   with the same row layout, `units::microsecond` scaling and `hit_time` convention (`rise` =
   StartTime + RiseTime) as `SBNDReco1OpHitSource`, and set metadata run/subrun/event +
   `frame_apply_at_caf` (FrameShiftInfo `FrameApplyAtCaf()`, 0 when absent -- the
   `wclsOpFlashSource` rule). `SBNDOpFlashFinder` passes the set metadata through, so
   `FlashTensorToOpticalPCs` applies the same offset as before.
2. **Toolkit jsonnet** (`cfg/pgrapher/experiment/sbnd/`): the monolithic job became the function
   `wcls-img-clus-matching-xin-lib.jsonnet(flash_source='reco1', hit_time='rise', ff={},
   xtpc_sc1_light_gate=null, xtpc_sc1_overpred_max=null)`; `wcls-img-clus-matching-xin.jsonnet` =
   `(import lib)()` (must compile byte-identical); new `wcls-img-clus-matching-xin-hits.jsonnet` =
   `(import lib)(flash_source='hits', xtpc_sc1_light_gate=true, xtpc_sc1_overpred_max=2.9)`, i.e.
   `wclsOpHitSource:tpc<N>` (channels from `sbnd-pmt-channels.json`) -> `SBNDOpFlashFinder:tpc<N>`
   (nchan 312, `sbnd-opdet-geom.json`, production defaults) into `flash_attach` port 1, plus the
   light gate on `QLMatching:matching_joint` -- the two 2026-09-25 flips of the standalone chain
   (`wct-reco1-dump.jsonnet` `flash_source='hits'`, `wct-clus-matching-perevt.jsonnet` gate TLAs).
   No new required extVar on the reco1 path (Xin's `compile_consumers.sh` / tripwire unaffected);
   the hits path reads `ophit<N>_input_label` lazily.
3. **fcls** (`wcp-porting-validation/sbnd/`): `wcls-img-clus-matching-xin-hits.fcl` (MC) and
   `-data-hits.fcl` include the OpFlash fcls and override `configs`, `plugins` (+`WireCellFlash`),
   `inputers` (`wclsOpHitSource:tpc0/1` instead of `wclsOpFlashSource:tpc0/1`) and add
   `ophit0/1_input_label: "ophitpmt"` (process Reco1 in both data and MC reco1, checked in the
   event dumps of all four samples). Bare-name re-export `sbnd/wcls-img-clus-matching-xin-hits.jsonnet`.
4. **Gates**: `gate-1step-cfg.sh` (run by `build-wct-lwc.pbs` step 3): G-A the reco1 job compiles
   byte-identical to the pre-split file taken from `origin/master`, sim and data extVar sets; G-B
   the hits job compiles and differs from the reco1 job only in the light nodes, the two
   `xtpc_sc1_*` keys and the plugin list. Then the full-chain gate: the hits 1-step on nueCC-48 +
   NCpi0-19 vs Xin's `m0925pr` arms with `compare-xin.pbs` -- the standalone chain's hit flashes
   are not on Flare, so flash-for-flash identity is tested through the final outputs.
- Build: `qsub -q debug -v STAGES=lwc,DO_CFG_GATE=1 build-wct-lwc.pbs` -> job 8871445
  (`build-lwc-ophit.out`).
