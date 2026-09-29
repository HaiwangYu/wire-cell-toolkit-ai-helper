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

### 2026-09-26 (f) hit-flash 1-step vs Xin: 60/67 exact, all flashes and all Bee content identical, residual = the cross-machine FP class

- Build job 8871445: larwirecell `f8177c7` rebuilt and deployed (`MRB_RC=0`); **gate G-A PASS** (reco1
  job byte-identical to the pre-split `origin/master` file, sim `8ab6b7ae3e7d` and data
  `274954ca7612`), **G-B PASS** (hits job = reco1 job + `wclsOpHitSource:tpc0/1` +
  `SBNDOpFlashFinder:tpc0/1` - `wclsOpFlashSource:tpc0/1`, `QLMatching` +`xtpc_sc1_light_gate=true`,
  `xtpc_sc1_overpred_max=2.9`, plugins +`WireCellFlash`; nothing else moves).
- Runs with `wcls-img-clus-matching-xin-data-hits.fcl`: NCpi0-19 `production-prep/ncsb-hits-20260926-0535`
  (job 8871473, 19/19 rc=0, audit ok, 92 s parallel wall), nueCC-48 `production-prep/nuecc48-hits-20260926-0535`
  (job 8871474, 48/48 rc=0, 293 s). The log shows the path: `<OpHitSource:tpc0> run 18255 subrun 1
  event 56982: emit 11992 of 22212 hits from ophitpmt (hit_time rise, frame_apply_at_caf 2608 ns)`.
  MC smoke `wcls-img-clus-matching-xin-hits.fcl` on Avinay's 50-event file
  (`production-prep/mc50-hits-20260926-0608`, job 8871528): 9/9 rc=0, audit ok, 23-60 s/event.
- **Comparison vs Xin's m0925pr arms** (jobs 8871498 / 8871499, `cmp-xin/` in the run dirs):

| | NCpi0-19 | nueCC-48 |
|---|---|---|
| deep_compare exact (T_kine, T_tagger, every T_rec_charge point) | **18/19** | **41/48** |
| census: flash branches differing (`Trun.nu_n_flashes`, `T_cluster/T_tagger.flash_*`) | **0** | **0** |
| census: `Trun`, `T_cluster` branches differing | 0 | 0 |
| Bee, Xin's 7 layers, content (`compare-bee-content.py`) | **19/19** | **46/48** |

  The remaining 7 (`evt-branch-diff.py`, `cmp-xin/evt-diff.txt`):
  - NCpi0 314838, nueCC 122660, 196649, 74544: `T_rec_charge` point hash only; the census puts
    every `T_rec_charge` branch at <= 1.4e-9 relative (q, reduced_chi2; x/y/z at 1e-15) -- the
    doc-24 cross-machine residual (FNAL vs wcgpu1 was ~1e-12; SL7-gcc12.1 vs Debian-gcc12.2 here).
  - nueCC 239794: `hol_2_ncount` / `shw_sp_hol_2_ncount` 1 vs 2 (two T_tagger counts); 90055:
    `ssm_offvtx_energy` 1013.19 vs 1013.53 (one scalar). No T_kine, no score change.
  - nueCC 131357 and 433451: a discrete PR-tail branch -- the T_rec_charge point count differs
    (384 vs 377, 1162 vs 1144), the track-fit dQ/dx vectors and the shower energies move
    (131357: `kine_reco_Enu` 768.87 -> 768.96 MeV, `nue_score` 11.74 -> 11.61; 433451:
    `kine_reco_Enu` 2405 -> 2487 MeV, `gap_energy` 1829 -> 1913, `numu_score` -1.19 -> -0.35,
    `nue_score` 11.18 -> 9.19), the Bee track_fit / shower_track / vertices / mc layers with them.
    Flashes, matching, clustering and the pre-fit T_cluster scalars are identical in both, so the
    branch is inside the PR fit -- the "FP-seeded discrete shower-sampling change" class of doc 24
    sec 7 (there 1/241 cross-machine; here 2/48 on this machine pair), reported, not tuned.
- Structural Bee differences excluded by `compare-bee-content.py` (all measured, none physics):
  Xin's `clustering-global` layer is the PR-stage grouping that the 1-step writes as
  `clustering-pr-global` (the label string `type` differs); the 1-step adds an `opflash_time` key
  per point; the `mc` node's text line carries the BDT scores in the 1-step and `numu 0.000
  nue 0.000` in Xin's PR job.
- Bee sets (same ascending event order in each pair):

| sample | Aurora hit-flash 1-step | Xin m0925pr |
|---|---|---|
| NCpi0-19 | https://www.phy.bnl.gov/twister/bee/set/60dc27dd-f834-4150-8785-d5d43ed4f9df/event/list/ | https://www.phy.bnl.gov/twister/bee/set/ad2e51ab-c463-472c-8cf6-8c39a0e79d2f/event/list/ |
| nueCC-48 | https://www.phy.bnl.gov/twister/bee/set/d0431af6-f345-457f-a713-8956185e7d11/event/list/ | https://www.phy.bnl.gov/twister/bee/set/158e6093-e9d1-4e47-b6ff-0405d315cdd0/event/list/ |

- vs the reco1-flash 1-step of (c) (same toolkit, `ncsb-m0925-20260926-0223` / `nuecc48-m0925-20260926-0223`):
  0/19 and 0/48 identical, as intended -- this is the light flip itself.
- Commits: larwirecell `f8177c7` (pushed, HaiwangYu), toolkit `c7e7775e` on `polaris-build-fixes`
  (pushed to the fork; a PR to WireCell master is the next step), wcp-porting-validation `d76afb08`
  (fcls + re-export), ai-helper scripts `gate-1step-cfg.sh`, `compare-bee-content.py`,
  `evt-branch-diff.py`, `evt-diff.pbs`, `compare-xin.pbs` step 4b.
- Both chains stay available: `wcls-img-clus-matching-xin[-data].fcl` = reco1 `recob::OpFlash`
  light (unchanged, byte-identical config), `-hits` = the standalone production light.

### 2026-09-26 (g) event-by-event: exactly what differs, hit-flash 1-step vs Xin's m0925pr (all 67 events)

Method: `evt-branch-diff.py --max 0 --json` (job 8872289) compares EVERY branch of all 8 trees of
`tracking-pr.root` at exact float, per event (`cmp-xin/evt-diff.{txt,json}` in the run dirs);
`compare-bee-content.py` compares Xin's 7 Bee layers at exact JSON value (`cmp-xin/bee_content.txt`);
`evt-diff-table.py` writes the tables. Classes:
- **fp**: only `T_rec_charge` differs, same number of points, every branch within the quoted relative
  precision (q, reduced_chi2 first, then the coordinates at 1e-15..1e-11) -- the float-precision
  residual between the two builds (SL7 gcc 12.1 vs Debian 12 gcc 12.2). `Trun`, `T_cluster`,
  `T_kine`, `T_tagger`, `T_bad_ch`, `T_proj`, `T_proj_data` are bit-identical.
- **discrete**: a `T_kine`/`T_tagger` branch or the `T_rec_charge` point count differs; the branches
  and values are listed.
- No event is bit-identical (the fp residual is in every event); at the deep_compare tolerance
  (1e-6 on T_kine/T_tagger, 1e-5 per T_rec_charge point) 18/19 + 41/48 are exact, as in (f).

Bee (same ascending event order in each pair; the table's `#` is the Bee event index + 1):

