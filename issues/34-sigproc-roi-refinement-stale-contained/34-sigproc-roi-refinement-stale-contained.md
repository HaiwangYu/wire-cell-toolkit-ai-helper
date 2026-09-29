# Issue 34: sigproc ROI_refinement: stale `contained_rois` keys cause run-by-run non-determinism

GitHub: https://github.com/HaiwangYu/wire-cell-toolkit-ai-helper/issues/34.

**Ask (Haiwang, 2026-09-29).** Find sources of run-by-run non-determinism in `ROI_refinement` and `ROI_formation`. Write a failing test first, then fix.

Toolkit fix: branch `polaris-build-fixes`, commit `d2046242` (fork `HaiwangYu/wire-cell-toolkit`).

## The bug

`ROI_refinement::contained_rois` is a `std::map<SignalROI*, SignalROISelection>` (`SignalROI.h:53`). It maps each loose ROI, keyed by pointer, to the tight ROIs it contains.

`CleanUpInductionROIs(plane)` deletes the "fake" loose ROIs (`sigproc/src/ROI_refinement.cxx`). For each one it unlinks `front_rois` and `back_rois`, but it never erased the key from `contained_rois`. A bad loose ROI can still contain a tight ROI, because the fake-signal thresholds (`fake_signal_low_th`, `fake_signal_high_th` and the `*_ind_factor`s) are independent of `th_factor*rms`. So after U is refined, `contained_rois` holds keys that point to freed memory.

**How it reaches the V plane.** `OmnibusSigProc` refines U, V and W in sequence on the same `ROI_refinement` object (`OmnibusSigProc.cxx`, the second `for iplane` loop). Right after U's `CleanUpInductionROIs(0)`, the V loop runs `BreakROIs`, then `BreakROI1`, then `ShrinkROI`. These allocate many `SignalROI` objects of the same size as the ones just freed, so address reuse is very likely. A new V ROI that lands on a freed U address inherits the stale entry:

| where | effect |
|---|---|
| `BreakROI1`, `ShrinkROI` (the `contained_rois` update at the end) | `find(new_roi)` succeeds and `push_back`s onto the old list, so the V ROI "contains" U tight ROIs |
| `BreakROI` (`for ... contained_rois[roi]`) | copies those U tight ROIs' contents into the V waveform wherever the broken signal is zero |
| `CleanUpROIs` (`contained_rois.find(roi) != end`) | treats the V ROI as a "contains good stuff" seed, so it survives cleanup |
| `ShrinkROI` (the `// check tight ROIs` block) | uses U tight ranges as the shrink's inner boundary |

Whether reuse happens depends on the heap state of the running thread. Under TbbFlow, or with other threads active, that varies between runs, so V-plane ROIs, and everything downstream, can differ between runs even with identical input. Single-threaded Pgrapher mostly reproduces itself, but by luck.

`CleanUpCollectionROIs` had the same omission. It is harmless there, because W tight ROIs are never keys, but it is fixed too for consistency.

## Fix

Add `contained_rois.erase(roi);` before `delete roi;` in:
- `CleanUpInductionROIs`, plane-0 branch;
- `CleanUpInductionROIs`, plane-1 branch;
- `CleanUpCollectionROIs`.

Also add a read-only accessor, `const SignalROIMap& get_contained_rois() const` (`ROI_refinement.h`), so the map can be tested.

## Test

`sigproc/test/doctest_roi_refinement.cxx`, picked up automatically by `wcdoctest-sigproc`.

- **Setup:** one channel per plane, with an 11-tick triangular pulse (peak 100) and rms 10. The tight ROI is `[40,50]` and the loose ROI is `[30,60]`. Both survive `load_data` (> 3·rms), and each loose ROI contains its tight ROI. The fake-signal thresholds are 500/1000, so both loose ROIs are "bad".
- **Check:** after `CleanUpInductionROIs(0)`, and then `(1)`, every key in `contained_rois` must be a live loose ROI. The map size must be 1, then 0.
- **Why not test the output directly:** the check is on bookkeeping, not on the V-plane output. The visible symptom depends on the allocator reusing an address, so a test built on it would be flaky.

| | result |
|---|---|
| before the fix | 5 assertions failed: dead keys remain, and the size is 2 where 1 or 0 is expected. The setup preconditions passed. |
| after the fix | 11/11 assertions pass |

The runs used a standalone runner: the test plus `ROI_refinement`, `ROI_formation`, `SignalROI` and `PeakFinding`, compiled with the larsoft gcc v12_1_0 and the `build/compile_commands.json` flags, and linked to `build/util` and `build/iface`. The full `./wcb build` does not run on the bare Aurora host, because `root/dict` `rootcling` needs `libtinfo.so.5`. **TODO:** run `wcdoctest-sigproc` inside the container.

## Other findings from the audit (latent, not changed)

- `SignalROI::ext_start_bin` and `ext_end_bin` are uninitialized in both constructors. `apply_roi` uses them as unchecked Eigen indices. This is safe only because `ExtendROIs` always runs first.
- `BreakROI` has fixed arrays `valley_pos[205]`, `valley_pos1[205]` and `peak_pos1[205]`. They overflow the stack if `r_max_npeaks` is above ~202. The default is 200, and no cfg overrides it.
- `peak_pos1[0]` is read uninitialized in `LogDebug` when `npeaks1` is forced to 1. Only debug output is affected.

## Checked, deterministic

- **Pointer-keyed containers are only used for lookups, never iterated:** `front_rois`, `back_rois`, `contained_rois`, `Good_ROIs`, `ROIsaved_map` and `covered_tight_rois`. Neighbour lists are vectors, in insertion order.
- `PeakFinding`.
- The MP2/MP3 maps, which are int-keyed.
- `CheckROIs`.
- `ExtendROIs`, which sorts by start bin.
- All of `ROI_formation.cxx`: integer and `.at()` logic, `percentile`, and no pointer containers.

## Follow-up

- [ ] Run `wcdoctest-sigproc` inside the container.
- [ ] Check end to end: repeat a multithreaded SBND SP job N times, and V-plane `gauss`/`wiener` frames should be byte-identical (cf. #31).
