# Draft review: WireCell/wire-cell-toolkit PR #543 (not posted)

Review type: **Comment** (or **Approve**, if the model move is fine as a follow-up)

## Review body

Thanks @dsnehadri, this is a clear improvement, and the `original` path is preserved exactly. I validated the PR on SBND at FNAL. Details, scripts and numbers: https://github.com/HaiwangYu/wire-cell-toolkit-ai-helper/issues/43

**Setup**
- **Build:** this PR merged into our SBND branch (master `b7bd2a1a` + the flat-tree/truth-match commits), compared with the same branch without it.
- **Events DV2-MAX has never seen:** 100 MC CV + 109 MC nueCC from Gen2 files that are not in r7 at all, plus the real-data hand-scan sets nueCC-48 and NCπ0-19.
- **Runs:** step 2 from identical step-1 inputs, for master, `original`, `dv2_snap`, `dv2_split` and `dv2_split_move`; 1 thread; `DV2_STRICT=1`.
- **Python:** in-chain Python 3.9 / torch 2.6 / numpy 2.0. lightgbm 4.7 has no glibc-2.17 (SL7) wheel, so I used **4.6.0**: it loads `ranker_fold0.txt` without warnings.

**`original` is exactly master.** The compiled config is byte-identical. All 276 events are identical in every tree and branch of `tracking-pr.root` (920k branch arrays), apart from `Trun.wct_version`.

**In-chain = standalone.** I replayed all 229 in-chain DV2 calls standalone, from the dumped `T_dlvtx_cloud` / `T_dlvtx_call` inputs through `DV2_Vertex.DV2_Vertex`. All 228 with a prediction are identical (max 1.6e-5 cm; calibrated score equal to 3e-8). The other is a 2-point cloud with no prediction on either side.

**Physics on unseen events** (the same events for every method):

| | master = `original` | `dv2_snap` | `dv2_split` | `dv2_split_move` |
|---|---|---|---|---|
| vertex within 1 cm of truth (MC, n = 141) | 0.645 | 0.681 | 0.759 | **0.837** |
| within 2 cm | 0.752 | 0.837 | 0.894 | **0.915** |
| ν_e CC selected (`nue_score > 7`), n = 101 | 0.416 | 0.485 | 0.446 | **0.505** |
| ν_μ CC selected (`numu_score > 0.9`), n = 30 | 0.767 | 0.700 | 0.667 | 0.733 |
| ν_μ CC + NC selected as ν_e, n = 52 | 0 | 0 | 0 | 1 |
| data nueCC-48 selected as ν_e | 38 | 38 | 38 | **41** |
| data NCπ0-19 selected as ν_e | 1 | 1 | 1 | 1 |

This agrees with your fold-0 table. The ν_μ and background changes are within statistics (±8 points on ν_μ).

**Cost (1 thread):**

| | master / `original` | `dv2_*` |
|---|---|---|
| vertex step per call, median | 21 ms (uboone SCN) | 0.63 s |
| first call, once per `wire-cell` process | ~5.2 s | ~4.8 s warm; 16–23 s from a cold CVMFS cache |
| whole step 2, CPU, 276 events | 4,442 s | 3,180–3,230 s (**−28 %**: the `original` chain is skipped) |
| peak RSS per process | 1.54 GB median | **+165 MB** |

- Loading is once per process: 27 loads for 276 events, about 6 % of step-2 CPU.
- A one-process-per-event job (`wct-pr-perevt.jsonnet`) would pay about 5 s per event, for either model.

**Crashes:** 4 / 135 step-2 runs crashed, in the known `TaggerCheckNeutrino` / `TrackFitting` places. All 4 passed on rerun, `original` included, so nothing is method-specific.