| sample | Aurora hit-flash 1-step (all layers) | Xin m0925pr (7 PR layers) |
|---|---|---|
| NCpi0-19 | https://www.phy.bnl.gov/twister/bee/set/60dc27dd-f834-4150-8785-d5d43ed4f9df/event/list/ | https://www.phy.bnl.gov/twister/bee/set/ad2e51ab-c463-472c-8cf6-8c39a0e79d2f/event/list/ |
| nueCC-48 | https://www.phy.bnl.gov/twister/bee/set/d0431af6-f345-457f-a713-8956185e7d11/event/list/ | https://www.phy.bnl.gov/twister/bee/set/158e6093-e9d1-4e47-b6ff-0405d315cdd0/event/list/ |

**NCpi0-19, hit-flash 1-step vs Xin m0925pr** -- 19 events: exact 0, float-precision residual only 19, discrete difference 0

| # (Bee) | run subrun event | class | tracking-pr.root: what exactly differs (Xin -> Aurora) | Bee content (Xin's 7 layers) |
|---|---|---|---|---|
| 1 | r18259 s1 e18625 | fp | T_rec_charge only, same 822 points: q, reduced_chi2, nq, pt, y, rr, x, pw, z, pu at <= 4.0e-13 relative (float-precision residual) | identical (7 layers) |
| 2 | r18345 s1 e21073 | fp | T_rec_charge only, same 783 points: q, reduced_chi2, nq, rr, x, y, pt at <= 1.4e-12 relative (float-precision residual) | identical (7 layers) |
| 3 | r18259 s1 e37112 | fp | T_rec_charge only, same 427 points: q, reduced_chi2 at <= 6.4e-13 relative (float-precision residual) | identical (7 layers) |
| 4 | r18255 s1 e56982 | fp | T_rec_charge only, same 658 points: q, reduced_chi2, nq, rr, x, pt, y, pv, z, pu at <= 4.0e-10 relative (float-precision residual) | identical (7 layers) |
| 5 | r18255 s1 e71372 | fp | T_rec_charge only, same 1458 points: reduced_chi2, q, nq, rr, pt, y, z, x, pu, pv, pw at <= 2.8e-12 relative (float-precision residual) | identical (7 layers) |
| 6 | r18364 s1 e84229 | fp | T_rec_charge only, same 806 points: q, reduced_chi2, rr, nq, y, z, x, pt, pu, pw, pv at <= 5.2e-12 relative (float-precision residual) | identical (7 layers) |
| 7 | r18259 s1 e105946 | fp | T_rec_charge only, same 491 points: q, reduced_chi2, rr, nq, z at <= 3.1e-13 relative (float-precision residual) | identical (7 layers) |
| 8 | r18255 s1 e114446 | fp | T_rec_charge only, same 519 points: reduced_chi2, q, nq, rr, pt, x, y, z at <= 2.8e-13 relative (float-precision residual) | identical (7 layers) |
| 9 | r18255 s1 e142421 | fp | T_rec_charge only, same 1238 points: q, reduced_chi2, nq, rr, x, pt, z at <= 2.4e-13 relative (float-precision residual) | identical (7 layers) |
| 10 | r18255 s1 e180801 | fp | T_rec_charge only, same 628 points: q, reduced_chi2, pu at <= 3.2e-13 relative (float-precision residual) | identical (7 layers) |
| 11 | r18345 s1 e259542 | fp | T_rec_charge only, same 861 points: q, reduced_chi2, nq, rr, y, pt, x, z at <= 5.2e-13 relative (float-precision residual) | identical (7 layers) |
| 12 | r18261 s1 e285567 | fp | T_rec_charge only, same 824 points: q, reduced_chi2, nq, rr, x, y, z, pt, pu, pw, pv at <= 3.5e-12 relative (float-precision residual) | identical (7 layers) |
| 13 | r18255 s1 e314838 | fp | T_rec_charge only, same 644 points: q, reduced_chi2, nq, rr, x, y, z, pt, pw, pv, pu at <= 1.4e-09 relative (float-precision residual) | identical (7 layers) |
| 14 | r18255 s1 e359980 | fp | T_rec_charge only, same 463 points: q, reduced_chi2, nq, rr, x, y, pt, pu, z, pw, pv at <= 4.1e-13 relative (float-precision residual) | identical (7 layers) |
| 15 | r18255 s1 e399860 | fp | T_rec_charge only, same 574 points: q, reduced_chi2, nq, rr, x, y, pu at <= 5.0e-13 relative (float-precision residual) | identical (7 layers) |
| 16 | r18255 s1 e463565 | fp | T_rec_charge only, same 719 points: q, nq, reduced_chi2, rr, x, y, pt, z, pw, pu, pv at <= 3.1e-12 relative (float-precision residual) | identical (7 layers) |
| 17 | r18255 s1 e506114 | fp | T_rec_charge only, same 915 points: q, reduced_chi2, nq, rr, y, pt, x, z, pw, pu, pv at <= 1.6e-10 relative (float-precision residual) | identical (7 layers) |
| 18 | r18255 s1 e506746 | fp | T_rec_charge only, same 790 points: q, reduced_chi2, nq, rr, pt, pu, y, z, x, pw, pv at <= 5.1e-12 relative (float-precision residual) | identical (7 layers) |
| 19 | r18255 s1 e521075 | fp | T_rec_charge only, same 261 points: q, reduced_chi2 at <= 3.0e-13 relative (float-precision residual) | identical (7 layers) |

