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
