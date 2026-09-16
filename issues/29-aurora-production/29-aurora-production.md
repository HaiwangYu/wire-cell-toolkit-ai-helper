# Issue 29: Aurora production of img-clus-match-pr (port of issue 27)

Tracking: https://github.com/HaiwangYu/wire-cell-toolkit-ai-helper/issues/29
Plan: `docs/aurora-img-clus-match-pr-production-plan.md` (v2, 2026-09-16).

## scripts/
- `probe-aurora.pbs` -- phase A1 probe (node facts, `/tmp`, cgroup, userns/fuse, proxy, apptainer
  modes, Recipe A' via twester's Flare UPS tree incl. an `eventdump.fcl` of a Gen2 reco1 file with
  the product check, Recipe B via cvmfsexec + fnal-dev-sl7, and a one-time `apptainer pull` of the
  dev image into `$Y/images/`). Submit from a UAN: `cd $Y/aurora-build-logs && qsub $S/probe-aurora.pbs`
  (`-A neutrinoGPU::debug2 -q debug -l filesystems=flare:home`, 30 min). Everything it needs is on Flare.

## log
- 2026-09-16 (a): plan v1 written from ALCF docs + sbank + colleagues' Aurora tooling (nothing run on Aurora yet); issue opened.
- 2026-09-16 (b): **plan v2 = review of v1 from `aurora-uan-0010`** (section 0 of the plan lists the corrections).
  Measured: no cgroup limits and direct internet on the UAN, but `user.max_user_namespaces=0` and a
  non-setuid apptainer 1.2.5 -> no containers/cvmfsexec on login nodes; Eagle not mounted; project quota
  3.045/3.2 PB (95 %), 223 M files; unrestricted suballocation **17257 = 28,262 node-hours** (+ `debug2` 472);
  queues via `qstat -Qf` (`debug-scaling` takes 1-256 nodes, `capacity` 1-16 nodes/7 d); twester's Flare UPS
  tree has **sbndcode v10_14_02_03 / larsoft v10_14_02_02** and is launched with plain `apptainer -B /lus/flare
  slf7.sif` (no overlays) -> Recipe A' is the primary recipe; spdlog v1_14_1 + fmt v11_0_2 are on scisoft,
  patchelf and scn are not. **Gen2 reco1 (Q4)**: MC `prodgenie_corsika_proton_rockbox0p1_sbnd`, sbndcode
  v10_14_02_03, 3 productions x ~250k files, 13.24 events/file, 28.4 MB/event (~3.3 M events and ~94 TB
  each); reco1 keeps `simtpc2d:dnnsp` wires (drops gauss/wiener) -> MC fcl. 1M events = prod1
  `reco1/000000-000075`.
  Done on Flare (`$Y=/lus/flare/projects/neutrinoGPU/yuhw`): cloned WCT `polaris-build-fixes` `9195180d`,
  larwirecell `dev-v10_14_02_02` `a02a1a4`, wcp-porting-validation `main`, wire-cell-data `master`
  (still lacks `XGB_nue_seed2_0923.xml`), this repo, cvmfsexec v4.53 (`makedist -m rhel8-x86_64 osg`);
  `$Y/aurora-build-logs`; `gh` 2.101 in `~/bin` (unauthenticated). `probe-aurora.pbs` revised, not yet submitted.
