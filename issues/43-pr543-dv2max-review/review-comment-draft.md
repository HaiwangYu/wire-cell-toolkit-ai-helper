Thanks, @dsnehadri. I validated this on SBND at FNAL, on events DV2-MAX has never seen. Details and scripts: https://github.com/HaiwangYu/wire-cell-toolkit-ai-helper/issues/43

**Setup**
- **Builds:** this PR merged into our SBND branch (master `b7bd2a1a` + the flat-tree/truth-match commits), compared against the same branch without the PR.
- **Samples:** 100 MC CV + 109 MC nueCC events from Gen2 files that are not in r7 at all, plus the two real-data hand-scan sets nueCC-48 and NCπ0-19.
- **Runs:** step 2 from identical step-1 inputs for master, `original`, `dv2_snap`, `dv2_split` and `dv2_split_move`; 1 thread; `DV2_STRICT=1`.
- **Python:** the in-chain interpreter is Python 3.9 / torch 2.6 / numpy 2.0. lightgbm 4.7 has no glibc-2.17 wheel, so I used **lightgbm 4.6.0**; it loads `ranker_fold0.txt` without warnings.

**1. `original` reproduces master exactly.** The compiled config is byte-identical. All 276 events are identical in every tree and branch of `tracking-pr.root` (920k branch arrays), apart from `Trun.wct_version`. The vertex and selection numbers are identical too.

**2. In-chain vs standalone.** I replayed every in-chain DV2 call (229) standalone, from the dumped `T_dlvtx_cloud` through `DV2_Vertex.DV2_Vertex`, and compared with the `DV2_HOOK_LOG` record:
- 226 / 228 are identical (< 1e-4 cm; calibrated score equal to 2e-8).
- 2 differ: by 0.09 cm, and by 0.22 cm with the score 0.58 vs 0.44. In the latter, the ranker sees 121 candidates in-chain and 122 standalone (one CNN mode). So the torch passes are not bit-identical inside `wire-cell`, with the same inputs, the same torch library and 1 thread. These are near-ties like the GPU vs CPU ones in your README, and both sides are deterministic.
- A suggestion: add an input digest (e.g. sha1 of the x/y/z/q bytes) to the `DV2_HOOK_LOG` record, so a call can always be matched to its standalone replay.

**3. Cost (1 thread):**

| | master / `original` | `dv2_*` |
|---|---|---|
| vertex step per call, median | 21 ms (uboone SCN) | 0.63 s |
| first call of a process | ~5.4 s | ~9 s (imports + model load) |
| whole step 2, CPU, 276 events | 4,442 s | 3,180–3,230 s (−28 %: the `original` chain is skipped) |
| peak RSS per process | 1.54 GB median | +165 MB |

**Physics on these unseen events** (the same events for every method):

| | master = `original` | `dv2_snap` | `dv2_split` | `dv2_split_move` |
|---|---|---|---|---|
| vertex within 1 cm of truth (MC, n = 141) | 0.645 | 0.681 | 0.759 | **0.837** |
| within 2 cm | 0.752 | 0.837 | 0.894 | **0.915** |
| ν_e CC selected (`nue_score > 7`), n = 101 | 0.416 | 0.485 | 0.446 | **0.505** |
| ν_μ CC selected (`numu_score > 0.9`), n = 30 | 0.767 | 0.700 | 0.667 | 0.733 |
| ν_μ CC + NC selected as ν_e, n = 52 | 0 | 0 | 0 | 1 |
| data nueCC-48 selected as ν_e | 38 | 38 | 38 | **41** |
| data NCπ0-19 selected as ν_e | 1 | 1 | 1 | 1 |

This agrees with your fold-0 table (0.581 / 0.661 / 0.801 / 0.847). The ν_μ and background numbers are within statistics.

**Crashes:** 4 / 135 step-2 runs crashed, in the known `TaggerCheckNeutrino` / `TrackFitting` places. All 4 were intermittent: on rerun they passed, `original` included. So I see nothing method-specific.

**Request: move the model files to wire-cell-data.**
- `cfg/dv2max/r7_cloud/` (`pass1.pt`, `pass2.pt` at ~80 MB each, `ranker_fold0.txt`, `isotonic_fold0.json`, `bundle.json`) would fit better in https://github.com/WireCell/wire-cell-data/tree/master/uboone/dsnehadri/.
- It would then resolve through `WIRECELL_PATH` the same way as the SCN weights (`uboone/scn_vtx/…`). The toolkit repo and every `wcb install` (which copies `cfg/` to `share/wirecell`) would no longer carry 160 MB of binaries.
- The default `dv2_bundle` would become e.g. `uboone/dsnehadri/dv2max/r7_cloud/bundle.json`.