**nueCC-48, hit-flash 1-step vs Xin m0925pr** -- 48 events: exact 0, float-precision residual only 44, discrete difference 4

| # (Bee) | run subrun event | class | tracking-pr.root: what exactly differs (Xin -> Aurora) | Bee content (Xin's 7 layers) |
|---|---|---|---|---|
| 1 | r18255 s1 e388 | fp | T_rec_charge only, same 1014 points: q, nq, reduced_chi2, rr, y, pt, x, pu, z, pv, pw at <= 1.6e-10 relative (float-precision residual) | identical (7 layers) |
| 2 | r18255 s1 e10550 | fp | T_rec_charge only, same 443 points: q, reduced_chi2 at <= 8.5e-14 relative (float-precision residual) | identical (7 layers) |
| 3 | r18342 s1 e30504 | fp | T_rec_charge only, same 569 points: q, reduced_chi2, rr, nq, y, x, z, pw, pu, pt, pv at <= 6.6e-13 relative (float-precision residual) | identical (7 layers) |
| 4 | r18304 s1 e38856 | fp | T_rec_charge only, same 607 points: q, reduced_chi2, nq, y, rr, x, pt, pu, z, pw, pv at <= 3.1e-13 relative (float-precision residual) | identical (7 layers) |
| 5 | r18259 s1 e42280 | fp | T_rec_charge only, same 925 points: q, nq, reduced_chi2, rr, y, x, z, pt, pu, pv at <= 7.2e-13 relative (float-precision residual) | identical (7 layers) |
| 6 | r18255 s1 e46363 | fp | T_rec_charge only, same 932 points: q, reduced_chi2, rr, nq, y, x, z, pu, pt, pw, pv at <= 4.2e-10 relative (float-precision residual) | identical (7 layers) |
| 7 | r18259 s1 e52672 | fp | T_rec_charge only, same 612 points: q, reduced_chi2, nq, rr, y, pt, x, pu at <= 6.3e-13 relative (float-precision residual) | identical (7 layers) |
| 8 | r18259 s1 e54095 | fp | T_rec_charge only, same 1256 points: q, reduced_chi2, nq, rr, pt, y, x, z, pu, pv at <= 6.6e-11 relative (float-precision residual) | identical (7 layers) |
| 9 | r18255 s1 e69314 | fp | T_rec_charge only, same 807 points: q, reduced_chi2, nq, y, rr, pt, x, z, pu, pw, pv at <= 8.9e-13 relative (float-precision residual) | identical (7 layers) |
| 10 | r18259 s1 e74544 | fp | T_rec_charge only, same 762 points: q, reduced_chi2, nq, rr, y, pt, z, x, pw, pu, pv at <= 1.8e-11 relative (float-precision residual) | identical (7 layers) |
| 11 | r18313 s1 e81597 | fp | T_rec_charge only, same 675 points: q, reduced_chi2, nq, rr, y, pt, x, pu, z at <= 5.7e-13 relative (float-precision residual) | identical (7 layers) |
| 12 | r18255 s1 e90055 | discrete | T_rec_charge nq, pt, pu, pv, pw, q, reduced_chi2, rr, x, y, z at <= 9.4e-12 rel / T_tagger (1): `ssm_offvtx_energy` 1013.19 -> 1013.53 | identical (7 layers) |
| 13 | r18259 s1 e111412 | fp | T_rec_charge only, same 427 points: q, reduced_chi2, nq, rr, pt, y, x at <= 1.3e-11 relative (float-precision residual) | identical (7 layers) |
| 14 | r18259 s1 e116962 | fp | T_rec_charge only, same 466 points: q, reduced_chi2 at <= 1.7e-13 relative (float-precision residual) | identical (7 layers) |
| 15 | r18255 s1 e122660 | fp | T_rec_charge only, same 821 points: q, reduced_chi2, nq, rr, y, pu, z, x, pt at <= 1.2e-09 relative (float-precision residual) | identical (7 layers) |
| 16 | r18259 s1 e131357 | discrete | T_rec_charge 384 vs 377 points / T_kine (2): `kine_reco_Enu` 768.868 -> 768.958; `kine_energy_particle` [154.727, 601.541, 4.0002] -> [154.817, 601.541, 4.0002] / T_tagger (482 branches): `mip_n_lowest` 9 -> 8; `mip_length_main` 111.501 -> 109.472; `ssm_offvtx_length` 114.549 -> 113.09; `ssm_offvtx_energy` 279.714 -> 279.844; `ssm_offvtx_track1_dist_mainvtx` 53.4715 -> 53.4939; `ssm_offvtx_shw1_score_mu_fwd` 0.15868 -> 0.138056; `ssm_offvtx_shw1_score_p_fwd` 0.878462 -> 0.826892; `ssm_offvtx_shw1_score_e_fwd` 0.25061 -> 0.249711; `ssm_offvtx_shw1_score_mu_bck` 0.506031 -> 0.422702; `ssm_offvtx_shw1_score_p_bck` 1.48469 -> 1.33042; ... / HEADLINE `kine_reco_Enu` 768.868 -> 768.958; `nue_score` 11.744 -> 11.6088 | mc, shower_track-global, track_fit-global, vertices-global |
| 17 | r18264 s1 e137238 | fp | T_rec_charge only, same 638 points: q, nq, reduced_chi2, rr, y, pt, x, pu, z at <= 7.9e-12 relative (float-precision residual) | identical (7 layers) |
| 18 | r18255 s1 e138009 | fp | T_rec_charge only, same 579 points: q, reduced_chi2, nq, rr, pu, z, x, pt, y at <= 1.3e-12 relative (float-precision residual) | identical (7 layers) |
| 19 | r18255 s1 e163543 | fp | T_rec_charge only, same 643 points: reduced_chi2, q at <= 4.6e-13 relative (float-precision residual) | identical (7 layers) |
| 20 | r18255 s1 e168596 | fp | T_rec_charge only, same 921 points: q, reduced_chi2, nq, rr, y, pt, z, x, pu, pw, pv at <= 1.6e-11 relative (float-precision residual) | identical (7 layers) |
| 21 | r18253 s1 e172230 | fp | T_rec_charge only, same 745 points: q, reduced_chi2, rr, nq, x, z, y, pt, pu at <= 4.5e-11 relative (float-precision residual) | identical (7 layers) |
| 22 | r18255 s1 e174637 | fp | T_rec_charge only, same 478 points: q, nq, reduced_chi2, rr, pt, y, x, pw, pv, z, pu at <= 2.7e-12 relative (float-precision residual) | identical (7 layers) |
| 23 | r18255 s1 e196649 | fp | T_rec_charge only, same 824 points: q, reduced_chi2, nq, rr, y, z, pu, pw, pv at <= 1.5e-10 relative (float-precision residual) | identical (7 layers) |
| 24 | r18409 s1 e214469 | fp | T_rec_charge only, same 1176 points: q, reduced_chi2, rr, nq, y, x, pt, z, pu, pv, pw at <= 1.6e-11 relative (float-precision residual) | identical (7 layers) |
| 25 | r18255 s1 e219295 | fp | T_rec_charge only, same 767 points: q, reduced_chi2, nq, rr, y, pt, pu, pw, z, x, pv at <= 6.5e-13 relative (float-precision residual) | identical (7 layers) |
| 26 | r18255 s1 e234638 | fp | T_rec_charge only, same 790 points: q, reduced_chi2, nq, rr, y, pv at <= 2.9e-13 relative (float-precision residual) | identical (7 layers) |
| 27 | r18255 s1 e235435 | fp | T_rec_charge only, same 263 points: q, reduced_chi2, nq, rr, y, pu, pt, x at <= 4.6e-11 relative (float-precision residual) | identical (7 layers) |
| 28 | r18255 s1 e239794 | discrete | T_rec_charge nq, pt, pu, pv, pw, q, reduced_chi2, rr, x, y, z at <= 1.5e-12 rel / T_tagger (2): `shw_sp_hol_2_ncount` 1 -> 2; `hol_2_ncount` 1 -> 2 | identical (7 layers) |
| 29 | r18255 s1 e246579 | fp | T_rec_charge only, same 929 points: q, reduced_chi2, rr, nq, x, z, y, pv, pt, pu at <= 1.6e-11 relative (float-precision residual) | identical (7 layers) |
| 30 | r18306 s1 e256587 | fp | T_rec_charge only, same 1874 points: q, reduced_chi2, nq, rr, y, pt, x, z, pu, pw, pv at <= 9.0e-11 relative (float-precision residual) | identical (7 layers) |
| 31 | r18279 s1 e267597 | fp | T_rec_charge only, same 840 points: q, reduced_chi2, nq, rr, x, y, pt at <= 5.8e-13 relative (float-precision residual) | identical (7 layers) |
| 32 | r18255 s1 e268067 | fp | T_rec_charge only, same 526 points: q, reduced_chi2, nq, y, rr, pt, pu, x at <= 1.5e-12 relative (float-precision residual) | identical (7 layers) |
| 33 | r18255 s1 e268784 | fp | T_rec_charge only, same 854 points: q, reduced_chi2, rr, nq, y, x, pt, z, pu, pv, pw at <= 1.0e-11 relative (float-precision residual) | identical (7 layers) |
| 34 | r18255 s1 e269774 | fp | T_rec_charge only, same 1179 points: q, reduced_chi2, nq, rr, y, z, x, pt, pw, pv at <= 7.1e-12 relative (float-precision residual) | identical (7 layers) |
| 35 | r18255 s1 e271851 | fp | T_rec_charge only, same 884 points: q, reduced_chi2, nq, rr, y, pt, x, z, pu, pw, pv at <= 2.9e-11 relative (float-precision residual) | identical (7 layers) |
| 36 | r18269 s1 e342199 | fp | T_rec_charge only, same 613 points: q, reduced_chi2, y, nq at <= 1.8e-11 relative (float-precision residual) | identical (7 layers) |
| 37 | r18255 s1 e350186 | fp | T_rec_charge only, same 316 points: q, reduced_chi2, nq, rr, y, pu at <= 1.9e-13 relative (float-precision residual) | identical (7 layers) |
| 38 | r18255 s1 e360535 | fp | T_rec_charge only, same 834 points: q, nq, reduced_chi2, rr, pt, z, pv, pu, x at <= 5.7e-12 relative (float-precision residual) | identical (7 layers) |
| 39 | r18255 s1 e389538 | fp | T_rec_charge only, same 946 points: reduced_chi2, q, nq, rr, y, pt, x, pu, z, pw, pv at <= 6.8e-13 relative (float-precision residual) | identical (7 layers) |
| 40 | r18355 s1 e400474 | fp | T_rec_charge only, same 810 points: q, reduced_chi2, nq, rr, x, y, pt, z, pw, pu, pv at <= 8.6e-13 relative (float-precision residual) | identical (7 layers) |
| 41 | r18255 s1 e422851 | fp | T_rec_charge only, same 649 points: q, nq, rr, reduced_chi2, y, pt, z, x, pw, pv, pu at <= 2.9e-13 relative (float-precision residual) | identical (7 layers) |
| 42 | r18255 s1 e423981 | fp | T_rec_charge only, same 760 points: q, reduced_chi2, nq, rr, x, y, z, pt, pw, pv, pu at <= 7.3e-13 relative (float-precision residual) | identical (7 layers) |
| 43 | r18255 s1 e433451 | discrete | T_rec_charge 1162 vs 1144 points / T_kine (16 branches): `kine_nu_x_corr` -150.143 -> -150.228; `kine_nu_y_corr` 43.4994 -> 43.5209; `kine_nu_z_corr` 211.292 -> 211.535; `kine_reco_Enu` 2405.45 -> 2487.34; `kine_energy_particle` [72.2572, 1829.12, 54.4962, 113.633, ..] -> [71.513, 1912.52, 54.8281, 112.541, ..]; `kine_pio_mass` 39.0119 -> 39.1652; `kine_pio_energy_1` 1829.12 -> 1912.52; `kine_pio_theta_1` 18.8442 -> 20.0868; `kine_pio_phi_1` -23.7074 -> -22.9896; `kine_pio_theta_2` 18.7583 -> 18.8178; ... / T_tagger (597 branches): `nu_x` -150.143 -> -150.228; `nu_y` 43.4994 -> 43.5209; `nu_z` 211.292 -> 211.535; `gap_energy` 1829.12 -> 1912.52; `mip_energy` 1829.12 -> 1912.52; `mip_n_lowest` 5 -> 6; `mip_length_main` 244.837 -> 244.236; `ssm_offvtx_length` 196.124 -> 186.715; `ssm_offvtx_energy` 926.407 -> 936.803; `ssm_offvtx_track1_score_mu_fwd` 0.192559 -> 1.30266; ... / HEADLINE `kine_reco_Enu` 2405.45 -> 2487.34; `kine_pio_mass` 39.0119 -> 39.1652; `numu_score` -1.18608 -> -0.350157; `nue_score` 11.1784 -> 9.19255 | mc, shower_track-global, track_fit-global, vertices-global |
| 44 | r18255 s1 e437699 | fp | T_rec_charge only, same 692 points: q, reduced_chi2, nq, rr, z, x, y, pt, pu, pw, pv at <= 3.4e-13 relative (float-precision residual) | identical (7 layers) |
| 45 | r18253 s1 e444187 | fp | T_rec_charge only, same 451 points: q, rr, nq, reduced_chi2, x, y, z, pt, pw, pu, pv at <= 6.1e-13 relative (float-precision residual) | identical (7 layers) |
| 46 | r18255 s1 e447477 | fp | T_rec_charge only, same 537 points: q, nq, reduced_chi2, rr, y, pt, x, z, pu at <= 2.8e-13 relative (float-precision residual) | identical (7 layers) |
| 47 | r18255 s1 e469665 | fp | T_rec_charge only, same 379 points: q, nq, rr, reduced_chi2, y, x, pt, z, pu, pv at <= 3.0e-13 relative (float-precision residual) | identical (7 layers) |
| 48 | r18255 s1 e489330 | fp | T_rec_charge only, same 879 points: q, reduced_chi2, nq, rr, x, z, pt, y, pw, pv, pu at <= 4.4e-12 relative (float-precision residual) | identical (7 layers) |

