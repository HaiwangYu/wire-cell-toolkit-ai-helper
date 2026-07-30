# Run: STM/TGM/FC tagger BEE sets — 2026-07-29

Validation of issue #2 (`tagger_stm` / `tagger_tgm` / `tagger_fc` in
`wclsTensorSetLabeler`). The graph is `MABC → pr(taggers) → labeler → dump`,
assembled in the **entry** jsonnet (`wcls-img-clus-matching-xin.jsonnet`);
`clus.jsonnet` does clustering+matching only.

The tagger sets use **`clustering_global`'s corrected coords** (data
`x_t0cor/y_cor/z_cor`, sim `x_sce/y_sce/z_sce`) and contain **only the beam-window
candidates** (`main_cluster` with `cluster_t0 ∈ [0.2,2.2) µs`), colored `0` not
tagged / `1` tagged.  Out-of-window mains and non-main clusters are dropped.
(See `issues/2-tagger-bee-sets.md` for how the taggers only act on beam-window
`main_cluster`s.)

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
- MC (1 evt): `RC=0`. Candidate-only: tagger sets 1818 pts (vs 22009 in
  `clustering-global`), all `cluster_id=0` (nothing tagged this event).
- Data (evt 269774): `RC=0`. `TaggerCheckFC: cluster 13 → FC=true` → `tagger_fc`
  = {0: 16, 1: 9689} (9705 candidate pts); STM/TGM all `0`.
- Coordinate fix confirmed: MC `tagger_fc` x-mean −12.8 tracks `clustering_global`
  −13.0 (corrected scope), vs raw truth sets at −91/−173.

### 10 MC + 10 data (per-event, all `RC=0`, no segfaults)
Candidate-only `cluster_id` aggregate in the merged sets (0 not tagged / 1 tagged;
per-set total = the candidate-point count, identical across the three taggers):

| set | MC (0/1) | data (0/1) |
|---|---|---|
| `tagger_stm` | 30307 / **2545** | 90272 / — |
| `tagger_tgm` | 13879 / **18973** | 75568 / **14704** |
| `tagger_fc`  | 32852 / — | 51891 / **38381** |

Out-of-window mains and non-main clusters are omitted, so each set is just the
beam-window candidates. Fired: STM 1 MC evt; TGM 2 MC + 2 data; FC 5 data.

### All 48 data events (2026-07-30, per-event, all `RC=0`)
The full evt-269774 data file (`Events` = 48), one `lar -n 1 --nskip K` per event
(K=0..47), two parallel worker loops. Candidate-only 0/1 aggregate:

| set | data 48-evt (0/1) | tagged in |
|---|---|---|
| `tagger_stm` | 421465 / — | 0/48 |
| `tagger_tgm` | 378688 / **42777** | 5/48 |
| `tagger_fc`  | 228115 / **193350** | 22/48 |

Two events needed a retry (both then clean, `RC=0`):
- **evt29** hung in *imaging* (`MaskSlice`, before clustering) for >10 min — a
  data-dependent imaging hang, not the tagger. Killed and retried under
  `timeout 300`; completed in < 5 min.
- **evt30** crashed on HDF5 finalize (`truncate ... Disk quota exceeded`,
  errno 122) because the `yuhw` cephfs quota (60 GiB) filled mid-run; events
  31–47 then failed to write. Freed space (removed superseded intermediate run
  dirs + per-event `nugraph.h5`/`trash-all-apa.tar.gz`) and re-ran 29–47.

## Outputs (absolute paths)
- 10-evt per-event dirs: `tagger_bee/mc_pe4/evt{0..9}/mabc.zip`,
  `tagger_bee/data_pe4/evt{0..9}/mabc.zip`
- 48-evt data per-event dirs: `tagger_bee/data_48/evt{0..47}/mabc.zip`
- Merged (BEE-uploaded): `tagger_bee/tagger_mc_10evt.zip`,
  `tagger_bee/tagger_data_10evt.zip`, `tagger_bee/tagger_data_48evt.zip`

Merge = renumber each per-event zip's index dir `0 → K` and combine
(`prefix/K/K-<set>.json`); BEE lists events by the real RSE inside each JSON.

## BEE (full `.../event/list/` URLs, candidate-only 0/1)
- MC 10-evt:     https://www.phy.bnl.gov/twister/bee/set/169bdddf-0f71-44ab-aab1-47a896316040/event/list/
- data 10-evt:   https://www.phy.bnl.gov/twister/bee/set/98263fdf-53ac-491d-84cf-c4dca3522606/event/list/
- data 48-evt:   https://www.phy.bnl.gov/twister/bee/set/7d081fbf-b08f-4dbd-9c47-cd73a7c98472/event/list/

Related: `issues/2-tagger-bee-sets.md`.
