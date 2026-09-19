# Round-3 samples for Xin on wcgpu1: MC CV ~2000, MC nueCC ~2000, beam-off 1000 (reco1 + truth)

Owner request 2026-09-19 (Xin's message): reco1 files for three species so he can measure the effect of PDHD/PDVD-era improvements on SBND before touching it; MC needs event-level truth. wcgpu1's agent pulls from sbndbuild03 (the reverse direction is not possible), so everything is staged on FNAL disk first.

## Layout (identical on both sides)

FNAL: `/exp/sbnd/data/users/yuhw/production-prep/xin-round3-samples/`  →  wcgpu1: `/nfs/data/1/yuhw/2025-fall-prod-sample/xin-round3-samples/`

```
mc-cv/      reco1/*.root  lists/{SAMDEF.txt,reco1-files.lst,skipped-not-online.lst}  truth/mc-cv-truth.tsv      MD5SUMS.txt  README.md
mc-nuecc/   reco1/*.root  lists/...                                                  truth/mc-nuecc-truth.tsv   MD5SUMS.txt  README.md
beam-off/   reco1/data_SBND2026A_InTime-Run1_reco1_frameshift_1000evt.root  lists/{SAMDEF.txt,reco1-source-files.lst,*.rse.tsv}  MD5SUMS.txt  README.md
scripts/    dump_truth.py copy-sample.sh make-frameshift-1k.sh run_frameshift_nofastclone.fcl
```

## Samples

| species | source (SAM) | selection | events | files | size |
|---|---|---|---|---|---|
| **MC BNB CV** (the inclusive Gen2 CV; no dedicated νμCC sample exists in SBND2026A — the truth TSV tells which events are νμCC) | `aurora_SBND2026A_gen2_BNBLight_prodgenie_corsika_proton_rockbox0p1_sbnd_CV_v10_14_02_03_reco1_sbnd` | first files of our validated 1,000-file list (#16/#26) that are ONLINE in dCache, until ≥ 2,000 events | 2,017 | 154 | ~55 GB |
| **MC nueCC** (exclusive) | `…_EX_nuecc_v10_14_02_05_reco1_sbnd` | same rule on the #19/#26 list | 2,001 | 225 | ~50 GB |
| **beam-off** | `data_SBND2026A_gen2_InTime-Run1_v10_14_02_02_reco1_sbnd` (unblinded off-beam, our round-3 choice) | first 25 of our random 240-file selection → **merged + FrameShift added** (`run_frameshift.fcl`), `-n 1000` | 1,000 | 1 | ~4 GB |

Beam-off is delivered frameshifted because Xin's stage-A reader requires the `FrameShiftInfo` product (`caf_offset_mode=product`, it aborts without it); the raw reco1 files carry none. `run_frameshift.fcl` needed `outputs.out1.fastCloning: false` for this file set (a product missing in some inputs otherwise ends the merge with "Tree branches have different numbers of entries").

MC truth: **inside the reco1 files** (`simb::MCTruths_generator__GenieGen.`) plus a per-event TSV — see [`truth-from-reco1.md`](truth-from-reco1.md) (columns, how it was made, how to do it standalone à la `wire-cell-sbnd-reco1`).

## Status

- [x] lists fixed (2026-09-19 14:33; 5 CV + 11 nueCC files skipped as dCache `UNAVAILABLE`, replaced by the next online files)
- [x] MC copies /pnfs → FNAL staging (2026-09-19 14:35; 154 + 225 files, sizes verified)
- [x] beam-off frameshift merge (1,000 unique events, 21 runs, FrameShift product verified)
- [x] truth TSVs, MD5SUMS, READMEs (14:50) — **STAGING COMPLETE**
- [ ] wcgpu1 agent: rsync (instructions below), verify MD5SUMS, report here
- [ ] Xin: confirm

## Truth content (from the TSVs)

| | MC CV (2,017 events) | MC nueCC (2,001 events) |
|---|---|---|
| true-neutrino rows | 3,647 | 3,786 |
| events with ≥1 neutrino vertex in the active TPC | **954** (47 %) | 1,949 (97 %) |
| of which νμCC in TPC | **687** | 107 |
| of which νeCC in TPC | 9 | **1,946** |

So the CV sample gives ~690 in-TPC νμCC events, not 2,000: rockbox events mostly have their neutrino in dirt/cryostat. Reaching ~2,000 in-TPC νμCC would need ~6,000 CV events (~165 GB) — open question to the owner; the tree can be extended incrementally (the wcgpu1 rsync is resumable).

## Instructions for the wcgpu1 agent

Wait for the "STAGING COMPLETE" comment on this issue, then, from wcgpu1:

```
SRC=sbndbuild03.fnal.gov:/exp/sbnd/data/users/yuhw/production-prep/xin-round3-samples/
DST=/nfs/data/1/yuhw/2025-fall-prod-sample/xin-round3-samples/
mkdir -p $DST && rsync -av --partial --progress $SRC $DST            # ~110 GB; re-run to resume
cd $DST && for s in mc-cv mc-nuecc beam-off; do (cd $s && md5sum -c MD5SUMS.txt | grep -v ': OK$'; echo "$s checked"); done
```
Then post: file counts per species, `md5sum -c` result, total size, wall time. Do not modify anything under the tree; if a file fails the checksum, re-rsync that file and re-check.

## Traps
- `/pnfs` files can be `UNAVAILABLE` in dCache (5/153 CV, 11/226 nueCC on 2026-09-19): `cp` blocks forever. Check `.(get)(<file>)(locality)` first (`copy-sample.sh` does not; the list builder does).
- Gen2 data must be frameshifted before any Wire-Cell chain; MC must not be.
- MC reco1 is ~28 MB/event — plan disk accordingly.
