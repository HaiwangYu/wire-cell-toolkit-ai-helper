# 40 — SBND open FixedDev BNB data: full 2-step + CAF-merge production

The first full production with the #39 workflow: every reco1 file of the open FixedDev BNB data definition went through the 2-step Wire-Cell chain. The output was merged into the matching flat CAF as `recTreeWireCell`. The production ran on FNAL sbndbuild03, 2026-10-10 01:40 – 21:04 CDT.

**Result:**
- 1,817 pairs: 1,816 `OK`, 1 `PARTIAL`, 0 `FAIL`. Every `validate.json` is `PASS`.
- 89,921 of the 89,946 CAF events (99.97 %) have Wire-Cell output.
- 3 reco1 files have no CAF to merge into.

Builds on #39 (the workflow, schema and validation) and #38 (the r7 2-step chain, and the step-2 crash it found).

## 1. Input

| | |
|---|---|
| reco1 SAM definition | `data_MCP2025C_Fall25-Run1_BNB_FixedDev_bnblight_v10_14_02_reco1_sbnd`: 1,820 files, 381.6 GB, runs 18255 and 18259, sbndcode `v10_14_02`, `/pnfs/sbn/data_add/sbn_nd/poms_production/data/MCP2025C/v10_14_02/Fall25-Run1_BNB_Dev_bnblight/reco1/bnblight/` |
| CAF SAM definition | `data_SBND2026A_SBND2026A_gen2_run1_BNBLight_Data_FixedDev_Respin_v10_14_02_04_flatcaf_sbnd`: 1,817 files, 18.5 GB, sbndcode `v10_14_02_04`, `/pnfs/sbn/data_add/sbn_nd/poms_production/data/SBND2026A/v10_14_02_04/SBND2026A_gen2_run1_BNBLight_Data_FixedDev_Respin/flatcaf/data_filtered_decoded/` |
| events | 89,946 (SAM `sbn_dm.event_count`; 1–50 per file, mean 49.5) |
| dCache | every reco1 and every CAF `ONLINE` at pairing time |

### Why the Respin CAF (Haiwang's choice, 2026-10-10)

The data has two flat-CAF productions:
- **gen2 FixedDev Respin** (`v10_14_02_04`): reco2 + CAF rerun on these reco1 files. Each CAF is a **direct SAM child** of its reco1, and the two have identical event lists in all 1,817 pairs. `bin/find-pairs.py` pairs by `ischildof`, so it finds these.
- **MCP2025C original** (`data_MCP2025C_Fall25-Run1_BNB_{Fixed,}Dev_bnblight_v10_14_02_flatcaf_sbnd`, `v10_14_02`): made from the raw `EventBuilder` file in one decode→reco1→reco2→caf job. Its only parent is the raw file, so it is a **sibling** of the reco1, and `find-pairs.py` finds 0 of them.

The two FixedDev definitions each apply `sbnd.random < 0.74` on their own files. So `data_MCP2025C_..._FixedDev_..._flatcaf_sbnd` is not the CAF counterpart of the reco1 definition either.

### Pair database

| file | what |
|---|---|
| [`lists/pairs.tsv`](lists/pairs.tsv) | the 1,817 pairs: `id`, `reality`, reco1 path, CAF path, reco1 events (output of `bin/find-pairs.py`) |
| [`lists/missing-caf.tsv`](lists/missing-caf.tsv) | the 3 reco1 files without a Respin CAF, with their MCP2025C CAF sibling |
| [`lists/status.tsv`](lists/status.tsv) | per pair: status, CAF events, Wire-Cell events, validation verdict, merged CAF path, qlpctree path |
| [`scripts/find-pairs.sh`](scripts/find-pairs.sh), [`scripts/launch.sh`](scripts/launch.sh) | the exact commands used |
| FNAL `production-prep/opendata-fixeddev-prep/` | the same files plus `meta-reco1.json` / `meta-caf.json` (full SAM metadata of every file), `reco1-locality.txt`, `README.md` (run notes) |

### Missing in the pair finding

- **reco1 without a CAF: 3 files (150 events, 0.16 %).** These 3 have no child at all in SAM; the Respin skipped them. Each does have an MCP2025C CAF sibling (in `lists/missing-caf.tsv`).

  | reco1 | run | events |
  |---|---|---|
  | `data_filtered_decoded_reco1-2fe8de1b-7e5b-69c4-e71c-5c5a1ee54aa8.root` | 18255 | 50 |
  | `data_filtered_decoded_reco1-c7910425-1185-2f46-8358-26470c8360d9.root` | 18255 | 50 |
  | `data_filtered_decoded_reco1-d1ebf69b-e2c9-9d44-2f31-48d7f55f034b.root` | 18259 | 50 |

