# Issue 37: duneopdet light simulation -- fixes for the two pile-up bugs of fdvd_sim doc 08a

GitHub: https://github.com/HaiwangYu/wire-cell-toolkit-ai-helper/issues/37.

**Ask (Haiwang, 2026-10-04).** Read wcp-porting-validation
[`fdvd_sim/docs/08a_duneopdet-light-simulation-bugs.md`](https://github.com/WireCell/wcp-porting-validation/blob/main/fdvd_sim/docs/08a_duneopdet-light-simulation-bugs.md)
and propose fixes in the corresponding repos. Build and test in SL7. Push only to
this repo; no commit or push anywhere else, the human reviews. Test output under
`/exp/dune/data/users/yuhw/wire-cell-toolkit-ai-helper-workarea/issue-37`.

**Decisions (Haiwang, 2026-10-04).**
- Bug 1 (overlapping focus ranges): fixed **by default**, with a knob to restore the legacy behaviour.
- Bug 2 (per-event late-light reference): fix is **opt-in** (knob, legacy default). It is a physics-model choice for DUNE PDS simulation.
- `FocusList` moves to a shared header used by `WaveformDigitizerSim` only. The five other digitizer copies are documented here as follow-up (§5).

**Status (2026-10-05).** Proposal written, built and unit-tested in SL7, validated on 8
regenerated FD-VD events (§3, §4): all gates pass. Uncommitted, for review. A third bug
turned up during validation (§4.5); whether to add its fix is open.

## 1. Where the proposal lives

- Repo: DUNE/duneopdet, cloned at `/exp/dune/data/users/yuhw/duneopdet`. Local branch
  `fix-light-sim-pileup` off `origin/develop` (`608c633`, = tag `v10_26_00d02`).
  **Uncommitted** working-tree changes, not pushed.
- Both modules are unchanged between `v10_26_00d00` (the release doc 08a used) and
  `develop`. The two differ only in version strings (top-level `CMakeLists.txt`,
  `ups/product_deps`). The patch applies cleanly to both.
- Patch copy for review: [`duneopdet-fix-light-sim-pileup.patch`](duneopdet-fix-light-sim-pileup.patch).
  It covers 5 modified and 3 new files: about +50/-53 in the modules and fcl, plus a 116-line header and a 149-line test.

| file | change |
|---|---|
| `OpticalDetector/FocusList.h` (new) | `FocusList` + `Ranges_t` moved out of `WaveformDigitizerSim_module.cc`. `AddRange` keeps the ranges disjoint: the new range is merged with **every** range it overlaps, the union goes into the first overlapping range in list order (the one legacy extends), and the others are erased. Ranges are disjoint before each call, so one pass finds them all. Third constructor argument `mergeOverlaps` (default `true`); `false` runs the legacy loop unchanged. |
| `OpticalDetector/WaveformDigitizerSim_module.cc` | uses the header; new fhicl `MergeOverlappingRanges` (default `true`) passed to every `FocusList`. |
| `OpticalDetector/WaveformDigitizerSim.fcl` | `standard_daphne.MergeOverlappingRanges: true` (explicit, with a comment). |
| `OpticalDetector/SIPMOpSensorSim_module.cc` | new fhicl `LateLightReference`, `"Event"` (default, legacy) or `"Track"` (anything else throws at configuration). `"Track"`: the reference for each SDP is the first photon of the same `trackID` on that OpDet. The dead loop at legacy :270-274 (re-read element 0 every iteration) is replaced by a real minimum over the BTR. The map is time-sorted, so `"Event"` results are unchanged. |
| `OpticalDetector/SIPMOpSensorSim.fcl` | `xarapuca_ar_xe10ppm.LateLightReference: "Event"` with a comment. Inherited by `_ext` and the `dunefdvd_` variants. |
| `OpticalDetector/test/FocusList_test.cc`, `test/CMakeLists.txt` (new), `OpticalDetector/CMakeLists.txt` (`add_subdirectory(test)`) | Boost unit test of `FocusList` (`cet_test(... USE_BOOST_UNIT)`). duneopdet had no unit tests before. |

Design notes:
- **Bit compatibility of the bug 1 fix.** If the legacy loop never creates an
  overlap in an event, the fixed `AddRange` gives the identical range list in the
  identical order. Noise draws and stored waveforms are then bit-identical to
  legacy. The legacy list only changes once ranges overlap, and overlaps are never
  removed afterwards. So single-interaction samples (beam, solar-only) are mostly
  unchanged, and only the events that were actually corrupted change. Measured in §4.
- **"Touching" ranges are not merged.** Ranges are merged only if they share a sample, as in legacy.
  - The self-trigger's 20-tick pre-trigger can still re-read up to 20 samples of a neighbouring range.
  - That is the 0.08 % residual Xin saw. It is the readout model, not this bug.
- **Per track vs per interaction.** Doc 08a explains why per track is more generous than per interaction.
  - Each MARLEY track gets its own 10 ns window.
  - Untracked EM daughters carry `-parentID`, so they share one reference per parent.
  - An exact per-interaction reference needs the MCTruth grouping, which the module does not have.
  - `LateLightReference` is a string so that an `"Interaction"` mode can be added later.
- **RNG alignment.** `LateLightReference` changes only Poisson means, never the number of draws. `"Track"` and `"Event"` therefore consume the same random sequence.
- Knob names: `MergeOverlappingRanges` keeps Xin's fdvd08b name. `LateLightPerTrack` (fdvd08b) became `LateLightReference: "Track"`.

## 2. Build (SL7)

Scripts are in [`scripts/`](scripts/). Everything runs in
`fnal-dev-sl7:latest` via `scripts/in-sl7.sh`. The script binds `/cvmfs /exp /nashome`
and sets up `dunesw v10_26_00d00 -q e26:prof`; with `OPDEV=<mrb dir>` it also runs
`localProducts*/setup` and `mrbslp`.

    scripts/build-opdev.sh test      # mrb newDev v10_26_00d00 e26:prof in $WA/opdev; srcs/duneopdet = git worktree of
                                     # the clone at tag v10_26_00d00, proposal's duneopdet/ rsynced over; mrb i -j16; ctest

**Gate:** build rc=0, 0 compiler warnings (the project builds with `-Werror`; all
140 "warning" lines are CMake deprecation notices), `FocusList_test` passed
(1/1). About 1 min on dunebuild03.

Unit test coverage (`FocusList_test.cc`):
- padding and clipping at both ends;
- nested / extend-end / extend-front / disjoint: identical to legacy;
- an enclosing range is merged (legacy: appended, overlapping);
- a bridging range merges three ranges (legacy: overlap);
- touching ranges stay separate until a range bridges them;
- `everything()`;
- 2000 random pile-up trials with 325-tick pulses and 100-tick padding. The fixed ranges are always disjoint and cover exactly the padded pulses. In every trial where legacy stayed disjoint (both regimes are hit > 100 times), the fixed list equals the legacy list.

## 3. Test events

Xin's events live on his BNL disk, so they were regenerated here with his Stage A
seeds (`scripts/gen-events.sh` = `fdvd_sim/stageA/run_stageA.sh` steps 1-5, policy
`random`, `masterSeed = SEED0 + 10*idx + step`, dunesw `v10_26_00d00`):
- `sol` 0-3: MARLEY only;
- `mix` 0, 1, 2, 500: MARLEY + radiological decay0.

Per event: gen → g4 stage 1/2 → light-only detsim → light-only reco. A `mix`
event takes ~5 min, `g4s1` peaks at 6.2 GB RSS, and `reco.root` is 241 MB.

Each event was then rerun through the light detsim with 4 builds
(`scripts/run-rerun.sh <build> <s> <i>`). The rerun reads the kept
`OpDetBacktrackerRecords` from `reco.root` with the event's own detsim seed. It
then runs the official `ophit10ppm`, Xin's `dump_light_truth.py` (generator join)
and `scripts/light_bugs_metrics.py`. `scripts/summarize.py` → `$WA/summary.md`.

| build | duneopdet | knobs |
|---|---|---|
| `stock` | cvmfs `v10_26_00d00` | -- (control for the rerun mechanism) |
| `legacy` | proposal | `MergeOverlappingRanges: false`, `LateLightReference: "Event"` |
| `default` | proposal | its defaults: merge on, `"Event"` |
| `track` | proposal | merge on, `LateLightReference: "Track"` on `sipmAr10ppm{,Ext}` |

## 4. Results

Full tables: [`rerun-summary.md`](rerun-summary.md), produced by `scripts/summarize.py`. Totals are over the 4 events of each sample.

### 4.1 The regenerated events are Xin's events

The stock rerun of mix 0 / mix 500 has **15,028,912 / 14,910,646** samples stored
again and **31,755 / 31,970** snippets sharing a start tick. These are exactly the
doc 08a numbers. Sample-level fractions for the 4 mixed events:
- samples stored twice: 15.7 % (doc 08a, 1000 events: 15.7 %);
- duplicate hits: 12.3 % (12.4 %);
- duplicate PE: 15.8 % (16.0 %).

### 4.2 Gates

| gate | result |
|---|---|
| stock rerun == stored products (`raw::OpDetWaveform` and all 4 `OpDetDivRec`, FNV hash) | **8/8** |
| proposal with `MergeOverlappingRanges: false` == stored (the legacy knob is bit-for-bit) | **8/8** |
| proposal default: DivRecs == stored (`SIPMOpSensorSim` untouched by bug 1) | **8/8** |
| proposal default: waveforms == stored where legacy never overlapped (all 4 `sol`) | **4/4** |
| proposal default: duplicate OpHits | **0** in 7 events; 1 in mix 500, an artefact of finding 3 (§4.5), not an overlap |
| `"Track"`: Xe DivRecs == stored (only the Ar products change) | **8/8** |
| unit test | 1/1 |

### 4.3 Bug 1, mixed events (stock → proposal default)

| | stock (= legacy) | default (merge on) |
|---|---|---|
| snippets | 889,893 | 697,270 (−21.6 %) |
| samples stored | 376.6 M | 290.0 M |
| samples stored again | 59.2 M (15.7 %) | 0.21 M (0.07 %: the 20-tick pre-trigger re-reading a neighbouring range, as in Xin's 0.08 %) |
| of those, differing ADC | 0 | 0 |
| snippets sharing a start tick | 126,710 | **0** |
| OpHits | 51,978, of which 6,396 duplicates (12.3 %) | 43,806, **0** duplicates |
| OpHit PE | 1,348,666, of which 212,537 duplicated (15.8 %) | 1,083,572 |
| median pre-trigger RMS (first 15 samples of each snippet) [ADC] | **2.740** | **2.496** (solar-only: 2.544) |
| DivRec PE | 4,717,371 | 4,717,371 (identical products) |

- **Double line noise is now measured.** Doc 08a inferred it only from the code. With the
  fix, the median baseline RMS drops from 2.74 to 2.50 ADC, matching the solar-only events.
- **Offline de-duplication is not enough.** Even after dropping the duplicate hits, legacy
  still has more hits and PE than the fixed build:
  - 45,582 hits / 1,136,129 PE, against 43,806 / 1,083,572: **+4.1 % hits, +4.8 % PE**;
  - and 317.4 M unique samples against 290.0 M (+9.4 %).
  - This is consistent with the doubled noise firing the CFD and inflating pulses. The CFD threshold is a 15-ADC rise over 10 ticks. For a two-sample difference that is ~4.1σ at RMS 2.6 and ~2.9σ at 2.6·√2 = 3.7.
  - The mechanism is inferred; the excess is measured.
  - So `stageB/dedup_ophits.py` leaves a few-percent hit excess in the mixed sample.

### 4.4 Bug 2 (`LateLightReference`)

| | sol stock | sol `"Track"` | mix stock | mix `"Track"` | doc 08a (1000 mix / 20 sol) |
|---|---|---|---|---|---|
| MARLEY `sipmAr10ppm` PE / `PDFastSimAr` photon | 0.1845 | **0.2250** | 0.1319 | **0.2028** | sol 0.188 → 0.225; mix 0.136 → 0.214 |
| MARLEY total PE (Ar+Xe, all 4 products) | 2,374 | 2,508 (+5.6 %) | 2,067 | 2,283 (+10.4 %) | +4.7 % / +10.2 % |
| all PE in the mixed events | | | 4,717,371 | 5,690,757 (**+20.6 %**) | +20.6 % |

- Per track brings the mixed-event MARLEY Ar light from 71 % to 90 % of the solar-only value.
  - Stock: 0.132 / 0.185.
  - Track: 0.203 / 0.225, against 0.214 / 0.225 on 1000 events.
  - The remaining gap is within the 4-event statistics (a few hundred MARLEY Ar PE per sample).
- Xe products are bit-identical (no late-light scale there), and the RNG sequence is unchanged (§1).
- `"Track"` also removes duplicates and keeps the merge on. Its snippet and hit counts rise because there is more light.

### 4.5 Finding 3 (not in doc 08a): `CFDTrigger` start-tick underflow

- `CFDTrigger` sets `wstart = tick - fPreTrigger` with `size_t` arithmetic.
- A trigger in the first 20 ticks of the event window wraps `wstart` to ~2^64.
- The snippet is then stored with TimeStamp `Tick2us(2^64 - k)` = **2.95e17 µs**.
- `Digitize(begin + wstart, begin + wend + 1)` builds it from an iterator k samples *before* the waveform buffer.
  - That is an out-of-bounds read.
  - `Digitize` clamps values above the dynamic range in place, so it can also be an out-of-bounds write.
- Count in the stock output: **14, 12, 5, 8** snippets in mix 0, 1, 2, 500 (out of ~222k each); 0 in the solar-only events, whose light starts µs from t = 0.
- The ±4.25 ms radiological light reaches tick 0. The earliest normal snippet is at t0 = −4255.000 µs, i.e. exactly tick 20 − 20 = 0.
- These snippets give OpHits at 2.95e17 µs. Doc 08a's scripts silently drop them (`abs(TimeStamp) > 1e6`).
- At that magnitude the double ULP is 64 µs, so two different wrapped snippets on channel 71 of mix 500 give the "same" PeakTime. That is the one remaining duplicate in the default build.
- **Proposed fix (not yet in the patch, awaiting decision):** `wstart = tick >= fPreTrigger ? tick - fPreTrigger : 0`. `wend = tick - fPreTrigger + fReadoutWindow` is already correct under unsigned modular arithmetic. The fix changes only the wrapped snippets: their samples come from outside the buffer, so the legacy knob cannot be expected to reproduce them anyway.


## 5. Follow-up, not in this proposal

- **Five more copies of the same `AddRange`.** The legacy loop is copied verbatim into `OpDetDigitizerDUNE`,
  `OpDetDigitizerDUNEDP`, `OpDetDigitizerProtoDUNE`, `OpDetDigitizerProtoDUNEHD`
  and `OpDetDigitizerProtoDUNEVD` (`int` instead of `size_t`).
  - All of them loop over `fl.ranges` both in `AddLineNoise` and when cutting the stored waveforms.
  - In the ProtoDUNE-HD/VD digitizers this is the self-trigger (`DAPHNESelfTriggerSplit`) path for all non-full-streaming channels.
  - So the same overlap → duplicate-readout / double-noise mechanism applies wherever pulses pile up.
  - ProtoDUNE is a surface detector with heavy cosmic pile-up, so it may well be affected.
  - Not measured here. The fix would be to switch each to `FocusList.h`, which needs ProtoDUNE MC validation.
- **More duneopdet findings in other fdvd_sim docs**, outside doc 08a and not touched here:
  - `SIPMOpSensorSim::AddDarkNoise` generates dark-count times in µs and stores them as ns (doc 14 §6, doc 30 "bug 3");
  - Xin's doc 30 patch (`stageA/duneopdet_v10_26_00d00_doc30.patch`: `DarkNoiseTimeInNs`, `BinomialQE`, ProtoDUNE-HD/VD `FixSPEKey`, `FixDarkLoop`).
  - These could become a second proposal.
- **Upstream route.** The PR text for DUNE/duneopdet is for the human to write.
  - This doc and the patch can be appended to it, attributed to the model.
  - Note for reviewers: the bug 1 default changes FD-VD/HD MC outputs, but only in events with overlapping pulses.

## 6. Reproduce

    S=/exp/dune/data/users/yuhw/wire-cell-toolkit-ai-helper/issues/37-duneopdet-light-sim-bugs/scripts
    $S/build-opdev.sh test
    printf "sol 0\nsol 1\nsol 2\nsol 3\nmix 0\nmix 1\nmix 2\nmix 500\n" | xargs -P 8 -n 2 $S/gen-events.sh
    for c in stock legacy default track; do for e in "sol 0" "sol 1" "sol 2" "sol 3" "mix 0" "mix 1" "mix 2" "mix 500"; do echo $c $e; done; done \
      | xargs -P 8 -n 3 $S/run-rerun.sh
    python3 $S/summarize.py