### 2026-09-26 (h) BDT scores added to Xin's Bee sets; provenance of the Bee particle flow and scores

**Particle flow (PID, energy, position).** Both chains write the Bee "mc" layer from the same code, `MultiAlgBlobClustering::fill_bee_pf_tree` (clus/src/MultiAlgBlobClustering.cxx), configured by `bee_pf` on the `clus_pr` MABC. It walks the PR graph of the neutrino candidate's `TrackFitting` (the main vertex, its segments and daughter vertices) and makes one node per segment/shower: the label is `particle_info()->pdg()` mapped to a name (the PR particle ID from the dQ/dx and topology tests) plus `particle_info()->kinetic_energy()` (range/dQ/dx energy for tracks, the shower energy for showers, printed in MeV); `data.start`/`data.end` are the first and last **fit points** of the segment (`seg->fits()`, T0-corrected, oriented by `dirsign`); `children` follow the vertex/segment tree. So PID, energy and position are the PR stage's own fit results, identical in both arms (the `mc` layers matched in 65/67 events).

**BDT scores.** The summary node on top ("reco nu <Enu> MeV numu <s> nue <s>", `pf_summary_node`) prints `TrackFitting`'s `KineInfo.kine_reco_Enu`, `TaggerInfo.numu_score` and `nue_score` **at the moment the dump runs** -- `bee_pf.visitor` says after which pipeline stage. The scores are set by `UbooneNumuBDTScorer:pr` / `UbooneNueBDTScorer:pr` (XGBoost, `uboone/weights/numu_scalars_scores_0923.xml` and `XGB_nue_seed2_0923.xml`, on the T_tagger variables). The 1-step dumps with `visitor: UbooneNueBDTScorer:pr` (after both scorers); Xin's `wct-pr-perevt.jsonnet` dumps with `visitor: TaggerCheckNeutrino:pr`, i.e. **before** the scorers, so his text reads `numu 0.000 nue 0.000` while the scores themselves are in his `tracking-pr.root` (`T_tagger.numu_score/nue_score`, written by `UbooneTaggerOutputVisitor` after the scorers).

