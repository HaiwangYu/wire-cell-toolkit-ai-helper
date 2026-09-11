# Round-3 output size breakdown — what the bytes are, per species

Companion to the [data guide](sbnd-r3-data-guide.md) and [#26](https://github.com/HaiwangYu/wire-cell-toolkit-ai-helper/issues/26). Measured 2026-09-11 over **every** output file of the four samples (42,093 Bee zips + 42,093 `tracking-pr.root`): zip central directories (compressed and uncompressed size per JSON layer) and ROOT `TTree::GetZipBytes/GetTotBytes` per tree. Script: `issues/26-r3-four-sample-campaign/scripts/size-breakdown.py` (+ `make-report.py`); raw JSON in `production-prep/r3-size-breakdown/`.

## 0. Headline

| | MC BNB CV | MC nueCC | beam-on | beam-off |
|---|---|---|---|---|
| events | 13,216 | 8,877 | 10,000 | 10,000 |
| **`run/` total** | **77.6 GB** | **63.6 GB** | **15.1 GB** | **14.0 GB** |
| Bee zips | 71.5 GB (92 %) | 56.0 GB (88 %) | 10.2 GB (68 %) | 10.5 GB (75 %) |
| `tracking-pr.root` | 1.77 GB (2 %) | 2.69 GB (4 %) | 1.32 GB (9 %) | 0.36 GB (3 %) |
| per-event lar logs | 4.26 GB (5 %) | 4.92 GB (8 %) | 3.50 GB (23 %) | 3.20 GB (23 %) |
| **deliverables per event** (bee + root) | **5.5 MB** | **6.6 MB** | **1.16 MB** | **1.08 MB** |
| of which Bee | 5.41 MB | 6.31 MB | 1.02 MB | 1.05 MB |
| of which root | 134 kB | 304 kB | 132 kB | 36 kB |
| root per *candidate* file | 274 kB | 321 kB | 291 kB | 424 kB |
| root per non-candidate file | 12 kB | 12 kB | 8 kB | 8 kB |

Four facts explain almost everything below:

1. **MC Bee is 79 % truth energy-deposit layers, stored three times.** `sed-smear_readout`, `sed-sce_smear_readout`, `sed-sce_drift_smear_readout` are 1.42 MB/event *each* (4.3 MB of the 5.4 MB per MC event). Data has none of them, which is the whole MC-vs-data size gap.
2. **The reco point cloud is written three times in every Bee zip**: `img-global`, `clustering-global`, `clustering-pr-global` are the same points (same size to within 1 %) at 235–250 kB/event each — 72 % of a data event's Bee, and another 13 % of an MC event's.
3. **`T_tagger` is 44 % of a candidate `tracking-pr.root` and does not compress** (1.0×): 1,229 branches × 1 entry, so per-branch basket overhead (~100 B) dominates the ~120 kB. `T_proj_data` (34 kB) and `T_rec_charge` (23 kB) are the physics payload.
4. **Per-event lar logs are 330–550 kB each** (2,600 lines, mostly DEBUG-level WCT node chatter) and **gzip 9:1**. On data they are a quarter of the disk.

## 1. Other large files not in the deliverables

| what | where | size | note |
|---|---|---|---|
| per-event lar logs | `<sample>/run/logs/missing_<idx>_r*_s*_e*.log` | 3.2–4.9 GB per sample, **351 kB/event mean** (p50 328, p99 702, max 13 MB) | `[HH:MM:SS.mmm] D [main/img/match/clus]` debug lines, `TICK`/`MEM` tables. gzip → 37 kB. Loglevel is `debug` in the fcl (`loglevels: ["debug"]`); `info` would cut these ~5×. |
| retry duplicates | `r3-mc-cv-2026-09-09/run-retry/{bee,tracking-pr}` | **6.1 GB** | the 1,087 Kerberos re-runs; already copied into `run/`, so `run-retry/` is a pure duplicate — deletable. |
| staged frameshifted data inputs | `r3-data-stage-2026-09-09/{beam-on,beam-off}/chunk*.root` | **86 GB** (43 + 43) | 22 × ~3.9 GB merged reco1 chunks the data manifests point at. Owner decision. |
| step-4b 2-step check | `r3-beam-off-2026-09-11/step4b/` | 2.3 GB | reader frames + pctrees for 8 groups — deletable after the issue is closed. |
| pilots / crash reproducer | `r3-pilot-mccv/`, `r3-pilot-nuecc/`, `r3-crash-471-18-33/`, `r3-data-stage-*/spot-*` | 0.6 + 0.4 + 0.2 + 0.6 GB | keep the crash reproducer (§5a of #26). |
| Bee upload bundles | `<sample>/bee-upload/*.zip` | 11–53 MB per sample | already on the Bee server. |
| `summary*.csv`, lists, records | | < 10 MB total | keep. |

`work/` is empty in every sample (the harness cleans per-event work dirs) and `nugraph/` is empty (switched off this round; it was ~1.2 MB/event in #16).

## 2. Comparison with the official CAF / flatCAF of the same samples

SAM definition summaries (total size / events) and one file per definition opened for its trees (`recTree` carries the event; `globalTree` ~1.4 MB per file is MC-only). CAF per-event is **the whole reconstruction summary** — comparable in role to our `tracking-pr.root`, not to Bee (which is a display product).

| species | CAF definition | per event | flatCAF per event | our `tracking-pr.root` per candidate | our Bee per event |
|---|---|---|---|---|---|
| MC BNB CV | `aurora_…_CV_v10_14_02_03_flatcaf_sbnd` (7.86 TB / 9.94 M ev; no plain-caf def) | — | **791 kB** | 274 kB | 5,412 kB |
| MC nueCC | `aurora_…_EX_nuecc_v10_14_02_05_flat_caf_sbnd` (117 GB / 117,809 ev) | — | **995 kB** | 321 kB | 6,306 kB |
| beam-on (FixedDev) | `…FixedDev_Respin_v10_14_02_04_caf_sbnd` (15.0 GB / 1,817 files ≈ 90.8 k ev) | **~165 kB** (one file: 8.47 MB / 50) | ~204 kB (18.5 GB) | 291 kB | 1,024 kB |
| beam-off (InTime) | `data_SBND2026A_gen2_InTime-Run1_v10_14_02_02_caf_sbnd` (271 GB / 49,020 files) | **~170 kB per recTree entry** — but see note | ~150 kB nominal | 424 kB | 1,048 kB |

Notes.
- MC CAFs are 3–4× larger per event than data CAFs because they carry truth (`GenieEvtRecTree`, `globalTree`, MC particle blocks) — the same reason our MC Bee is 5× the data Bee.
- **The InTime off-beam CAF files are almost empty**: the three files opened had 0, 3 and 0 `recTree` entries against 50 reco1 events per file, and the definition's 271 GB / 49,020 files = 5.5 MB/file average hides a very wide spread. So the reco1 definition we ran on is the *unfiltered* off-beam-light stream, and the CAF stage applied an event filter (presumably the "InTime" light selection) that keeps a small fraction. The SAM "Event count: 2,233,625" on the CAF definition is inherited metadata, not the recTree count. **Joining our beam-off output to its CAF will therefore match only the filtered subset** — worth checking before any comparison (open item in #28).
- Per candidate event our ROOT summary (274–424 kB) is 1.5–2.5× a data CAF event, essentially all of it the uncompressed `T_tagger` (121 kB) and `T_proj_data` (34 kB); the CAF's `recTree` compresses 2–2.5×.

## 3. What would shrink it (not done — for discussion)

| change | saves | risk |
|---|---|---|
| write one `sed-*` layer instead of three (or none in production) | **−4.3 MB/event on MC, −79 % of MC Bee** (≈ −57 GB on CV, −40 GB on nueCC) | truth-display only; no reconstruction impact |
| drop `img-global` and/or `clustering-global` when `clustering-pr-global` is written (same points, PR labels are a superset) | −0.5 MB/event everywhere (−45 % of data Bee) | Bee shows fewer intermediate stages |
| lar `loglevels: ["info"]` or gzip logs after the run | −3 to −5 GB per sample (−23 % of data disk) | debug lines lost / one extra step |
| `T_tagger` in one branch or with baskets merged (`SetAutoFlush`/`OptimizeBaskets`) | −~100 kB per candidate | downstream readers expect the flat 1,229-branch layout |
| delete `run-retry/` and `step4b/` now | −8.4 GB | none |

---

# Full tables (generated)
## A. Where the bytes are, per sample (run/ directory)

| sample | events | total | `bee/` | `tracking-pr/` | `logs/` | other | **per event** (bee + root) |
|---|---|---|---|---|---|---|---|
| MC BNB CV | 13,216 | **77.6 GB** | 71.5 GB (92 %) | 1.77 GB (2 %) | 4.26 GB (5 %) | 6 MB | **5,546 kB** (bee 5,412, root 134) |
| MC nueCC | 8,877 | **63.6 GB** | 56.0 GB (88 %) | 2.69 GB (4 %) | 4.92 GB (8 %) | 2 MB | **6,609 kB** (bee 6,306, root 304) |
| beam-on | 10,000 | **15.1 GB** | 10.2 GB (68 %) | 1.32 GB (9 %) | 3.50 GB (23 %) | 1 MB | **1,156 kB** (bee 1,024, root 132) |
| beam-off | 10,000 | **14.0 GB** | 10.5 GB (75 %) | 0.36 GB (3 %) | 3.20 GB (23 %) | 1 MB | **1,084 kB** (bee 1,048, root 36) |

## B. Bee zip — per JSON layer, summed over every event (compressed = on disk; ratio = uncompressed/compressed)


### MC BNB CV — 13,216 zips, 71.5 GB, 5,412 kB/event

| layer | in N events | compressed total | per event (all) | per event (when present) | share | uncompressed total | ratio |
|---|---|---|---|---|---|---|---|
| `sed-sce_drift_smear_readout.json` | 13,216 | 18,852 MB | 1,426.5 kB | 1,426.5 kB | 26.4 % | 72,619 MB | 3.9× |
| `sed-smear_readout.json` | 13,216 | 18,829 MB | 1,424.7 kB | 1,424.7 kB | 26.3 % | 72,613 MB | 3.9× |
| `sed-sce_smear_readout.json` | 13,216 | 18,828 MB | 1,424.6 kB | 1,424.6 kB | 26.3 % | 72,612 MB | 3.9× |
| `img-global.json` | 13,216 | 3,094 MB | 234.1 kB | 234.1 kB | 4.3 % | 13,480 MB | 4.4× |
| `clustering-global.json` | 13,216 | 3,094 MB | 234.1 kB | 234.1 kB | 4.3 % | 16,602 MB | 5.4× |
| `clustering-pr-global.json` | 13,216 | 3,078 MB | 232.9 kB | 232.9 kB | 4.3 % | 13,508 MB | 4.4× |
| `truth_trackid_labeled.json` | 13,216 | 1,710 MB | 129.4 kB | 129.4 kB | 2.4 % | 15,917 MB | 9.3× |
| `clustering-apa0-face0.json` | 13,211 | 1,569 MB | 118.7 kB | 118.8 kB | 2.2 % | 6,739 MB | 4.3× |
| `clustering-apa1-face0.json` | 13,213 | 1,542 MB | 116.7 kB | 116.7 kB | 2.2 % | 6,468 MB | 4.2× |
| `truth_unlabeled.json` | 13,216 | 282 MB | 21.3 kB | 21.3 kB | 0.4 % | 1,652 MB | 5.9× |
| `op.json` | 13,216 | 177 MB | 13.4 kB | 13.4 kB | 0.2 % | 1,020 MB | 5.8× |
| `tagger_stm.json` | 13,216 | 77 MB | 5.9 kB | 5.9 kB | 0.1 % | 567 MB | 7.3× |
| `tagger_tgm.json` | 13,216 | 77 MB | 5.9 kB | 5.9 kB | 0.1 % | 567 MB | 7.3× |
| `tagger_fc.json` | 13,216 | 77 MB | 5.9 kB | 5.9 kB | 0.1 % | 567 MB | 7.3× |
| `tagger_lm.json` | 13,216 | 77 MB | 5.9 kB | 5.9 kB | 0.1 % | 567 MB | 7.3× |
| `shower_track-global.json` | 6,018 | 54 MB | 4.1 kB | 8.9 kB | 0.1 % | 465 MB | 8.7× |
| `track_fit-global.json` | 6,018 | 27 MB | 2.0 kB | 4.5 kB | 0.0 % | 74 MB | 2.7× |
| `mc.json` | 13,216 | 13 MB | 1.0 kB | 1.0 kB | 0.0 % | 50 MB | 3.8× |
| `channel-deadarea-apa0-face0.json` | 13,216 | 10 MB | 0.7 kB | 0.7 kB | 0.0 % | 22 MB | 2.3× |
| `channel-deadarea-apa1-face0.json` | 13,216 | 9 MB | 0.7 kB | 0.7 kB | 0.0 % | 22 MB | 2.4× |
| `vertices-global.json` | 6,018 | 3 MB | 0.2 kB | 0.5 kB | 0.0 % | 6 MB | 2.0× |

### MC nueCC — 8,877 zips, 56.0 GB, 6,306 kB/event

| layer | in N events | compressed total | per event (all) | per event (when present) | share | uncompressed total | ratio |
|---|---|---|---|---|---|---|---|
| `sed-sce_drift_smear_readout.json` | 8,877 | 14,620 MB | 1,646.9 kB | 1,646.9 kB | 26.1 % | 56,274 MB | 3.8× |
| `sed-smear_readout.json` | 8,877 | 14,605 MB | 1,645.3 kB | 1,645.3 kB | 26.1 % | 56,270 MB | 3.9× |
| `sed-sce_smear_readout.json` | 8,877 | 14,605 MB | 1,645.2 kB | 1,645.2 kB | 26.1 % | 56,269 MB | 3.9× |
| `img-global.json` | 8,877 | 2,395 MB | 269.8 kB | 269.8 kB | 4.3 % | 10,543 MB | 4.4× |
| `clustering-global.json` | 8,877 | 2,392 MB | 269.5 kB | 269.5 kB | 4.3 % | 12,972 MB | 5.4× |
| `clustering-pr-global.json` | 8,877 | 2,382 MB | 268.4 kB | 268.4 kB | 4.3 % | 10,573 MB | 4.4× |
| `truth_trackid_labeled.json` | 8,877 | 1,299 MB | 146.4 kB | 146.4 kB | 2.3 % | 12,283 MB | 9.5× |
| `clustering-apa0-face0.json` | 8,877 | 1,227 MB | 138.2 kB | 138.2 kB | 2.2 % | 5,336 MB | 4.3× |
| `clustering-apa1-face0.json` | 8,876 | 1,179 MB | 132.9 kB | 132.9 kB | 2.1 % | 4,996 MB | 4.2× |
| `truth_unlabeled.json` | 8,877 | 236 MB | 26.6 kB | 26.6 kB | 0.4 % | 1,399 MB | 5.9× |
| `shower_track-global.json` | 8,308 | 162 MB | 18.2 kB | 19.5 kB | 0.3 % | 1,444 MB | 8.9× |
| `tagger_fc.json` | 8,877 | 154 MB | 17.4 kB | 17.4 kB | 0.3 % | 1,204 MB | 7.8× |
| `tagger_tgm.json` | 8,877 | 154 MB | 17.4 kB | 17.4 kB | 0.3 % | 1,204 MB | 7.8× |
| `tagger_stm.json` | 8,877 | 154 MB | 17.4 kB | 17.4 kB | 0.3 % | 1,204 MB | 7.8× |
| `tagger_lm.json` | 8,877 | 154 MB | 17.4 kB | 17.4 kB | 0.3 % | 1,204 MB | 7.8× |
| `op.json` | 8,877 | 122 MB | 13.7 kB | 13.7 kB | 0.2 % | 703 MB | 5.8× |
| `track_fit-global.json` | 8,308 | 69 MB | 7.8 kB | 8.3 kB | 0.1 % | 194 MB | 2.8× |
| `vertices-global.json` | 8,308 | 11 MB | 1.3 kB | 1.4 kB | 0.0 % | 26 MB | 2.3× |
| `mc.json` | 8,877 | 11 MB | 1.2 kB | 1.2 kB | 0.0 % | 43 MB | 3.9× |
| `channel-deadarea-apa0-face0.json` | 8,877 | 7 MB | 0.7 kB | 0.7 kB | 0.0 % | 15 MB | 2.3× |
| `channel-deadarea-apa1-face0.json` | 8,877 | 6 MB | 0.7 kB | 0.7 kB | 0.0 % | 15 MB | 2.4× |

### beam-on — 10,000 zips, 10.2 GB, 1,024 kB/event

| layer | in N events | compressed total | per event (all) | per event (when present) | share | uncompressed total | ratio |
|---|---|---|---|---|---|---|---|
| `img-global.json` | 10,000 | 2,430 MB | 243.0 kB | 243.0 kB | 23.7 % | 10,645 MB | 4.4× |
| `clustering-global.json` | 10,000 | 2,429 MB | 242.9 kB | 242.9 kB | 23.7 % | 13,130 MB | 5.4× |
| `clustering-pr-global.json` | 10,000 | 2,417 MB | 241.7 kB | 241.7 kB | 23.6 % | 10,708 MB | 4.4× |
| `clustering-apa0-face0.json` | 10,000 | 1,252 MB | 125.2 kB | 125.2 kB | 12.2 % | 5,412 MB | 4.3× |
| `clustering-apa1-face0.json` | 10,000 | 1,191 MB | 119.1 kB | 119.1 kB | 11.6 % | 5,018 MB | 4.2× |
| `op.json` | 10,000 | 123 MB | 12.3 kB | 12.3 kB | 1.2 % | 627 MB | 5.1× |
| `tagger_tgm.json` | 10,000 | 75 MB | 7.5 kB | 7.5 kB | 0.7 % | 534 MB | 7.1× |
| `tagger_stm.json` | 10,000 | 75 MB | 7.5 kB | 7.5 kB | 0.7 % | 534 MB | 7.1× |
| `tagger_fc.json` | 10,000 | 75 MB | 7.5 kB | 7.5 kB | 0.7 % | 534 MB | 7.1× |
| `tagger_lm.json` | 10,000 | 75 MB | 7.5 kB | 7.5 kB | 0.7 % | 534 MB | 7.1× |
| `shower_track-global.json` | 4,455 | 39 MB | 3.9 kB | 8.8 kB | 0.4 % | 332 MB | 8.5× |
| `track_fit-global.json` | 4,455 | 20 MB | 2.0 kB | 4.4 kB | 0.2 % | 54 MB | 2.7× |
| `channel-deadarea-apa0-face0.json` | 10,000 | 7 MB | 0.7 kB | 0.7 kB | 0.1 % | 17 MB | 2.3× |
| `channel-deadarea-apa1-face0.json` | 10,000 | 7 MB | 0.7 kB | 0.7 kB | 0.1 % | 17 MB | 2.4× |
| `vertices-global.json` | 4,455 | 2 MB | 0.2 kB | 0.5 kB | 0.0 % | 4 MB | 2.0× |
| `mc.json` | 10,000 | 2 MB | 0.2 kB | 0.2 kB | 0.0 % | 5 MB | 2.3× |

### beam-off — 10,000 zips, 10.5 GB, 1,048 kB/event

| layer | in N events | compressed total | per event (all) | per event (when present) | share | uncompressed total | ratio |
|---|---|---|---|---|---|---|---|
| `img-global.json` | 10,000 | 2,497 MB | 249.7 kB | 249.7 kB | 23.8 % | 10,921 MB | 4.4× |
| `clustering-global.json` | 10,000 | 2,496 MB | 249.6 kB | 249.6 kB | 23.8 % | 13,501 MB | 5.4× |
| `clustering-pr-global.json` | 10,000 | 2,484 MB | 248.4 kB | 248.4 kB | 23.7 % | 11,000 MB | 4.4× |
| `clustering-apa0-face0.json` | 10,000 | 1,279 MB | 127.9 kB | 127.9 kB | 12.2 % | 5,519 MB | 4.3× |
| `clustering-apa1-face0.json` | 10,000 | 1,230 MB | 123.0 kB | 123.0 kB | 11.7 % | 5,175 MB | 4.2× |
| `op.json` | 10,000 | 118 MB | 11.8 kB | 11.8 kB | 1.1 % | 597 MB | 5.1× |
| `tagger_tgm.json` | 10,000 | 82 MB | 8.2 kB | 8.2 kB | 0.8 % | 552 MB | 6.7× |
| `tagger_stm.json` | 10,000 | 82 MB | 8.2 kB | 8.2 kB | 0.8 % | 552 MB | 6.7× |
| `tagger_fc.json` | 10,000 | 82 MB | 8.2 kB | 8.2 kB | 0.8 % | 552 MB | 6.7× |
| `tagger_lm.json` | 10,000 | 82 MB | 8.2 kB | 8.2 kB | 0.8 % | 552 MB | 6.7× |
| `channel-deadarea-apa0-face0.json` | 10,000 | 7 MB | 0.7 kB | 0.7 kB | 0.1 % | 17 MB | 2.3× |
| `channel-deadarea-apa1-face0.json` | 10,000 | 7 MB | 0.7 kB | 0.7 kB | 0.1 % | 17 MB | 2.4× |
| `shower_track-global.json` | 626 | 6 MB | 0.6 kB | 10.0 kB | 0.1 % | 53 MB | 8.5× |
| `track_fit-global.json` | 626 | 3 MB | 0.3 kB | 4.8 kB | 0.0 % | 8 MB | 2.8× |
| `mc.json` | 10,000 | 1 MB | 0.1 kB | 0.1 kB | 0.0 % | 2 MB | 1.5× |
| `vertices-global.json` | 626 | 0 MB | 0.0 kB | 0.5 kB | 0.0 % | 1 MB | 2.0× |

## C. `tracking-pr.root` — per TTree, candidate vs non-candidate files (zip = compressed on disk, tot = uncompressed)


### MC BNB CV — candidate (has T_kine): 6,138 files, 1,684 MB, 274.4 kB/file

| tree | zip total | per file | share of files' bytes | uncompressed | ratio |
|---|---|---|---|---|---|
| `T_tagger` | 743.2 MB | 121.1 kB | 44.1 % | 743.8 MB | 1.0× |
| `T_proj_data` | 208.5 MB | 34.0 kB | 12.4 % | 653.9 MB | 3.1× |
| `T_rec_charge` | 138.8 MB | 22.6 kB | 8.2 % | 237.7 MB | 1.7× |
| `T_kine` | 19.6 MB | 3.2 kB | 1.2 % | 19.8 MB | 1.0× |
| `T_cluster` | 16.6 MB | 2.7 kB | 1.0 % | 35.3 MB | 2.1× |
| `T_bad_ch` | 5.7 MB | 0.9 kB | 0.3 % | 19.3 MB | 3.4× |
| `Trun` | 2.5 MB | 0.4 kB | 0.1 % | 2.5 MB | 1.0× |
| `T_proj` | 0.0 MB | 0.0 kB | 0.0 % | 0.0 MB | 0.0× |

Trees account for 67 % of the file bytes; the rest is ROOT file structure/keys (~89.5 kB/file).

### MC BNB CV — non-candidate: 7,078 files, 87 MB, 12.3 kB/file

| tree | zip total | per file | share of files' bytes | uncompressed | ratio |
|---|---|---|---|---|---|
| `T_cluster` | 18.3 MB | 2.6 kB | 21.1 % | 36.1 MB | 2.0× |
| `T_bad_ch` | 6.6 MB | 0.9 kB | 7.6 % | 22.2 MB | 3.4× |
| `Trun` | 2.9 MB | 0.4 kB | 3.3 % | 2.9 MB | 1.0× |
| `T_proj` | 0.0 MB | 0.0 kB | 0.0 % | 0.0 MB | 0.0× |

Trees account for 32 % of the file bytes; the rest is ROOT file structure/keys (~8.3 kB/file).

### MC nueCC — candidate (has T_kine): 8,318 files, 2,688 MB, 323.2 kB/file

| tree | zip total | per file | share of files' bytes | uncompressed | ratio |
|---|---|---|---|---|---|
| `T_tagger` | 1,024.5 MB | 123.2 kB | 38.1 % | 1,033.0 MB | 1.0× |
| `T_proj_data` | 516.0 MB | 62.0 kB | 19.2 % | 1,743.0 MB | 3.4× |
| `T_rec_charge` | 339.7 MB | 40.8 kB | 12.6 % | 618.7 MB | 1.8× |
| `T_kine` | 26.7 MB | 3.2 kB | 1.0 % | 27.1 MB | 1.0× |
| `T_cluster` | 24.6 MB | 3.0 kB | 0.9 % | 62.0 MB | 2.5× |
| `T_bad_ch` | 7.8 MB | 0.9 kB | 0.3 % | 26.1 MB | 3.4× |
| `Trun` | 3.4 MB | 0.4 kB | 0.1 % | 3.4 MB | 1.0× |
| `T_proj` | 0.0 MB | 0.0 kB | 0.0 % | 0.0 MB | 0.0× |

Trees account for 72 % of the file bytes; the rest is ROOT file structure/keys (~89.6 kB/file).

### MC nueCC — non-candidate: 559 files, 7 MB, 12.3 kB/file

| tree | zip total | per file | share of files' bytes | uncompressed | ratio |
|---|---|---|---|---|---|
| `T_cluster` | 1.5 MB | 2.7 kB | 21.7 % | 3.1 MB | 2.1× |
| `T_bad_ch` | 0.5 MB | 0.9 kB | 7.6 % | 1.8 MB | 3.4× |
| `Trun` | 0.2 MB | 0.4 kB | 3.3 % | 0.2 MB | 1.0× |
| `T_proj` | 0.0 MB | 0.0 kB | 0.0 % | 0.0 MB | 0.0× |

Trees account for 33 % of the file bytes; the rest is ROOT file structure/keys (~8.3 kB/file).

### beam-on — candidate (has T_kine): 4,596 files, 1,256 MB, 273.2 kB/file

| tree | zip total | per file | share of files' bytes | uncompressed | ratio |
|---|---|---|---|---|---|
| `T_tagger` | 556.5 MB | 121.1 kB | 44.3 % | 557.0 MB | 1.0× |
| `T_proj_data` | 152.9 MB | 33.3 kB | 12.2 % | 477.8 MB | 3.1× |
| `T_rec_charge` | 101.8 MB | 22.2 kB | 8.1 % | 174.1 MB | 1.7× |
| `T_kine` | 14.7 MB | 3.2 kB | 1.2 % | 14.8 MB | 1.0× |
| `T_cluster` | 12.2 MB | 2.7 kB | 1.0 % | 26.2 MB | 2.1× |
| `T_bad_ch` | 4.3 MB | 0.9 kB | 0.3 % | 14.5 MB | 3.4× |
| `Trun` | 1.9 MB | 0.4 kB | 0.1 % | 1.9 MB | 1.0× |
| `T_proj` | 0.0 MB | 0.0 kB | 0.0 % | 0.0 MB | 0.0× |

Trees account for 67 % of the file bytes; the rest is ROOT file structure/keys (~89.6 kB/file).

### beam-on — non-candidate: 5,404 files, 66 MB, 12.2 kB/file

| tree | zip total | per file | share of files' bytes | uncompressed | ratio |
|---|---|---|---|---|---|
| `T_cluster` | 13.9 MB | 2.6 kB | 21.1 % | 28.3 MB | 2.0× |
| `T_bad_ch` | 5.1 MB | 0.9 kB | 7.7 % | 17.0 MB | 3.4× |
| `Trun` | 2.2 MB | 0.4 kB | 3.3 % | 2.2 MB | 1.0× |
| `T_proj` | 0.0 MB | 0.0 kB | 0.0 % | 0.0 MB | 0.0× |

Trees account for 32 % of the file bytes; the rest is ROOT file structure/keys (~8.3 kB/file).

### beam-off — candidate (has T_kine): 976 files, 254 MB, 260.6 kB/file

| tree | zip total | per file | share of files' bytes | uncompressed | ratio |
|---|---|---|---|---|---|
| `T_tagger` | 118.2 MB | 121.2 kB | 46.5 % | 118.3 MB | 1.0× |
| `T_proj_data` | 25.5 MB | 26.2 kB | 10.0 % | 84.1 MB | 3.3× |
| `T_rec_charge` | 15.4 MB | 15.7 kB | 6.0 % | 26.5 MB | 1.7× |
| `T_kine` | 3.1 MB | 3.2 kB | 1.2 % | 3.1 MB | 1.0× |
| `T_cluster` | 2.6 MB | 2.6 kB | 1.0 % | 5.5 MB | 2.1× |
| `T_bad_ch` | 0.9 MB | 0.9 kB | 0.4 % | 3.1 MB | 3.4× |
| `Trun` | 0.4 MB | 0.4 kB | 0.2 % | 0.4 MB | 1.0× |
| `T_proj` | 0.0 MB | 0.0 kB | 0.0 % | 0.0 MB | 0.0× |

Trees account for 65 % of the file bytes; the rest is ROOT file structure/keys (~90.4 kB/file).

### beam-off — non-candidate: 9,024 files, 110 MB, 12.2 kB/file

| tree | zip total | per file | share of files' bytes | uncompressed | ratio |
|---|---|---|---|---|---|
| `T_cluster` | 23.2 MB | 2.6 kB | 21.0 % | 47.0 MB | 2.0× |
| `T_bad_ch` | 8.5 MB | 0.9 kB | 7.7 % | 28.4 MB | 3.4× |
| `Trun` | 3.6 MB | 0.4 kB | 3.3 % | 3.6 MB | 1.0× |
| `T_proj` | 0.0 MB | 0.0 kB | 0.0 % | 0.0 MB | 0.0× |

Trees account for 32 % of the file bytes; the rest is ROOT file structure/keys (~8.3 kB/file).
