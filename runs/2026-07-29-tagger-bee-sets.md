# Run: STM/TGM/FC tagger BEE sets — 2026-07-29

Validation of issue #2 (`tagger_stm` / `tagger_tgm` / `tagger_fc` in
`wclsTensorSetLabeler`). The tagger PR pass runs between the all-APA MABC and
the labeler (`run_taggers=true`), so the labeler reads the `flag_STM/TGM/FC`
cluster flags and emits one tagged/not-tagged BEE set per tagger.

Work area: `/exp/sbnd/app/users/yuhw/wcp-porting-img/sbnd/TensorSetLabeler/tagger_bee/`

## Env / commands (SL7 + `setup-ap.sh`)
```bash
export FHICL_FILE_PATH=/exp/sbnd/app/users/yuhw/wcp-porting-img/sbnd:$FHICL_FILE_PATH
# MC smoke (1 evt):
lar -n 1 -c wcls-img-clus-matching-xin.fcl \
    -s .../round1-qlmatch/gen_g4_detsim_reco1-a0e0308f-....root --no-output
# data smoke (evt 269774):
lar -n 1 --nskip 20 -c wcls-img-clus-matching-xin-data.fcl \
    -s .../samples/filtered-reco1/data_..._frameshift.root --no-output
# 10-evt: ONE lar -n 1 --nskip K per event (K=0..9), NOT a single batch job
#         (a multi-event batch SIGSEGVs in the tagger/steiner patrec).
```

## Results

### Smoke
- MC (1 evt): `RC=0`. Tagger verdicts logged (`TGM=false`, `STM=0`, `FC=false`)
  → all three sets present, `cluster_id=0` everywhere (nothing tagged — correct
  for this event; confirms the read path handles absent/false flags as 0).
- Data (evt 269774): `RC=0`. `TaggerCheckFC: cluster 13 → FC=true` →
  `tagger_fc` `cluster_id` = {0: 11859, 1: 9689}; STM/TGM all 0.

### 10 MC + 10 data (per-event, all `RC=0`, no segfaults)
Tagged-point aggregates in the merged sets:

| set | MC | data |
|---|---|---|
| `tagger_stm` | 2545 pts / 1 evt | 0 / 0 |
| `tagger_tgm` | 18973 pts / 2 evt | 14704 pts / 2 evt |
| `tagger_fc`  | 0 / 0 | 38381 pts / 5 evt |

Spot-checks (per-event zips):
- MC evt9: `tagger_stm` {0: 32136, 1: 2545}, tgm/fc all 0 (matches
  `TaggerCheckSTM: cluster 4 → STM=1`).
- data evt1: `tagger_tgm` {0: 78579, 1: 2332}, `tagger_fc` {0: 77365, 1: 3546},
  stm all 0 (matches `TGM: cluster 6 → true`, `FC: cluster 19 → true`).

## Outputs (absolute paths)
- Per-event dirs: `tagger_bee/mc_pe/evt{0..9}/mabc.zip`,
  `tagger_bee/data_pe/evt{0..9}/mabc.zip`
- Merged (BEE-uploaded): `tagger_bee/tagger_mc_10evt.zip` (36 MB),
  `tagger_bee/tagger_data_10evt.zip` (11 MB)
- Batch-crash evidence: `tagger_bee/mc10/lar-mc10.log` (SIGSEGV on 3rd event),
  `tagger_bee/data10/lar-data10.log` (6th event)

Merge = renumber each per-event zip's index dir `0 → K` and combine
(`prefix/K/K-<set>.json`); BEE lists events by the real RSE inside each JSON.

## BEE
- MC (10 evt): https://www.phy.bnl.gov/twister/bee/set/2d09d17e-0696-45da-872b-91b7a7b9340f/event/list/
- data (10 evt): https://www.phy.bnl.gov/twister/bee/set/7937d2e8-5d4a-4f8a-9dda-cab7a2d166fb/event/list/

Related: `issues/2-tagger-bee-sets.md`.
