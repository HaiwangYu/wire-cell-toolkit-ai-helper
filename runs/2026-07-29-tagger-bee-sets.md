# Run: STM/TGM/FC tagger BEE sets — 2026-07-29

Validation of issue #2 (`tagger_stm` / `tagger_tgm` / `tagger_fc` in
`wclsTensorSetLabeler`). The graph is `MABC → pr(taggers) → labeler → dump`,
assembled in the **entry** jsonnet (`wcls-img-clus-matching-xin.jsonnet`);
`clus.jsonnet` does clustering+matching only.

The tagger sets use **`clustering_global`'s corrected coords** (data
`x_t0cor/y_cor/z_cor`, sim `x_sce/y_sce/z_sce`) and a **4-case `cluster_id`**:
`0` not-main, `1` main out-of-beam-window, `2` main in-window untagged, `3` main
in-window tagged.  (See `issues/2-tagger-bee-sets.md` for how the taggers only
act on beam-window `main_cluster`s.)

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
- MC (1 evt): `RC=0`. Nothing tagged (verdicts `TGM=false/STM=0/FC=false`) →
  `1`=20345 (out-of-window mains), `2`=1818 (in-window candidate, untagged).
- Data (evt 269774): `RC=0`. `TaggerCheckFC: cluster 13 → FC=true` → `tagger_fc`
  `cluster_id` = {1: 11843, 2: 16, 3: 9689}; STM/TGM in-window mains all `2`.
- Coordinate fix confirmed: MC `tagger_fc` x-mean −12.8 tracks `clustering_global`
  −13.0 (corrected scope), vs raw truth sets at −91/−173.

### 10 MC + 10 data (per-event, all `RC=0`, no segfaults)
4-case `cluster_id` aggregate in the merged sets (0 not-main / 1 out-of-window /
2 in-window untagged / 3 in-window tagged):

| set | MC (1/2/3) | data (1/2/3) |
|---|---|---|
| `tagger_stm` | 254013 / 30307 / **2545** | 278702 / 90272 / — |
| `tagger_tgm` | 254013 / 13879 / **18973** | 278702 / 75568 / **14704** |
| `tagger_fc`  | 254013 / 32852 / — | 278702 / 51891 / **38381** |

No code 0 (QLMatching flags every matched cluster a main); the code-1 bucket is
out-of-window cosmic mains, separated from the in-window candidates (2/3).
Fired: STM 1 MC evt; TGM 2 MC + 2 data; FC 5 data.

## Outputs (absolute paths)
- Per-event dirs: `tagger_bee/mc_pe3/evt{0..9}/mabc.zip`,
  `tagger_bee/data_pe3/evt{0..9}/mabc.zip`
- Merged (BEE-uploaded): `tagger_bee/tagger_mc_10evt.zip`,
  `tagger_bee/tagger_data_10evt.zip`
- Batch-crash evidence: `tagger_bee/mc10/lar-mc10.log` (SIGSEGV on 3rd event),
  `tagger_bee/data10/lar-data10.log` (6th event)

Merge = renumber each per-event zip's index dir `0 → K` and combine
(`prefix/K/K-<set>.json`); BEE lists events by the real RSE inside each JSON.

## BEE (full `.../event/list/` URLs)
- MC 1-evt smoke:   https://www.phy.bnl.gov/twister/bee/set/3b6ccf2b-a99a-4795-a031-3cef27bea31d/event/list/
- data 1-evt smoke: https://www.phy.bnl.gov/twister/bee/set/5e4a6fa2-6547-4c2d-af9d-a3a0303eafcc/event/list/
- MC 10-evt:   https://www.phy.bnl.gov/twister/bee/set/32520625-3ffe-4804-8eda-0e72b906f5b7/event/list/
- data 10-evt: https://www.phy.bnl.gov/twister/bee/set/01532c4a-b363-45ab-9374-247da14819b6/event/list/

Related: `issues/2-tagger-bee-sets.md`.
