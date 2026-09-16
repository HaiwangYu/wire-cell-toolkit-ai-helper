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