- **CAF without a reco1: 0.** All 1,817 Respin CAFs have their parent in the reco1 definition.
- One reco1 (`5f3c8b64-d1cc-eec6-eaa1-bce89a074d8c`) has no MCP2025C CAF sibling. It does have a Respin CAF and is in the production.

## 2. Software

| component | version |
|---|---|
| wire-cell-toolkit | fork `HaiwangYu/wire-cell-toolkit` branch `sbnd-wc-flatcaf` `f6fd2209` (master `b7bd2a1a` + #39), installed in `/exp/sbnd/app/users/yuhw/opt` |
| larwirecell | fork branch `sbnd-wc-flatcaf` `3b54651` |
| step-1 fcl | `wcls-img-clus-matching-data.fcl` from `wcp-porting-img/sbnd/` (`88cb05aa`) |
| FrameShift | sbndcode `run_frameshift.fcl` (step 0) |
| workflow | `HaiwangYu/sbnd-wirecell-production` `aurora/` at `68b7e3c` |
| schema | `aurora/schema/recTreeWireCell.schema.json`: 2,283 branches, 15 trees, md5 `c845fe94fbe5` |
| DL vertex | on, with the dump (`dl_vtx_dump=true`); `dl_fail` 0 everywhere |

### Workflow changes made for this run (`68b7e3c`)
- **Step 0, data only:** `bin/step0-frameshift.sh` copies each reco1 locally with the FrameShift product and checks that the product is there and no event was lost. Step 1 then reads the copy. Without the product, step 1 silently uses a shift of 0.
- **`WC_KEEP=minimal`:** after a pair is merged and validated, only `qlpctree.tar.gz`, the merged CAF and the logs are kept.
- **`site/fnal-sbndbuild03-60pct.sh`:** 60 % of the node (cores 26–63, 38 pairs) at night and on weekends, 19 pairs Mon–Fri 08:00–20:00, a 70 GB RSS guard. Owner-approved for this run only.
- **`find-pairs.py`:** the event count comes from `sbn_dm.event_count`, since the SAM "Event Count" is empty for data.

## 3. Output

`/exp/sbnd/data/users/yuhw/production-prep/opendata-fixeddev-prep/run/<id>/` (`<id>` = the reco1 file name without `.root`):

| path | what | total |
|---|---|---|
| `merged/reco2_data_filtered_decoded_reco1-<uuid>.wc.flat.caf.root` | the Respin flat CAF unchanged, plus `recTreeWireCell` (one entry per `recTree` entry, aligned by run / subrun / event) and `recTreeWireCell_info` (JSON provenance) | 1,817 files, 21.8 GB |
| `ql/all/qlpctree.tar.gz` | step-1 output: imaging, clustering, charge-light matching. Step 2 can be rerun from it | 1,817 files, 170 GB |
| `run_pair.log`, `status`, `events.json`, `validate.json`, `merged/merge.json`, `cost.tsv`, `cost/`, `ql/all/{lar.log.gz,frameshift.txt}`, `pr/all/{wct.log.gz,dl_fail}`, `attempts/*/wct.log.gz` | logs and bookkeeping | small |
| `run/pool.log`, `run/cost-summary.md`, `run/RUN-RECORD.txt` | pool record and cost table | |

- The list of merged CAFs is [`lists/merged-cafs.txt`](lists/merged-cafs.txt).
- Deleted as the run went (`WC_KEEP=minimal`): the FrameShift copies (381 GB), `mabc.zip`, `nugraph.h5`, the per-event `tracking-pr.root` (their content is in `recTreeWireCell`) and `mabc-pr.zip`.
- `recTreeWireCell` layout: the #39 README (`aurora/README.md`). An event without Wire-Cell output has `wc.valid = 0` and 0 rows in every tree.

## 4. Computing resources

| step | wall / event | CPU / event | max RSS median / max | output / event |
|---|---|---|---|---|
| step 0 FrameShift | 0.31 s | 0.18 s | 1.0 / 1.0 GB | 4.2 MB (deleted) |
| step 1 lar | 23.1 s | 22.5 s | 1.6 / 3.1 GB | 4.1 MB (2.0 MB kept: the qlpctree) |
| step 2 wire-cell | 4.5 s | 4.1 s | 1.5 / 6.0 GB | 0.71 MB (deleted) |
| step 3 merge | 0.13 s | 0.11 s | 0.6 / 0.6 GB | 0.25 MB (kept) |
| validate | 0.53 s | 0.52 s | 0.8 / 0.9 GB | |

- **Total:**
  - 687 core-hours of CPU, of which 2.6 were spent on failed tries;
  - 715 job-hours summed wall;
  - **19.4 h elapsed** at 38 concurrent pairs. The run happened to be all on a weekend, so it was at 60 % throughout.
  - The machine stayed at about 62 GB used and 62 GB available; other users took about 7 cores.
- **Disk:**
  - 191 GB kept: qlpctree 170, merged CAF 21.8, logs.
  - 600 GB of intermediates were created and deleted on the way.
  - The peak of in-flight intermediates was about 20 GB.
- **Scaling:** about **28.6 s of wall per event per job** (all steps), or **7.6 core-hours of CPU per 1,000 events**.
  - On sbndbuild03 at 38 slots that was about 4,600 events per hour elapsed, including the tail of the last pairs.
  - Aurora per-core speed is not measured yet.

## 5. Failures

| what | count | outcome |
|---|---|---|
| step-2 intermittent crash (SIGSEGV, RSS ~4.1–4.5 GB, the #38 crash) | 47 failed tries, ~1 per 2,000 events | 41 pairs recovered on try 2; `05efc800` and `d7e657c9` failed twice and recovered on a third try (`WC_RETRY_PARTIAL=1 WC_STEP2_ATTEMPTS=3`) |
| **step-2 deterministic crash**: pair `d5055859-cbfe-accd-26f6-9d1ecb480a26`, run 18259 / subrun 1 / **event 228973** (index 25 of 50) | 5 / 5 tries | `PARTIAL`: 25 / 50 events merged. The crash event and the 24 after it in the file have `wc.valid = 0` |
| step-1 crash | 0 | |
| precheck (missing / tape) | 0 | |

- **The deterministic crash** is a SIGSEGV in `WireCell::Clus::PR::find_vertices` (`clus/src/PRGraph.cxx:330`), called from `PR::mcs_fill_kine` ← `MultiAlgBlobClustering::operator()` (`MultiAlgBlobClustering.cxx:4120`). This is a different place from the intermittent crash (`TrackFitting` / `SteinerGrapher`).
  - Reproducer: `run/data_filtered_decoded_reco1-d5055859-*/ql/all/qlpctree.tar.gz`, step 2 (`bin/step2.sh <tar> <dir> data`). It crashes about 130 s in, on `ident=228973`.
  - Logs: `attempts/step2-all-try{1..5}/wct.log.gz`.

## 6. Left-over issues

1. **Event 228973 crash** (toolkit): fix `PR::find_vertices` / `mcs_fill_kine` with the reproducer above. Then rerun step 2 of `d5055859` from its kept qlpctree (`WC_RETRY_PARTIAL=1`).
2. **A step-2 crash costs the rest of the file.** Step 2 runs one job over the whole qlpctree, so a crash loses every event after it.
   - The 24 events of `d5055859` after 228973 could be recovered now: run step 1 on index 26–49 only, run step 2 on that, and re-merge.
   - `run_pair.py` could do this itself when the same event crashes on every try, as step 1 already does (slicing around the event).
3. **The intermittent step-2 crash** (#38): ~1 per 2,000 events on this data. All recovered by retries, but it costs ~2.6 core-h per 90k events and is not understood.
4. **3 reco1 without a Respin CAF** (150 events): get them respun, or merge them into their MCP2025C CAF sibling. The latter needs a sibling mode in `find-pairs.py` (pair through the shared raw parent), and the CAF version would differ from the rest.
5. **Aurora** (#39): not deployed yet. This run used FNAL sbndbuild03 only.
6. **Kerberos:** the run used the campaign cache `/tmp/krb5cc_53514_r6campaign`, renewed by `production-prep/r6-dlvtx-r26-samples/krb-renew.sh`, which is still running.

## Log

- 2026-10-09: pair finding. The `FixedDev` flatcaf definition gives 0 pairs (its CAFs are siblings), so the Respin definition is used: 1,817 / 1,820, all `ONLINE`, event lists identical. Estimate: ~27 s per event per job, 18–24 h at 38 slots, ~205 GB kept.
- 2026-10-10: workflow changes `68b7e3c`. Smoke on 2 pairs: `OK`, `PASS`, FrameShift 1.0–1.4 µs. Full run 01:40–20:56: 1,814 `OK`, 3 `PARTIAL`. Retry of the 3 `PARTIAL` pairs with 3 tries, 20:58–21:04: 2 recovered, `d5055859` deterministic.
