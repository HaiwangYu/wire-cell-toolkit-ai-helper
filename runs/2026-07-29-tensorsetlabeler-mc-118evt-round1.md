# Run: TensorSetLabeler 1-step chain, MC 118 events (round1 list) — 2026-07-29

> **File names renamed 2026-09-30 (issue 33 cleanup).** `wcls-img-clus-matching-xin-lib.jsonnet` is now `wcls-img-clus-matching-pr-lib.jsonnet`; the 1-step jobs `wcls-img-clus-matching-xin{,-hits}.jsonnet` are now `obsolete/wcls-img-clus-matching-pr-{flash,hits}.jsonnet` (the upstream name `wcls-img-clus-matching-xin.jsonnet` stays as a one-line shim); the fcls `wcls-img-clus-matching-xin{,-data,-hits,-data-hits}.fcl` are now `wcls-img-clus-matching-pr-{flash,flash-data,hits,data-hits}.fcl`. Production is the 2-step chain `wcls-img-clus-matching.jsonnet` + `wct-pr.jsonnet`. The names below are as they were when this work ran.


The full `wcls-img-clus-matching-xin.fcl` (img → clus → joint QLMatching →
`wclsTensorSetLabeler`, MC / `reality=sim`, `run_labeler=true`) 1-step chain run
over all events in the round1 10-file MC list, producing one combined
`mabc.zip` (Bee) + `nugraph.h5` (pynuml). No downstream patrec (tagger/steiner),
so no bulk-crash risk.

## Input
- List (10 files, 118 events total):
  `/exp/sbnd/app/users/yuhw/2025-fall-prod-sample/round1-qlmatch/mc_paths-10files.lst`
  (MCP2025C Fall, `prodgenie_corsika_proton_rockbox0p1_sbnd` CV reco1, pnfs).

## Command (SL7 + `setup-ap.sh`)
```bash
export FHICL_FILE_PATH=/exp/sbnd/app/users/yuhw/wcp-porting-img/sbnd:$FHICL_FILE_PATH
cd /exp/sbnd/app/users/yuhw/wcp-porting-img/sbnd/TensorSetLabeler/nugraph-sample-v3/mc-10evt-round1
lar -c wcls-img-clus-matching-xin.fcl \
    -S /exp/sbnd/app/users/yuhw/2025-fall-prod-sample/round1-qlmatch/mc_paths-10files.lst \
    --no-output
```

## Result
- `FULL_RC=0` (success); wall clock **42:04** for 118 events (~21 s/event).
- **118 records** in both `nugraph.h5` and `mabc.zip`; all events processed.
- No real crashes: 0 SIGSEGV / non-zero-exit; `Art ... will exit with status 0`.
  The per-event labeler warning `nugraph: 'ctpc' graph unavailable ...`
  (`raise<WireCell::ValueError>`) is expected and non-fatal.

## Outputs (absolute paths)
- Work dir: `/exp/sbnd/app/users/yuhw/wcp-porting-img/sbnd/TensorSetLabeler/nugraph-sample-v3/mc-10evt-round1/`
- Bee bundle: `/exp/sbnd/app/users/yuhw/wcp-porting-img/sbnd/TensorSetLabeler/nugraph-sample-v3/mc-10evt-round1/mabc.zip` (473 MB)
- nugraph HDF5: `/exp/sbnd/app/users/yuhw/wcp-porting-img/sbnd/TensorSetLabeler/nugraph-sample-v3/mc-10evt-round1/nugraph.h5` (179 MB)
- lar log: `/exp/sbnd/app/users/yuhw/wcp-porting-img/sbnd/TensorSetLabeler/nugraph-sample-v3/mc-10evt-round1/lar-full.log`

## BEE
https://www.phy.bnl.gov/twister/bee/set/c3130531-5c16-4fe7-9c59-2b98a6acc8b2/event/list/

Related: `issues/1-update-TensorSetLabeler.md` (the labeler changes exercised here).
