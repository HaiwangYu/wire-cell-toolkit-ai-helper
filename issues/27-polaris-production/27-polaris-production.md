# Issue 27: Polaris production of img-clus-match-pr on ~1M SBND reco1 events

Tracking: https://github.com/HaiwangYu/wire-cell-toolkit-ai-helper/issues/27

The plan (survey, measured facts, sizing, open questions, phases) lives in
`docs/polaris-img-clus-match-pr-production-plan.md`; this folder holds the
per-issue record and scripts.

## scripts/
- `probe.pbs` .. `probe4.pbs` -- the four 1-node `debug` probe jobs of
  2026-09-10 (`-A neutrinoGPU::debug`). `probe4.pbs` is the working pattern:
  rsync the cvmfsexec template to `/local/scratch`, mount 5 repos through the
  ALCF proxy, `apptainer exec --userns` the FNAL SL7 image, `setup sbndcode`,
  run `lar`.
- `cvmfs-default.local.compute` / `.login` -- the two `dist/etc/cvmfs/default.local`
  variants (node-local cache on `/local/scratch` vs `/home/yuhw/cvmfs-cache`).

## log
- 2026-09-10: survey + probes 1-4; plan v1 written; issue opened.
