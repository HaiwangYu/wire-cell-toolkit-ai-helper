# Issue 27: Polaris production of img-clus-match-pr on ~1M SBND reco1 events

Tracking: https://github.com/HaiwangYu/wire-cell-toolkit-ai-helper/issues/27

The plan (survey, measured facts, sizing, open questions, phases) lives in
`docs/polaris-img-clus-match-pr-production-plan.md`; this folder holds the
per-issue record and scripts.

## scripts/
- `compare-to-fnal.sh`, `branch-diff-tracking-pr.py` -- phase-2 comparison + Bee upload (plan doc section 6, step 5).
- `build-wct-lwc.pbs`, `smoke.pbs`, `smoke-1evt.sh`, `in-polaris-sl7.sh`, `setup-polaris-*.sh`, `configure-wct-polaris.sh`, `resync-operating-point-polaris.sh`, `compile-both-polaris.sh` -- the Recipe B build/run/gate chain.
- `probe.pbs` .. `probe4.pbs` -- the four 1-node `debug` probe jobs of
  2026-09-10 (`-A neutrinoGPU::debug`). `probe4.pbs` is the working pattern:
  rsync the cvmfsexec template to `/local/scratch`, mount 5 repos through the
  ALCF proxy, `apptainer exec --userns` the FNAL SL7 image, `setup sbndcode`,
  run `lar`.
- `cvmfs-default.local.compute` / `.login` -- the two `dist/etc/cvmfs/default.local`
  variants (node-local cache on `/local/scratch` vs `/home/yuhw/cvmfs-cache`).

## log
- 2026-09-10: survey + probes 1-4; plan v1 written; issue opened.
- 2026-09-15: Recipe B built (WCT `polaris-build-fixes` 9195180d, larwirecell a02a1a4) in debug jobs; operating-point gate 0 diff; MC smoke 9/9.
- 2026-09-16: Gen2 data nc-sideband 19/19 pass with the data fcl. Compared with FNAL `r3-ncpi0-lynn-2026-09-15` (toolkit 0ad64223): everything identical except 16 nue-BDT `T_tagger` score branches -- `uboone/weights/XGB_nue_seed2_0923.xml` (199 MB) missing on Eagle. Bee: FNAL https://www.phy.bnl.gov/twister/bee/set/a18b25ec-c95d-4206-b3f5-fd10b7d4bdf2/event/list/ , Polaris https://www.phy.bnl.gov/twister/bee/set/bb271eeb-602e-488b-a6bd-dc4925cbe2ed/event/list/ . Procedure written up in the plan doc section 6.
- 2026-09-16 (later): with `XGB_nue_seed2_0923.xml` copied from FNAL, rerun `ncsb-data-nuebdt-20260916-0446` is EXACT 19/19 vs FNAL (every-branch census: 0 differing pairs). Polaris Bee https://www.phy.bnl.gov/twister/bee/set/9e2378ce-e6ce-4ea8-92da-3abda3186cc9/event/list/ . Plan doc sec 8 answers the job-submission questions (qsub, allocation, wait times, node availability, filesystems, monitoring).
