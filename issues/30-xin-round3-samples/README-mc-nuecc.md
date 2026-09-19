# mc-nuecc — SBND Gen2 MC reco1 for Xin (round-3 samples, ai-helper #30)

- SAM definition: `aurora_SBND2026A_gen2_BNBLight_prodgenie_corsika_proton_rockbox0p1_sbnd_EX_nuecc_v10_14_02_05_reco1_sbnd` (the exclusive intrinsic-νe CC sample, same production family)
- Files: 225 reco1 artROOT files in `reco1/` (`lists/reco1-files.lst` = their /pnfs origin; `lists/skipped-not-online.lst` = files of our list skipped because dCache had them UNAVAILABLE). sbndcode v10_14_02_05, products `simtpc2d:{dnnsp,wienersummary,badmasks}` (process DetSim), `opflashtpc0/1`, no FrameShift (MC).
- Selection: the first files of the 1,000-file list used in our #16/#19/#26 campaigns, until ≥ 2,000 events — i.e. the same events our validated 1-step chain has already processed (outputs in ai-helper #26 → data guide).
- Truth: `truth/mc-nuecc-truth.tsv`, one row per (event, true neutrino) — columns and how it was made: https://github.com/HaiwangYu/wire-cell-toolkit-ai-helper/blob/main/issues/30-xin-round3-samples/truth-from-reco1.md . The full GENIE/G4 truth is also inside the reco1 files (`simb::MCTruths_generator__GenieGen.` etc.).
- Integrity: `md5sum -c MD5SUMS.txt`.
- Staged 2026-09-19 by yuhw (FNAL sbndbuild03) → wcgpu1 `/nfs/data/1/yuhw/2025-fall-prod-sample/xin-round3-samples/mc-nuecc/`.