**What I did.** `extract-scores.py` reads `T_tagger.numu_score`, `nue_score` and `T_kine.kine_reco_Enu` from Xin's own `tracking-pr.root` per event; `add-scores-to-bee.py` rewrites only the summary node's text of his `mabc-pr.zip` in the toolkit's own format (`"reco nu  %.1f MeV   numu %.3f   nue %.3f"`), nothing else in the zips changes. Cross-check: the patched text equals the 1-step's text in **65/67** events; the two exceptions are the two discrete events (131357: nue 11.744 vs 11.609; 433451: 2405.5 vs 2487.3 MeV, numu -1.186 vs -0.350, nue 11.178 vs 9.193), i.e. exactly the T_kine/T_tagger differences in the table above.

The links in the table above are replaced by the scored sets: NCpi0 [b2a709d5](https://www.phy.bnl.gov/twister/bee/set/b2a709d5-a914-4ff3-8996-3e31fd7f4ad0/event/list/), nueCC [6b0235bc](https://www.phy.bnl.gov/twister/bee/set/6b0235bc-0db8-4501-80ed-74a9d4ecd67a/event/list/) (same events, same order; the unscored originals ad2e51ab / 158e6093 stay up). Tools in `issues/29-aurora-production/scripts/`: `extract-scores.py`, `add-scores-to-bee.py`, `run-sl7.pbs`.

### 2026-09-29 (i) NCpi0: the r3 (#30, FNAL, 0ad64223, reco1 flash) arm vs Xin m0925pr, next to the hit-flash re-run

**r3** = `production-prep/r3-ncpi0-lynn-2026-09-15`: the FNAL 1-step of campaign #30, toolkit `0ad64223` (master-2026-09-08+yuhw), reco1 `recob::OpFlash` light, `wcls-img-clus-matching-xin-data.fcl`. **hits** = the current Aurora hit-flash 1-step (toolkit `2982785a` = master 129362fe + the hits job). **Xin** = `work-ncpi0-m0925pr` (wcgpu1, toolkit 129362fe, hit flashes + light gate), scores added from his `tracking-pr.root`.

**Bee, all 19 events, same ascending event order in all three sets:** r3 [051ee22b](https://www.phy.bnl.gov/twister/bee/set/051ee22b-049e-4465-a008-0203bc948b01/event/list/) · hits [60dc27dd](https://www.phy.bnl.gov/twister/bee/set/60dc27dd-f834-4150-8785-d5d43ed4f9df/event/list/) · Xin (scored) [b2a709d5](https://www.phy.bnl.gov/twister/bee/set/b2a709d5-a914-4ff3-8996-3e31fd7f4ad0/event/list/)

**Size of the difference (from the Bee content; the `tracking-pr.root` census follows):**

| | r3 vs Xin | hits vs Xin |
|---|---|---|
| Bee content identical (Xin's 7 layers) | **0/19** | **19/19** |
| reco Enu, \|Δ\|/Enu | median **15.9 %**, mean 20.1 %, max 83.3 % (e114446: 753 → 126 MeV) | 0 in all 19 |
| numu score, \|Δ\| | median 0.28, max 2.21 | 0 |
| nue score, \|Δ\| | median 0.00, max 13.31 | 0 |
| particle-flow list (PID × count) identical | **0/19** | 19/19 |
| PR clustering points, (y, z, q) common with Xin | 93.7-100 % | 100 % |
| clusters at a different x (= matched to another flash / t0) | 2-22 per event | 0 |

So the r3 arm differs from Xin in every event at the level of the physics output: a different light source matches 2-22 clusters per event to a different flash, and 2.5 weeks of PR changes (09-08 → 09-25: charge_stepped retile, Steiner prefer3, nu_bundle_flash_group, the 25-key operating-point fix, ...) change the particle flow of every candidate. The current hit-flash re-run removes all of it: its only differences to Xin are the float-precision residual in `T_rec_charge` of every event and nothing else in NCpi0 (table above).

Per event (Enu MeV / numu / nue; "clusters at another x" counts r3's PR clusters with > 50 % of their points shifted in x vs Xin; particle deltas are Xin → r3):

| # | event | Xin: Enu / numu / nue | r3 (FNAL, 0ad64223, reco1 flash) | hits (Aurora, 2982785a) | r3 PR points: yzq-common with Xin, clusters at another x | PF particles Xin -> r3 |
|---|---|---|---|---|---|---|
| 1 | r18259 s1 e18625 | 1502.5 / 0.59 / -15.00 | 1448.6 / 2.80 / -15.00 | 1502.5 / 0.59 / -15.00 | 26983/27062 (99.7%), 10/124 clusters | mu- 0->1, neutron 0->2, pi+ 1->0, proton 4->5 |
| 2 | r18345 s1 e21073 | 1400.5 / 0.56 / -7.36 | 1623.7 / -0.70 / -2.50 | 1400.5 / 0.56 / -7.36 | 15225/15225 (100.0%), 7/67 clusters | 0 1->0, mu- 3->2, neutron 3->0, pi+ 1->0, proton 2->1 |
| 3 | r18259 s1 e37112 | 1119.5 / 0.64 / -2.75 | 1147.8 / -0.61 / -2.62 | 1119.5 / 0.64 / -2.75 | 23063/23063 (100.0%), 22/84 clusters | e- 2->4, gamma 1->3, neutron 2->1, proton 3->1 |
| 4 | r18255 s1 e56982 | 1109.6 / 0.23 / 2.83 | 1268.5 / 0.07 / -4.82 | 1109.6 / 0.23 / 2.83 | 37822/37822 (100.0%), 5/85 clusters | e- 8->6, mu- 1->2, neutron 1->5, pi+ 0->1, proton 0->3 |
| 5 | r18255 s1 e71372 | 2290.5 / 1.80 / -15.00 | 2422.8 / 1.71 / -15.00 | 2290.5 / 1.80 / -15.00 | 37059/37059 (100.0%), 4/132 clusters | e- 6->5, mu- 2->1, neutron 2->0, pi+ 0->1, proton 1->0 |
| 6 | r18364 s1 e84229 | 1305.2 / 0.50 / -15.00 | 1492.2 / 0.62 / -15.00 | 1305.2 / 0.50 / -15.00 | 18587/18587 (100.0%), 6/69 clusters | gamma 2->3, mu- 4->1, neutron 3->1 |
| 7 | r18259 s1 e105946 | 1098.6 / -0.23 / -15.00 | 923.2 / -0.15 / -15.00 | 1098.6 / -0.23 / -15.00 | 7995/8071 (99.1%), 8/56 clusters | neutron 1->0, pi0 1->0, proton 3->1 |
| 8 | r18255 s1 e114446 | 753.0 / -0.64 / -15.00 | 125.8 / -2.74 / -15.00 | 753.0 / -0.64 / -15.00 | 34750/35052 (99.1%), 10/57 clusters | e- 1->0, gamma 1->0, mu- 3->0, neutron 2->0, proton 0->1 |
| 9 | r18255 s1 e142421 | 2110.7 / 2.69 / -15.00 | 2678.3 / 3.05 / -15.00 | 2110.7 / 2.69 / -15.00 | 29484/29488 (100.0%), 8/106 clusters | e- 6->3, gamma 5->3, mu- 5->2, neutron 5->2, pi+ 1->2, proton 8->4 |
| 10 | r18255 s1 e180801 | 1241.8 / -0.10 / -15.00 | 1302.5 / 1.36 / -3.59 | 1241.8 / -0.10 / -15.00 | 44265/47251 (93.7%), 9/109 clusters | gamma 8->7, neutron 1->2, pi+ 0->2 |
| 11 | r18345 s1 e259542 | 1378.8 / 0.38 / -15.00 | 1437.9 / -0.42 / -15.00 | 1378.8 / 0.38 / -15.00 | 45089/45089 (100.0%), 6/128 clusters | e- 7->11, gamma 5->11, mu- 4->1, neutron 2->4, pi+ 1->0, pi0 1->2, proton 0->3 |
| 12 | r18261 s1 e285567 | 1631.5 / 0.79 / -7.23 | 2169.1 / 0.83 / -3.94 | 1631.5 / 0.79 / -7.23 | 75614/75614 (100.0%), 8/119 clusters | e- 5->8, gamma 5->7, mu- 3->2, pi+ 3->1, pi0 1->2, proton 6->4 |
| 13 | r18255 s1 e314838 | 1092.6 / -0.06 / -15.00 | 1090.0 / -0.22 / -15.00 | 1092.6 / -0.06 / -15.00 | 56185/56185 (100.0%), 2/116 clusters | e- 4->3, gamma 4->3, mu- 0->1, pi0 1->0, proton 2->1 |
| 14 | r18255 s1 e359980 | 693.2 / -1.11 / -15.00 | 868.1 / -0.63 / -15.00 | 693.2 / -1.11 / -15.00 | 34221/34227 (100.0%), 6/74 clusters | e- 7->2, gamma 7->2, pi+ 1->0, proton 0->1 |
| 15 | r18255 s1 e399860 | 1164.6 / -0.89 / 9.00 | 978.2 / -0.47 / 1.09 | 1164.6 / -0.89 / 9.00 | 24203/24203 (100.0%), 19/72 clusters | proton 2->0 |
| 16 | r18255 s1 e463565 | 1266.1 / -0.03 / -1.69 | 1481.0 / -0.04 / -15.00 | 1266.1 / -0.03 / -1.69 | 25581/25581 (100.0%), 13/110 clusters | gamma 2->5, pi+ 1->2, pi0 0->1, proton 3->5 |
| 17 | r18255 s1 e506114 | 2247.2 / -0.92 / -15.00 | 2158.7 / -1.01 / -15.00 | 2247.2 / -0.92 / -15.00 | 40172/40172 (100.0%), 6/92 clusters | e- 6->5, gamma 6->5 |
| 18 | r18255 s1 e506746 | 1728.4 / 0.58 / -15.00 | 2140.9 / 0.38 / -15.00 | 1728.4 / 0.58 / -15.00 | 28521/28521 (100.0%), 10/73 clusters | e- 5->8, gamma 4->7, mu- 2->1, pi+ 2->1, proton 2->3 |
| 19 | r18255 s1 e521075 | 491.4 / -0.42 / -15.00 | 840.1 / -0.14 / -15.00 | 491.4 / -0.42 / -15.00 | 30994/31000 (100.0%), 5/87 clusters | e- 0->1, gamma 0->1, mu- 1->0, neutron 1->0 |

**`tracking-pr.root`, every branch at exact float (compare job 8876739 + `evt-branch-diff.py`, `production-prep/r3-ncpi0-vs-m0925/cmp-xin/`):** deep_compare exact **0/19**; census 1141 differing (tree, branch) pairs (the hit-flash re-run: 11, all in `T_rec_charge` at <= 1.4e-9). In **every** event `T_cluster` moves in `flash_id`, `flash_time_us`, `flash_pe`, `beam_flash`, `cluster_t0_us`, `npoints`, `length_cm`, `lm` (and `fc` 17, `in_scope` 18, `is_main`/`is_associated` 16, `tgm` 5 events), i.e. a different flash match and a different clustering; the T_kine energies and both BDT scores then move in every event. Caveat: r3's files have 8 trees and the older branch set, so only branches present in both are compared (the two trees and the provenance/record branches added since 09-08 are not in r3).

| # | event | T_rec_charge points Xin / r3 | differing branches: Trun / T_cluster / T_kine / T_tagger | headline (Xin -> r3) |
|---|---|---|---|---|
| 1 | r18259 s1 e18625 | 822 / 836 | 0 / 13 / 29 / 208 | kine_reco_Enu 1502.46 -> 1448.63; kine_pio_mass 23.4334 -> 25.9634; numu_score 0.586107 -> 2.79614 |
| 2 | r18345 s1 e21073 | 783 / 867 | 0 / 12 / 24 / 767 | kine_reco_Enu 1400.54 -> 1623.74; kine_pio_mass 148.525 -> 262.028; numu_score 0.562491 -> -0.696057; nue_score -7.35753 -> -2.49969 |
| 3 | r18259 s1 e37112 | 427 / 489 | 0 / 9 / 24 / 758 | kine_reco_Enu 1119.46 -> 1147.83; kine_pio_mass 301.398 -> 290.687; numu_score 0.639571 -> -0.613598; nue_score -2.74542 -> -2.6173 |
| 4 | r18255 s1 e56982 | 658 / 615 | 0 / 13 / 24 / 768 | kine_reco_Enu 1109.61 -> 1268.54; kine_pio_mass 141.941 -> 139.262; numu_score 0.229661 -> 0.065657; nue_score 2.82538 -> -4.8177 |
| 5 | r18255 s1 e71372 | 1458 / 1465 | 0 / 11 / 29 / 223 | kine_reco_Enu 2290.48 -> 2422.85; kine_pio_mass 327.904 -> 193.613; numu_score 1.80398 -> 1.71327 |
| 6 | r18364 s1 e84229 | 806 / 807 | 0 / 12 / 29 / 437 | kine_reco_Enu 1305.17 -> 1492.2; kine_pio_mass 177.126 -> 205.409; numu_score 0.500061 -> 0.61676 |
| 7 | r18259 s1 e105946 | 491 / 516 | 0 / 12 / 25 / 211 | kine_reco_Enu 1098.61 -> 923.223; kine_pio_mass 89.5652 -> 35.4754; numu_score -0.228942 -> -0.15193 |
| 8 | r18255 s1 e114446 | 519 / 42 | 0 / 13 / 24 / 220 | kine_reco_Enu 753.023 -> 125.77; kine_pio_mass 23.7483 -> 5.41556; numu_score -0.636342 -> -2.73984 |
| 9 | r18255 s1 e142421 | 1238 / 1353 | 0 / 11 / 31 / 229 | kine_reco_Enu 2110.66 -> 2678.34; kine_pio_mass 465.09 -> 137.29; numu_score 2.69402 -> 3.05041 |
| 10 | r18255 s1 e180801 | 628 / 625 | 0 / 13 / 24 / 806 | kine_reco_Enu 1241.82 -> 1302.47; kine_pio_mass 180.357 -> 114.077; numu_score -0.105212 -> 1.35915; nue_score -15 -> -3.59036 |
| 11 | r18345 s1 e259542 | 861 / 774 | 0 / 12 / 27 / 452 | kine_reco_Enu 1378.78 -> 1437.92; kine_pio_mass 26.0113 -> 275.195; numu_score 0.376181 -> -0.425498 |
| 12 | r18261 s1 e285567 | 824 / 811 | 0 / 12 / 31 / 881 | kine_reco_Enu 1631.48 -> 2169.07; kine_pio_mass 120.792 -> 198.423; numu_score 0.790748 -> 0.82979; nue_score -7.23398 -> -3.93641 |
| 13 | r18255 s1 e314838 | 644 / 654 | 0 / 10 / 21 / 178 | kine_reco_Enu 1092.56 -> 1089.98; kine_pio_mass 170.216 -> 171.002; numu_score -0.0639492 -> -0.221284 |
| 14 | r18255 s1 e359980 | 463 / 463 | 0 / 10 / 25 / 312 | kine_reco_Enu 693.191 -> 868.141; kine_pio_mass 335.335 -> 138.498; numu_score -1.10875 -> -0.628827 |
| 15 | r18255 s1 e399860 | 574 / 612 | 0 / 12 / 23 / 809 | kine_reco_Enu 1164.55 -> 978.165; kine_pio_mass 73.585 -> 13.9795; numu_score -0.891174 -> -0.467035; nue_score 8.99561 -> 1.09321 |
| 16 | r18255 s1 e463565 | 719 / 683 | 0 / 12 / 27 / 831 | kine_reco_Enu 1266.11 -> 1480.97; kine_pio_mass 61.7973 -> 128.426; numu_score -0.0318436 -> -0.0347881; nue_score -1.69123 -> -15 |
| 17 | r18255 s1 e506114 | 915 / 990 | 0 / 12 / 22 / 160 | kine_reco_Enu 2247.2 -> 2158.73; kine_pio_mass 166.413 -> 212.764; numu_score -0.91853 -> -1.01167 |
| 18 | r18255 s1 e506746 | 790 / 916 | 0 / 12 / 31 / 419 | kine_reco_Enu 1728.4 -> 2140.94; kine_pio_mass 181.661 -> 144.741; numu_score 0.579856 -> 0.376745 |
| 19 | r18255 s1 e521075 | 261 / 269 | 0 / 13 / 24 / 192 | kine_reco_Enu 491.372 -> 840.144; kine_pio_mass 3.00622 -> 78.9452; numu_score -0.42232 -> -0.141461 |
