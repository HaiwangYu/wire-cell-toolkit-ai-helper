# 42 — SBND r8: the r7 samples through the updated chain (2-step + truth match + CAF merge)

**Request (Haiwang, 2026-10-15):**
- Rerun the r7 samples **MC CV, MC nueCC and beam-off** with the updated chain: the 2-step chain; the truth match of #41; the CAF merge of #39; the revised dl-vtx dump.
- The open data was already run in #40, so it is not rerun; it is linked into this run's output.
- Two modes:
  - **validation**: ~100 events per sample; keep the Bee zips, `tracking-pr.root`, the merged CAF;
  - **semi-production**: all events; no Bee; keep `tracking-pr.root` and the merged CAF.
- **Load rule on sbndbuild03:** at most 60 % of CPU and memory while the other users take < 20 %, at most 30 % otherwise.

**Decisions (2026-10-15):**
- `qlpctree.tar.gz` is kept in both modes, so step 2 can be redone without step 1.
- The nueCC reco1 files without a flat CAF are **skipped** and recorded loudly (below).

## ⚠ Missing from this round: 55 MC nueCC files (732 events) without a flat CAF

| | files | events |
|---|---|---|
| r7 MC nueCC | 999 | 8,877 |
| **skipped: no flat CAF** | **55** | **732 (8.2 %)** |
| run here | 944 | 8,145 |

- 54 of the 55 reco1 files have **no CAF child at all** in SAM.
- One has a child in `aurora_SBND2026A_gen2_BNBLight_prodgenie_corsika_proton_rockbox0p1_sbnd_EX_nuecc_v10_14_02_05_flat_caf_sbnd`, but the file is not on disk at its location.
- The list is in `lists/mc-nuecc-skipped-no-caf.tsv`.
- These events are in r7 (step 2 without truth match or CAF) but not in r8.

## 1. Inputs

| sample | reco1 | CAF | pairing | pairs | events |
|---|---|---|---|---|---|
| MC CV | r7's 990 files (`r7…/lists/mc-cv.units.tsv`; the 10 of r7's 1,000 that are gone from /pnfs stay out), `aurora_SBND2026A_gen2_BNBLight_…_CV_v10_14_02_03_reco1_sbnd` | `…_CV_v10_14_02_03_flatcaf_sbnd`, path `…/CV/caf/…/reco2-<reco1>.flat.caf.root` | child (name rule, all checked on disk) | 990 | 13,113 |
| MC nueCC | r7's 999 files (`r7…/lists/mc-nuecc.units.tsv`), `…_EX_nuecc_v10_14_02_05_reco1_sbnd` | `…_EX_nuecc_v10_14_02_05_flat_caf_sbnd`, `…/nuecc/caf/…/reco2-<reco1>.flat.caf.root` | child | 944 (55 skipped) | 8,145 |
| beam-off | `data_SBND2026A_gen2_InTime-Run1_v10_14_02_02_reco1_sbnd`: the **212 files** holding r7's 10,000 events | `data_SBND2026A_gen2_InTime-Run1_v10_14_02_02_flatcaf_sbnd` | **sibling** (CAF and reco1 are children of one raw file) | 212 | 10,071 |
| beam-on (open data) | — | — | — | link to #40 | 89,921 |

- Every reco1 and every CAF was `ONLINE` in dCache at pairing time.
- **How the beam-off files were recovered.** r7 read staged, merged and FrameShifted chunks (`r3-data-stage-2026-09-09/beam-off/chunk*.root`), and those chunks and their file lists were deleted after #40. r7's `beam-off/events.tsv` still lists the 10,000 events (91 runs). The metadata of the 37,906 InTime reco1 files of those runs was matched against them.
  - Result: 212 files hold all 10,000 events. 209 are whole; in 3 r7's chunks used only part of the file (44, 33, 2 of 50).
  - Whole files are run here, so 71 more events than r7.
  - Spot check: the reco1 and its sibling CAF have identical event lists (5/5).
- **FrameShift:** step 0 of `run_pair.py` makes the copy for every data file, as in #40.

## 2. Software

| component | pin |
|---|---|
| wire-cell-toolkit | `HaiwangYu/wire-cell-toolkit` `sbnd-wc-flatcaf` `4b6853d4`: master `b7bd2a1a` (incl. the revised dl-vtx dump, WireCell PR 536 review fixes, merged 2026-10-07) + #39 flat tree + #41 truth match |
| larwirecell | `sbnd-wc-flatcaf` `73c79bc` (labeler `truth_detail`) |
| workflow | `sbnd-wirecell-production` `aurora/` `de83d8d` (keep modes, sibling pairing, load governor) |
| schema | `recTreeWireCell.schema.json` 2,401 branches / 20 trees, md5 `d4396a3490ea` |
| step 2 | `dl_vtx_dump=true`, `flat_tree=true`, `truth_match=true` on MC |