- 2026-09-16 (c): **probe runs 1-2 (jobs 8832255, 8832311, `debug`, node exclusive to us)**: Xeon Max 9470C, 208 threads (affinity 1-51,53-103,105-155,157-207), 1.1 TB, `/tmp` = 504 GB RAM tmpfs (no NVMe, no `/local/scratch`), no cgroup limits, `max_user_namespaces` 4.1 M, `unshare -U -r` ok, `/dev/fuse` present; proxy reaches GitHub, the CVMFS stratum-1, scisoft and DockerHub. `module load apptainer` (1.2.5) works in batch **only if not piped** (a `| tail` runs the module function in a subshell -> "apptainer: command not found", run 1). `slf7.sif` runs in all three modes (no flag, `--fakeroot`, `--userns`). **Recipe A' bare tree**: `source .../scisoft/larsoft/setup; setup sbndcode v10_14_02_03 -q e26:prof` -> `lar` = art 3.14.04 in 5 s, `eventdump.fcl` on a Gen2 reco1 file rc=0 in 32 s (`simtpc2d` badmasks/wienersummary, `ionandscint:priorSCE` SEDs, MCTruth/MCParticle seen; wires/OpFlash cut off by `head -40`, recheck in the smoke). `slf7.sif` has no `bzlib.h` (40 -devel rpms) -> builds use `$Y/images/fnal-dev-sl7.sif` (pulled from DockerHub through the proxy in 42 s, 548 MB). **Recipe B**: cvmfsexec mounts sbnd/larsoft/fermilab/singularity/uboone through the proxy (`sbn.opensciencegrid.org` was not mounted so `setup_sbnd.sh` failed -- irrelevant now); cache 376 MB. **scn v01_00_00 copied** from uboone CVMFS to `$Y/products/scn` (5.2 GB, 9 min). `$Y/products` overlay now: spdlog v1_14_1, fmt v11_0_2, srproxy v00.44 (py3915; missing from the tree and required by the sbndcode chain on the UAN), scn, `.upsfiles`; `$Y/tools/bin/patchelf` 0.14.5 static.
  **Build runs 1-3 failed before configure**: run 1 the overlay lacked `.upsfiles` (ups rejected PRODUCTS, system gcc 4.8); runs 2-3 gcc 12.1 + spdlog/fmt from the overlay are active but root/python are not (system python 3.6 -> `wscript` f-string `SyntaxError`), although the same `setup-aurora-opt.sh` sequence completes on the UAN (135 products, python 3.9). Run 4 (8832360) prints the setup stderr inside the container to find out why.
- 2026-09-16 (d): **build run 4** found the remaining setup fault by printing the container's setup stderr: `unsetup wirecell` (no `-j`) also unsetups root/python/boost -> `unsetup -j` (reproduced and fixed on the UAN in an `env -i` shell); then `wscript` needed `git describe --tags` (fork clone has no tags -> `git fetch upstream --tags`). **Build run 5 (8832376, debug-scaling, 6.6 min): WCT `polaris-build-fixes` 9195180d installed to `$Y/opt`, all §1 gates pass** -- configure 2m15 (spdlog v1_14_1 + fmt v11_0_2 lib64 from the overlay), `wcb install -j96` 3m26, `nlibs=19` incl. Mcs, `single_threaded_syms=0`, `fmt_needed=0`, RUNPATH spdlog/v1_14_1, `rpath_stripped=20`, `ldd_not_found=0`, `miniz.h` copied. larwirecell stage failed: `mrb newDev` needs `MRB_PROJECT=larsoft` (set by `setup_sbnd.sh` at FNAL, not by the bare tree setup) -> exported in `setup-aurora-opt.sh`; rerun as `qsub -v STAGES=lwc` (8832409).
- 2026-09-16 (e): **larwirecell built (8832409, 4.1 min)**: MRB area `$Y/larsoft-wct/v10_14_02` (`mrb newDev -v v10_14_02_02 -q e26:prof`, `srcs/larwirecell` = local clone of `dev-v10_14_02_02` a02a1a4); `mrbSetEnv` prints the sbnobj version-conflict error as on Polaris (fallback path), cmake configure 125 s, `mrb b -j96` rc=0; `WireCell_INCLUDE_DIR` = `$Y/opt/include`, `spdlog_DIR` = overlay v1_14_1, found WireCell "polaris-build-fixes-0.35.0-1623-g9195180"; **11 libs + 20 fcl deployed** to `$Y/opt/larwirecell/v10_01_28/slf7.x86_64.e26.prof/`, `tree_wirecell_refs=0`. Phase A2 done. Smoke (8832456, `smoke.pbs`, Gen2 MC reco1 file, MC fcl, 8 events, resync on) submitted; the 19-event data set, the FNAL/Polaris reference runs and `XGB_nue_seed2_0923.xml` are still not on Flare.
