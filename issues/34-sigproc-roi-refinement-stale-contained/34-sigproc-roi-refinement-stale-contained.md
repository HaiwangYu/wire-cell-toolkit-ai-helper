# Issue 34: sigproc ROI_refinement: stale `contained_rois` keys cause run-by-run non-determinism

GitHub: https://github.com/HaiwangYu/wire-cell-toolkit-ai-helper/issues/34.

**Ask (Haiwang, 2026-09-29).** Find sources of run-by-run non-determinism in `ROI_refinement` and `ROI_formation`. Write a failing test first, then fix.

Toolkit fix: branch `polaris-build-fixes` (fork `HaiwangYu/wire-cell-toolkit`). The fix is now **Xin's upstream `634fa688` + `af696a11`**, cherry-picked as `0beaed8a` + `17233155`. Our first version, `d2046242`, is reverted by `2ecb6645`. See section 2026-09-30 (c).

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

- [x] Run `wcdoctest-sigproc` inside the container (2026-09-29 (b), below).
- [ ] Check end to end: repeat a multithreaded SBND SP job N times, and V-plane `gauss`/`wiener` frames should be byte-identical (cf. #31).

## 2026-09-29 (b): Aurora build and test (procedure `docs/sbnd-1step-build-run-validate.md`, Aurora port #29)

- **First build failed (job 8878913).** Earlier the same day, `./wcb build` had been run on the login node, outside the container. That left host-toolchain objects in `build/` that the SL7 `ld` cannot read (`util/src/Array.cxx.3.o: file format not recognized`). The deployed `opt/lib` was untouched (all files from 09-26). Repair, per section 1 (`rm -rf build`): back up `opt/{lib,bin,include,share}` to `production-prep/opt-backup-i34-20260929` (1.7 GB), then do a clean rebuild. **Never run `wcb` on the UAN.**
- **Clean build (job 8878953, `CLEAN=1 STAGES=wct DO_CFG_GATE=0`):** WCT `d2046242` (`0.35.0-1720-gd2046242`). Configure took 2m16s and `wcb install -j96` 3m30s.
  - Every section-1 gate passes: `WCB_RC=0`, `nlibs=19` incl. Mcs, `single_threaded_syms=0`, `fmt_needed=0`, `rpath_stripped=20`, `ldd_not_found=0`.
  - larwirecell was not rebuilt: the change is a private sigproc header, so the ABI is unchanged.
  - Relative to the previous `opt`, the only code change is this fix. `2982785a..d2046242` also carries the #33 clus/root changes, but those were already deployed.
- **Unit test (job 8879000, `scripts/doctest-sigproc.pbs`, SL7 container):**
  - `ROI_refinement CleanUpInductionROIs drops deleted ROIs from contained_rois` is registered, and 11/11 assertions pass (`ROI_TEST_RC=0`).
  - The full sigproc suite gives 12/13 passed and 16429/16429 assertions. The one failure is a SIGSEGV in `doctest_l1sp_kernel.cxx:130`, `L1SPFilterPD dump-mode emits documented NPZ schema`. It is pre-existing, from upstream `ae430137`, and environmental: the test hard-codes `dump_path=/home/xqian/tmp/...`, which does not exist on Aurora. It is also unrelated to this fix, because `L1SPFilterPD` does not use `ROI_refinement`; only `OmnibusSigProc` does.
  - `deployed_lib_eq_build=NO` is expected. Section 1a patchelf-strips the RPATH of the `opt` copy. The `.text` md5 is identical, and only 707 RPATH bytes differ.
- **Workflow check: MC-9 1-step (job 8879028, `smoke.pbs`, the same RECO1 and `wcls-img-clus-matching-xin-hits.fcl` as `mc50-1step-m34`), run dir `production-prep/mc50-1step-i34-20260929-1829`:**
  - 9/9 `rc=0`, `audit=ok`, `dl_vertex_failed=0`. There are 12 trees (with `T_truth_*`) where there is a candidate, and 10 elsewhere.
  - Compared with `mc50-1step-m34-20260929-0607` (job 8879081, `compare-1step.pbs`): `deep_compare` exact 9/9, branch census 0 differing pairs, Bee identical 9/9, `T_truth_*` rows the same.
  - **Caveat:** the 1-step chain has **no SP stage**. It reads the reco1 `simtpc2d` wires, so `ROI_refinement` never runs in it. This is a no-regression check of the rebuild, not a test of the fix.
- **Relation to #31:** the example flip there, RSE 1/16/2, is on ch 342. SBND has 1984 U + 1984 V + 1664 W channels per TPC, so ch 342 is a **U**-plane channel. This bug only affects **V**: the stale keys are created when U ROIs are deleted, and only V-plane allocations can reuse those addresses. So it cannot explain that flip, and #31 must also have another cause (FP / thread order). The #31 V-plane differences would have to be checked channel by channel to see whether any are consistent with this bug.

Follow-up (still open): an SP-level check. Run the detsim SP job (`wcls-sim-drift-depoflux-nf-sp.jsonnet`, as in #31) N times with `$Y/opt`, multithreaded, before and after the fix, and compare V-plane gauss/wiener frames byte for byte.

## 2026-09-30 (c): adopted Xin's upstream fix; rebuild and doctest

Xin fixed the same bug upstream, on `origin/apply-pointcloud`:
- `634fa688` adds the OmnibusSigProc knob `r_erase_stale_contained`, which erases the key in both induction branches of `CleanUpInductionROIs`. It also adds the doctest `doctest_roi_refinement_stale_keys.cxx`.
- `af696a11` switches the knob's default to **true**.

Compared with our `d2046242`: the same root cause and the same two erase sites, and the same `get_contained_rois()` accessor. Ours also erased the key in `CleanUpCollectionROIs`, where it is harmless because W ROIs are never keys, so dropping it changes nothing.

Xin's SBND DetSim measurement:

| | legacy | fixed |
|---|---|---|
| events non-deterministic on V only (6 repeats) | 8/10 | 0/10 |
| stale U keys per event | 11-14 k | 0 |
| V address reuses per event | 470-2000 | 0 |

- The fixed output equals the majority state of the legacy runs.
- PDHD and PDVD NF+SP are byte-identical with the fix.
- This closes our open "SP-level check" follow-up.

To keep the upstream merge conflict-free, `polaris-build-fixes` now reverts ours (`2ecb6645`) and cherry-picks both of Xin's commits with `-x` (`0beaed8a`, `17233155`), pushed to the fork. The five touched sigproc files are byte-identical to `origin/apply-pointcloud`. Our `doctest_roi_refinement.cxx` went out with the revert; Xin's test covers the same case, plus the legacy path and the default.

Build and test on Aurora:
- **Rebuild (job 8879407, `STAGES=wct`, incremental):** `0.35.0-1723-g17233155`. `WCB_RC=0`, `nlibs=19`, `single_threaded_syms=0`, `fmt_needed=0`, `ldd_not_found=0`. `rpath_stripped=1`, because only `libWireCellSigProc.so` was reinstalled.
- **Doctest (job 8879470, `scripts/doctest-sigproc.pbs`, SL7):**
  - The deployed lib's `.text` equals the build's (`e0f7b7d4`). The check now compares `.text`, since the section-1a RPATH strip always changes the file.
  - Both of Xin's cases are registered and pass: `ROI_refinement CleanUpInductionROIs contained_rois stale keys` and `OmnibusSigProc r_erase_stale_contained defaults to true` (2/2 cases, 10/10 assertions).
  - The full suite is unchanged from (b): 12/13 cases and 16429/16429 assertions. The one failure is the pre-existing `L1SPFilterPD dump-mode` SIGSEGV (hard-coded `/home/xqian/tmp`).
- `$Y/opt` now matches HEAD `17233155`.
- A 1-step re-run is not needed: the 1-step chain has no SP stage, and (b) already showed it exact after the fix.
- The scripts `after-build-doctest.sh` (a detached UAN watcher: the debug queue allows 1 queued job per user, so `-W depend` is refused) and `doctest-sigproc.pbs` are in `scripts/`.