## 3. Modes and output

`/exp/sbnd/data/users/yuhw/production-prep/r8-r26-truth-caf/`:

| dir | pairs | `WC_KEEP` | kept per pair |
|---|---|---|---|
| `validation/{mc-cv,mc-nuecc,beam-off}` | first pairs of each list to ≥ 100 events: 7 / 11 / 2 pairs, 113 / 103 / 100 events | `validation` | `ql/all/qlpctree.tar.gz`, `ql/all/mabc.zip`, `pr/all/mabc-pr.zip`, `pr/all/pr_evt<E>/tracking-pr.root`, `merged/*.wc.flat.caf.root`, logs |
| `semiprod/{mc-cv,mc-nuecc,beam-off}` | all | `semiprod` | as validation without the two Bee zips |
| `semiprod/beam-on-opendata` | → `../../opendata-fixeddev-prep/run` (#40: qlpctree + merged CAF, no `tracking-pr.root`) | | |
| `lists/` | `validation-<s>.tsv`, `semiprod-<s>.tsv`, `mc-nuecc-skipped-no-caf.tsv` | | |
| `control/` | `governor.log`, `maxpar.override`, `memguard.override`, `krb-renew.log` | | |

Deleted in both modes: the FrameShift copies, `nugraph.h5`, and failed tries' large files (their logs stay).

## 4. Load rule

`bin/load-governor.sh control/` measures, every minute, the other users' summed CPU (`top`, 10 s sample) and RSS on sbndbuild03 (64 cores, 125 GB):

| state | condition | budget for all six pools together |
|---|---|---|
| idle | other users < 20 % CPU **and** < 20 % memory, 3 minutes in a row | 60 %: 38 jobs on cores 26–63, our RSS ≤ 75 GB |
| busy | otherwise (switch at once) | 30 %: 19 jobs, our RSS ≤ 37 GB |

- Each job is one single-threaded process.
- Running jobs are never killed, so after a switch to busy our load drains as pairs finish (10–25 min each).
- At the start (2026-10-15 22:38) the others held 3–11 % CPU and 21 % memory, i.e. busy.

## 5. Estimate

- **Events:** 31,329 (semi-production) + 316 (validation).
- **Time:** about 29 s per event per job (#40: 28.6 s on data; MC similar), so about 255 job-hours: about **7 h at 60 %**, **13 h at 30 %**.
- **Disk:** about 3.5 MB per event kept (qlpctree 2–2.5, `tracking-pr.root` 0.2–0.6, merged CAF 0.25–0.9), so about **110 GB**, plus Bee for the 316 validation events.

## Log
- 2026-10-16 12:15: **validation done**: 20/20 pairs OK, 20/20 `validate.json` PASS; MC CV 113 events, MC nueCC 103, beam-off 100.
  - The 9 pairs stopped in the incident were rerun by restarting their pools.
  - Kept as planned: Bee zips, `tracking-pr.root`, merged CAF, qlpctree.
  - Truth-match trees in every MC event (216/216) and in no data event (0/100); `T_dlvtx_call` and `recTreeWireCell` in every event.
  - Size: 983 / 1,090 / 315 MB.
- 2026-10-16 11:29–11:37: **memory incident.** One user's job grew 56 → 70 GB within a minute; swap full, MemAvailable 8.9 GB with our 19 step-1 jobs (23 GB) still growing.
  - Action: governor paused, cap 10; the 9 newest validation pairs killed (whole process trees: no orphan `lar`). Later the 4 newest pairs too, after the pools refilled; MemAvailable back to 30 GB.
  - Governor fixed (workflow `1350333`, see below): the job cap also respects memory headroom (MemAvailable minus what our running jobs will still grow, minus 20 GB, at 2 GB per job), and it logs ALERT below 10 GB.
  - Found: three pools can launch at the same instant and overshoot the shared cap by 1–2 (a launch lock in `run-pairs.sh` will fix it; not edited while the pools run).
  - 11:37: the other user is back at 27 GB; we run 20 pairs (30 GB), 47 GB available.
  - The killed pairs (13) have no status and are picked up when `launch.sh` is rerun after the pools finish.
- 2026-10-16 11:28: launched (`launch.sh`; ticket `/tmp/krb5cc_53514_r8campaign`, renewable to 10-23, hourly `krb-renew-r8`; the old r6 renewer stopped). Machine busy at launch: other users 29 % CPU, 77 % memory (one user 56 GB) -> 30 % budget, 19 pairs; 41 GB available.
- 2026-10-15: inputs paired (beam-off recovered from r7's events.tsv; sibling pairing); 55 nueCC files without CAF skipped (owner); qlpctree kept in both modes (owner); workflow `de83d8d`; waiting for a Kerberos ticket to launch.
