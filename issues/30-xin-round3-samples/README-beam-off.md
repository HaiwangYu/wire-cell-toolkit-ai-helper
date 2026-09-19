# beam-off — SBND Gen2 Run-1 off-beam data reco1 (frameshifted) for Xin (round-3 samples, ai-helper #30)

- SAM definition of the source: `data_SBND2026A_gen2_InTime-Run1_v10_14_02_02_reco1_sbnd` (unblinded OffBeamLight stream, sbndcode v10_14_02_02, 49,020 files / 2.2 M events; the same source as our round-3 beam-off sample in #26).
- `reco1/data_SBND2026A_InTime-Run1_reco1_frameshift_1000evt.root`: the first 1,000 events of the 25 raw reco1 files in `lists/reco1-source-files.lst` (first 25 of our seeded random 240-file selection), merged by `lar -c run_frameshift.fcl -n 1000` **with the `sbnd::timing::FrameShiftInfo_frameshift__FRAMESHIFT.` product added** — required by the standalone reader (`caf_offset_mode=product`). 1,000 unique (run, subrun, event), 21 runs; the list is `lists/data_SBND2026A_InTime-Run1_reco1_frameshift_1000evt.rse.tsv`.
- Products: `sptpc2d:{dnnsp,wienersummary,badmasks}` (process Reco1), `opflashtpc0/1`, FrameShift. Data reality: point shift (`pos_offset`) applies, `QtoL=0.86` — see the #26 data-vs-MC audit.
- Note: art fast-cloning had to be disabled for this merge (`run_frameshift_nofastclone.fcl`, in `scripts/`), because some input files lack `raw::TimingReferenceInfo_xarapucadecoder__DECODE.`; the output is a normal art file.
- Integrity: `md5sum -c MD5SUMS.txt`.