**Requests:**
1. **Move the model bundle to wire-cell-data** (`uboone/dsnehadri/`, https://github.com/WireCell/wire-cell-data/tree/master/uboone/dsnehadri/). See the inline comment on `cfg/wscript_build`.
2. **Make a missing Python dependency loud.** Without lightgbm, every DV2 call fails, but the job exits 0 and every candidate silently keeps the traditional vertex. See the inline comment on `NeutrinoVertexFinder.cxx`.

**Suggestions:** the dump's traditional-vertex convention; noting the SBND default change. See the inline comments.

## Inline comments

**`cfg/wscript_build` L9** (`bld.install_files('${PREFIX}/share/wirecell', bld.path.ant_glob("dv2max/**/*"), ...)`)

> Could the bundle (`pass1.pt`, `pass2.pt` at ~80 MB each, `ranker_fold0.txt`, `isotonic_fold0.json`, `bundle.json`) live in wire-cell-data instead, e.g. `uboone/dsnehadri/dv2max/r7_cloud/`, next to the SCN weights (`uboone/scn_vtx/…`)?
> - It would resolve through `WIRECELL_PATH` the same way.
> - The toolkit repo (and its history) would not carry ~160 MB of binaries.
> - `wcb install` would not copy them into every `share/wirecell`.
> - New models could be added without a toolkit release.
>
> The default `dv2_bundle` would then be `uboone/dsnehadri/dv2max/r7_cloud/bundle.json`, and this install rule can go.

**`cfg/pgrapher/experiment/sbnd/clus.jsonnet` L1027** (`dv2_bundle='dv2max/r7_cloud/bundle.json'`)

> The path to update if the bundle moves to wire-cell-data (see `cfg/wscript_build`).
>
> Separately: with `vertex_method='dv2_split_move'` as the SBND default, every SBND job that does not pass the option changes its physics output, and also needs torch + scipy + lightgbm at run time. Could the PR description or release notes say so explicitly, with `--tla-str vertex_method=original` as the way to keep the previous behaviour?

**`clus/src/NeutrinoVertexFinder.cxx` L4921** (`std::vector<float> trad3(3, std::numeric_limits<float>::quiet_NaN());`)

Two things around this call:

> **1. A missing dependency is silent.** I ran a `dv2_split_move` job with lightgbm absent from `PYTHONPATH` and `DV2_STRICT` unset.
> - Every DV2 call failed with `ModuleNotFoundError: No module named 'lightgbm'`. Each candidate kept the traditional vertex with the original refinement; only a WARN line and stderr show it.
> - The job exited 0 with complete-looking output.
> - Each call also retried the import (0.7–18 s per call), because the vertexer is cached only on success.
>
> We hit the same trap with the SCN net ("DL vertex failed", geometric fallback, rc 0). Could the dv2 methods check that the Python side imports, and the bundle loads, at configure time or on the first call, and throw otherwise? Keep the per-call fallback only for a genuine no-prediction case (fewer than 5 points). At least, could the fallback count reach the output (e.g. a `Trun`/`T_tagger` field), so that a degraded production is visible without the DL-vertex dump?
>
> **2. The dump's convention differs from the call's.** When there is no traditional vertex, this call passes NaN (good: DV2-MAX then has no `tag_nu`). But `PRDlVtxDump` keeps `trad_valid = 0` with `trad_x/y/z = 0`.
> - Replaying a call from the dump with `(0, 0, 0)` gives DV2-MAX a fake tag at the origin and a different pick. That happened to 2 of my 229 replayed calls until I honoured `trad_valid`.
> - Could the dump write NaN for `trad_*` when `trad_valid` is false, or document that replays must pass NaN? The same applies to `validate_r7.py`-style tools.

**`pyutil/python/DV2_Vertex.py` L71** (`def _hook(rec):`)

> Optional: an input digest in the hook record (e.g. sha1 of the x/y/z/q bytes plus `n_vertex_rows` and `trad`) would let any in-chain call be matched to its standalone replay without guessing. I matched on `(n, n_vertex_rows)` + nearest prediction.

**`pyutil/python/dv2max_vertexer/README.md`** (requirements; no line anchor needed)

> For SL7 / glibc 2.17 (the SBND UPS stack), lightgbm 4.7 has no wheel; 4.6.0 works with this bundle (identical in-chain and standalone results; no warnings). It may be worth listing the tested versions: Python 3.9, numpy 2.0.2, scipy 1.13.1, torch 2.6.0, lightgbm 4.6.0.
