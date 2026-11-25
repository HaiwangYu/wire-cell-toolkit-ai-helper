# Issue 46: SBND YZ non-uniformity in the WCT simulation (data-driven YZ map)

Goal (owner, 2026-11-12): a WCT component that scales simulated depos (`IDepo`) by an external YZ map, a jsonnet based on `cfg/pgrapher/experiment/sbnd/wcls-sim-drift-depoflux-nf-sp.jsonnet` that uses it, a doctest, and a long single-muon fcl test. The work goes on a new WCT branch from master.

Input map (from its author): `/exp/sbnd/data/users/yuhw/YZ-non-uniformity/run_2_gen_2_BNBLight_data_v10_14_02_02_200usEast80usWest.root`
- `zy_<plane>_<tpc>`: median dQ/dx per YZ pixel; `CzyHist_<plane>_<tpc>`: correction factor that makes `zy` uniform; `zynhits_<plane>_<tpc>`: hits per pixel; `zydqdx`: ignore; `dqdxHist`: 1D dQ/dx per plane, in ADC/cm (axis title). Note (2026-11-24): `dqdxHist_<p>_0` and `_<p>_1` each hold East + West hits of the plane (entries = sum of both `zynhits`), so their index is not the TPC; `_1` is 0.5 % lower in median. A question for the map's author.
- plane 0 = U, 1 = V, 2 = Y (collection); tpc 0 = East, 1 = West.
- Every 2D map: 100 z bins × 80 y bins of 5 cm, z 0–500 cm, y −200–200 cm.
- Empty (C = 0) pixels: East V 52, East Y 80; none on the West.

## 1. Can one number per depo serve all three planes? (2026-11-12)

`scripts/compare_planes.py <map.root> <outdir> [min_hits=100]`. It compares g = 1/C (the relative response of a plane; data × C = uniform) between planes, using pixels with C > 0 on all three planes and ≥ 100 hits (East 7,798 of 8,000, West 8,000). Figures: `figs/planes_<TPC>.png` (maps, ratios, spread, scatter, ratio histograms), `figs/profiles_<TPC>.png` (z and y profiles), `figs/scales_<TPC>.png` (45 cm smoothed part and fine part). Numbers: `figs/plane_compare.json`.

| | East U | East V | East Y | West U | West V | West Y |
|---|---|---|---|---|---|---|
| rms of g (the plane's own non-uniformity) | 3.8 % | 4.3 % | 2.7 % | 2.6 % | 4.4 % | 2.4 % |
| g 5–95 % range | 0.94–1.05 | 0.93–1.06 | 0.97–1.04 | 0.97–1.03 | 0.92–1.06 | 0.97–1.03 |
| rms left if the **Y map** scales all planes | 3.9 % | 4.5 % | 0 | 2.9 % | 4.5 % | 0 |
| rms left if the **plane-average map** scales all planes | 2.4 % | 2.8 % | 2.3 % | 1.8 % | 2.7 % | 2.2 % |

| pixel-by-pixel | East | West |
|---|---|---|
| correlation U–Y / V–Y / U–V | 0.34 / 0.26 / 0.36 | 0.35 / 0.22 / 0.41 |
| g_U/g_Y: rms, pixels off by > 5 % | 3.9 %, 17 % | 2.9 %, 7 % |
| g_V/g_Y: rms, pixels off by > 5 % | 4.5 %, 24 % | 4.5 %, 26 % |
| (max − min)/mean over U, V, Y: median, 95 % | 4.5 %, 10.7 % | 3.9 %, 9.6 % |
| correlation of the 45 cm smoothed maps U–Y / V–Y | 0.38 / 0.31 | 0.44 / 0.25 |

Reading:
- **The planes differ as much as each plane varies.** Plane-to-plane differences (3–4.5 % rms) are as large as each plane's own non-uniformity (2.4–4.4 %), and the correlation between planes is weak (0.2–0.4).
- **The structure follows each plane's wires:** stripes along the U wire direction on U, at constant z (vertical) on Y, and on V both along the V wire direction and at constant z (variance fractions 0.16–0.17 vs 0.20–0.23; deck slide 15). That is channel- or wire-level response, different on each plane by construction. The large-scale (45 cm smoothed) parts are also only weakly correlated (0.25–0.5).
- **Shared features:** the z ≈ 250 cm line (the middle of the wire planes) and the corners and edges.
- **Y map for all planes:** it does nothing for U and V. Their residual rms gets slightly worse (East U 3.8 → 3.9 %, V 4.3 → 4.5 %).
- **Plane-average map for all planes:** it removes about a third of each plane's non-uniformity and gives Y about 2 % rms of non-uniformity it does not have.
- **Conclusion:** one factor per depo cannot reproduce the per-plane maps. Doing it right needs the factor per (plane, depo).

Implementation note: `DepoTransform` (`gen/src/DepoTransform.cxx:212`) already calls a virtual `modify_depo(WirePlaneId, depo)` for every plane before the depo enters that plane's `BinnedDiffusion` (the default returns the depo unchanged). A subclass that scales the charge by the plane's map gives per-plane scaling with no extra simulation cost. The ICARUS approach (master: `YZMap` + `Scaler` + `DepoSetScaler`, 360 per-plane pipelines) copies the depos for each plane instead.

### Summary deck of the map file (2026-11-24)

`docs/46-yz-map-file-summary.pdf` (23 slides; source `.tex`; figures and numbers from `scripts/make_deck_figs.py <map.root> docs/deck-figs`, numbers in `docs/deck-figs/deck_numbers.json`): the file and its variables (one slide per plane and TPC), coverage, how the map is used, the non-uniformity maps, numbers, profiles, stripes, edges, plane-to-plane, the overall data dQ/dx scale, the validation and the questions for the author.

- **Overall data scale (data only; the file has no MC):** pixel-median dQ/dx East/West U 1160/1175, V 1164/1156, Y 1121/1121 ADC/cm. Y is 3–4.6 % below U and V; West vs East +1.4 % (U), −0.7 % (V), 0.0 % (Y). The 1D peak of Y is 4.9–5.3 % below U and V.
- **Data vs MC:** open. It needs an MC version of the same histograms (owner's choice: data side only for now).
- **Questions for the author:** the unit of the 2D maps, the meaning of "200usEast80usWest", what the `_0`/`_1` index of `dqdxHist` is, an MC version, the outer-10 cm pixels, the event selection and run range, and `zydqdx`.

## 2. Implementation (owner's choice 2026-11-13: per plane, inside DepoTransform)

WCT branch `sbnd-yz-depo-scaling` from master 7710c43b, worktree `/exp/sbnd/app/users/yuhw/wct-yz`, installed to `/exp/sbnd/app/users/yuhw/opt-yz` (`scripts/build-wct-yz.sh configure|install|doctest`).

| commit | what |
|---|---|
| 26590c9e | `gen: DepoTransformYZ` + `YZMap` edge-clamp fix + doctest + converter |
| 6450d7ed | `cfg sbnd: wcls-sim-drift-depoflux-nf-sp-yzmap.jsonnet` |
| ca017a4d | `cfg sbnd: wcls-sim-drift-depoflux-nf-sp` ChannelSelector 5632 → 5638 |
| 6fdb9371 | `cfg sbnd: wcls-nf-sp` and `wcls-sim-drift-simchannel-nf-sp` ChannelSelector 5632 → 5638 (after the rebase; the three above are now 52062c35, da7e57f1, 31bc3e79) |

- **`Gen::DepoTransformYZ`** (`gen/{inc,src}/…DepoTransformYZ…`): a `DepoTransform` that overrides `modify_depo(WirePlaneId, depo)`. The hook runs for every depo and every plane before the depo enters that plane's `BinnedDiffusion`, so each plane gets its own factor at no extra cost.
  - Config: the `DepoTransform` keys plus `yzmap` (an `IYZMap` type:name, required) and `yzmap_key` (default: the `anode` type:name, the YZMap file convention).
  - `configure()` fails if the map has no non-zero value for a plane of the anode, so a wrong key cannot silently zero the charge.
  - SimChannels (`wclsDepoFluxWriter`, upstream of the transform) stay unscaled.
- **`YZMap` fixes:**
  - `value()` clamped an out-of-range bin to `nbins` instead of `nbins − 1`, reading one past the end of the grid. A depo at or beyond the upper y or z edge got garbage (doctest before the fix: `1.23659e-316`, then SIGSEGV). ICARUS's map files have exactly nbins per axis, so they hit the same bug.
  - `configure()` now checks that each grid is nbinsz × nbinsy and that the binning is positive.
- **Converter** `gen/test/convert-yzmap-sbnd.py <map.root> <out.json.bz2> [--factor inv-norm|inv] [--keys …]`:
  - factor 1/C. `inv-norm` (the default) scales it to mean 1 over the pixels with data, per plane and TPC; `inv` leaves it as is.
  - Output keys: `AnodePlane:apa0` = TPC 0 = East (x < 0), `AnodePlane:apa1` = West.
  - It prints the matching `YZMap` binning.
- **Map file:** `wire-cell-data/sbnd/sbnd-yzmap-run2-gen2-bnblight-v1.json.bz2` (80 KB, `inv-norm`; committed to WireCell/wire-cell-data master acbe8e5, 2026-11-24; it reproduces byte-identically from the ROOT file with the converter). YZMap binning: nbinsz 100, nbinsy 80, 5 cm × 5 cm, zoffset 0, yoffset 200 cm.
  - Factor rms per plane: East U 3.8 %, V 4.6 %, Y 2.7 %; West 2.6 %, 4.4 %, 2.4 %.
  - Range 0.42–1.68.
- **Note on map pixels (owner's choice: empty → 1, keep the rest):**
  - Pixels without data (C = 0: East V 52, East Y 80; mostly a V dead-channel diagonal and a Y dead-wire column) get factor 1, i.e. no YZ effect there. Dead channels themselves are the channel-status database's job, not the map's.
  - All other pixels are used as measured, including the edge and corner pixels where C reaches 1.7–2.4 (factor 0.42–0.6 before normalization). These are not low-statistics pixels: the 11–15 pixels per plane with C > 1.3 all lie in the outer 10 cm and have a median of 870–1,210 hits (correction 2026-11-24, deck slide 16). Low-hit pixels (< 100 hits: East U 9, V 64, Y 6; West none) have C 0.60–1.40; 53 of the 64 on East V touch the empty V diagonal.
  - If those edges look wrong in the sim, the converter is the place to cap or fill them.
- **jsonnet:**
  - `common/sim/nodes.jsonnet`: new `make_depotransform_yz`.
  - `sbnd/sim.jsonnet`: takes an optional `yzmap` argument; when given, it uses `DepoTransformYZ`.
  - New top-level `sbnd/wcls-sim-drift-depoflux-nf-sp-yzmap.jsonnet`: the toolkit's `wcls-sim-drift-depoflux-nf-sp.jsonnet` plus the YZMap service.
- **Two things about the toolkit copy of that jsonnet:**
  - It is older than sbndcode's (`sbndcode/WireCell/cfg`): it has no DNN ROI, no `tick0_time` SimChannel window, and a different `reference_time`. The test fcls therefore use the traditional-ROI `sbnd_wcls_simsp` with the outputers `postdrift`, `simdigits` and `spsaver`.
  - Its ChannelSelector used 5632 channels per anode, but the v0206 wires have 5638. The last 6 East collection channels went to the West NF/SP, and the last 12 West ones went nowhere. This is fixed in both files (sbndcode already uses 5638). `wcls-nf-sp.jsonnet` and `wcls-sim-drift-simchannel-nf-sp.jsonnet` are fixed too (6fdb9371, 2026-11-24); no SBND cfg in the toolkit uses 5632 now. sbndcode uses 5638 everywhere except the unused selector in `wcls-sim-drift-depoflux-nf-sp-samples_tru.jsonnet` (dead code). The Nov16 production ran none of the 5632 configs: step 1 (`img.jsonnet`) uses 5638 since toolkit 32852232 (2026-04-25).

## 3. Validation

### Doctest (`gen/test/doctest_depotransform_yz.cxx`, `scripts/run-doctest.sh`)

- **Cases:**
  - map lookups and edge clamp;
  - grid-size and binning checks;
  - per-plane scaling of one depo in each of two z bins (U, V, Y factors 0.5/1.5, 1.0/0.8, 2.0/1.25; measured per-plane |q| ratio equal within 1e-4);
  - two depos at once;
  - a unit map gives a frame identical to `DepoTransform`;
  - configure fails for a missing plane or key.
- The tests use a MicroBooNE anode under their own instance names (wires and field from wire-cell-data). The aux `Testing::anodes()` helper reconfigures shared instances, and with it the existing `empiricalnoisemodel shares spectra` test failed when run after these tests.
- **Before the `YZMap` fix:** `CHECK( 1.23659e-316 == 2 )`, then SIGSEGV (`logs/doctest-before-fix.log`).
- **After:** 5/5 cases, 412 assertions. The whole `wcdoctest-gen` passes 28/28 cases, 1,237 assertions.

### Long single muons (fcl)

- **Sample:** `scripts/fcl/gen_mu_long.fcl`, 10 events of a 5 GeV mu−:
  - starting at z = −5 cm, x uniform over ±180 cm, y uniform over ±120 cm;
  - direction +z, uniform ±20° in YZ and ±3° in XZ;
  - then `standard_g4_sbnd.fcl`. Output: `/exp/sbnd/data/users/yuhw/YZ-non-uniformity/mu-test/g4.root`.
- **Detsim:** `scripts/run-detsim.sh <dir> nominal|yzmap` with `scripts/fcl/detsim_wct_{nominal,yzmap}.fcl` (TPC only, RawDigits kept).
  - Both runs use the opt-yz build and the toolkit cfg, so only the jsonnet differs.
  - Each job runs in its own directory: art's MemoryTracker SQLite file fails with "disk I/O error" when two jobs share a directory on CephFS.
- **Check** (`scripts/compare_detsim.py`, then `scripts/plot_detsim.py`), per channel:
  - predicted factor = map value of the channel's plane and TPC, averaged over its SimChannel IDEs (weight: electrons);
  - measured = SP gauss charge, yz / nominal.

#### Result (2026-11-13)

- **Runs:** both passed, 10 events each, 5:11 wall, 1.9 GB peak RSS. The scaling costs no time.
- **Library caveat:** larwirecell in `opt` carries an RPATH to `opt/lib`, which wins over `LD_LIBRARY_PATH`. Inside `lar`, WCT therefore comes from `opt` (the first YZ-map attempt: "No factory for class DepoTransformYZ"). `run-detsim.sh` now `LD_PRELOAD`s the opt-yz WCT libraries (Util, Iface, Aux, Gen, SigProc, Root, Pgraph, Tbb, Pytorch) for both runs.
  - The header changes from opt's WCT (sbnd-wc-flatcaf) to master are additions.
  - `libWireCellLarsoft` uses none of the flat-CAF classes that master lacks; only AIML and QLMatch do, and detsim does not load them.
- **Compared:** 32,445 channel-events with SimChannel charge; 18,489 with ≥ 20,000 electrons and SP charge in both runs are used.
- **Figures:** `figs/detsim_scaling.png`; numbers in `figs/detsim_scaling.json`.

| | channels | predicted factor rms | measured/predicted − 1: median | rms | 5–95 % | corr(measured, predicted) | plane total measured / predicted |
|---|---|---|---|---|---|---|---|
| East U | 4150 | 3.5 % | −0.01 % | 2.2 % | −1.6 … +1.6 % | 0.83 | 0.9995 / 0.9997 |
| East V | 6298 | 3.8 % | −0.13 % | 3.0 % | −2.2 … +2.0 % | 0.74 | 1.0034 / 1.0050 |
| East Y | 2404 | 1.9 % | +0.00 % | 0.75 % | −0.6 … +0.5 % | 0.93 | 0.9972 / 0.9973 |
| West U | 2228 | 2.3 % | −0.01 % | 2.6 % | −1.3 … +1.2 % | 0.65 | 0.9988 / 0.9991 |
| West V | 2274 | 4.4 % | −0.10 % | 3.5 % | −2.6 … +1.9 % | 0.73 | 1.0002 / 1.0028 |
| West Y | 1135 | 1.8 % | +0.01 % | 0.49 % | −0.7 … +0.5 % | 0.96 | 0.9983 / 0.9985 |

- **The scaling works per plane.** On every plane and TPC the measured SP-charge ratio follows that plane's own map: the median deviation is ≤ 0.13 %, and the plane totals agree to ≤ 0.3 %.
- **Collection:** the ratio tracks the map within 0.5–0.75 % rms (correlation 0.93–0.96).
- **Induction:** 2–3.5 % rms, with a tail of outliers. Each run adds its own noise, and for a single muon the induction SP charge per channel is small and sensitive to ROI decisions. The 5–95 % band is still within ±2.6 %.
- **Lower correlation on West U** (0.65): the map varies little there (2.3 % rms), so the noise matters more.

### Rebase on master f604f815 (2026-11-24)

- `sbnd-yz-depo-scaling` rebased from 7710c43b onto `origin/master` f604f815 (26 commits). No conflicts: upstream touched none of our files, and `git range-diff` shows the 3 patches unchanged.
  - New SHAs: 52062c35 (gen), da7e57f1 (yzmap jsonnet), 31bc3e79 (5638 channels). The old tip is kept as local branch `sbnd-yz-depo-scaling-pre-rebase` (ca017a4d). The fork branch was force-pushed to 31bc3e79 (owner, 2026-11-24).
- **Build:** incremental install to `opt-yz`, no warnings. `WIRECELL_VERSION` in `opt-yz` still says 7710c43b, because it is stamped at configure time.
- **Doctests:** YZ 5/5 cases, 412 assertions. Whole `wcdoctest-gen`: 28/28 cases, 1,237 assertions.
- **ABI against opt's larwirecell:** every WireCell symbol that `libWireCellLarsoft`, the WCLS tool and module, AIML and QLMatch leave undefined is defined in `opt-yz` (0 missing; `logs/rebase-abi-check.log`).
- **Long muons:** the same `g4.root`, outputs in `mu-test/rebase-20261124/`. Nominal 4:55 and yzmap 4:56 wall, 1.9 GB peak RSS.
  - The per-channel comparison (`compare_detsim.tsv`) is byte-identical to the 2026-11-13 one, so the table above holds unchanged.
  - Figures: `figs/detsim_scaling_rebase.{png,json}`.

## 4. Hand-off kit for the map author (2026-11-24/25)

`yz-sim-kit/` (README = the step-by-step guide): the YZ scaling inside **sbndcode v10_14_02_03's standard detsim** (`standard_detsim_sbnd.fcl`, `simtpc2d` with DNN ROI), with one toggle `yz_scaling` off/on (`fcl/detsim_sbnd_yz_{off,on}.fcl`, `run-yz-detsim.sh --yz off|on [--reco1]`). Owner's choice: sbndcode config, not the older toolkit jsonnet.

- **Overlay:** `cfg/.../wcls-sim-drift-depoflux-nf-sp-yz.jsonnet` and `sim-yz.jsonnet`, copies of sbndcode's with the changes marked `YZ-KIT`. `sim-yz.jsonnet` carries its own `make_depotransform_yz`, because sbndcode's `pgrapher/common/sim/nodes.jsonnet` shadows the toolkit's.
- **Off = stock:** the compiled Wire-Cell config of off and of stock sbndcode is byte-identical (660,931 bytes; `scripts/check-config-identity.sh`). On differs only by `DepoTransform` → `DepoTransformYZ` (plus `yzmap`) and the `YZMap` service.
- **Environment:** sbndcode v10_14_02_03 + our larwirecell (`opt`) + the branch WCT (`opt-yz`), preloaded by **bare name** through `LD_LIBRARY_PATH`. The WCT libraries have no SONAME, so a full-path `LD_PRELOAD` (the old `scripts/run-detsim.sh`) still let RPATH pull `opt/lib/libWireCellApps.so` and second copies of Util/Iface/Aux/Mcs/Clus from `wct-yz/build`. The kit loads every WCT library once from `opt-yz`.
  - The kit does not use `setup-local-opt.sh`, whose local sbndcode cfg is not v10_14_02_03's.
  - Our install is world-readable (route A). Route B (build from the fork) was tested: 12 min, bit-identical output.
- **Long-muon validation** (the same 10 muons; `kit-validation/`): with DNN ROI the induction planes follow the map 2–3× more tightly than the toolkit config's traditional ROI.

| dnnsp | East U | East V | East Y | West U | West V | West Y |
|---|---|---|---|---|---|---|
| median measured/predicted − 1 | −0.00 % | −0.02 % | +0.00 % | −0.02 % | +0.01 % | −0.01 % |
| rms | 1.14 % | 1.17 % | 0.66 % | 1.13 % | 1.23 % | 0.68 % |
| correlation | 0.95 | 0.96 | 0.94 | 0.89 | 0.96 | 0.93 |

  `gauss`: Y the same (0.66–0.68 %); induction 1.9–3.9 % rms.
- **Cost:** `simtpc2d` takes 122.7 s per event both off and on (93 % of the event), and both use 6.4 GB max RSS. The scaling costs nothing measurable. That is 4.7× the toolkit config's 26 s, because of DNN ROI and both ROI methods.
- **Not bit-reproducible:** repeated runs of the same event split into two noise realizations, each bit-identical within itself. The signal agrees to 1e-4. A likely cause, not proven, is the two anode pipelines sharing one `Random` service in parallel. On/off comparisons have to use distributions, not single channels.
- **Test sample for the map author:** `/exp/sbnd/data/users/yuhw/YZ-non-uniformity/bnb-cv-10/g4.root`, 24 BNB CV-like events (GENIE BNB + CORSIKA, rockbox, sbndcode v10_14_02_03; README there).
- **Deck:** `docs/46-yz-sim-workflow.pdf` (workflow; results pending).

## Existing WCT pieces (master 7710c43b)

- `IYZMap` / `YZMap` (gen): service. JSON `{anode_name: {plane: [[z][y]]}}`, uniform binning (`bin_width` z, `bin_height` y, offsets, nbins). Its out-of-range clamp goes to `nbins` instead of `nbins − 1`, so an edge depo reads one past the end.
- `Scaler` (gen, `IDrifter`): one map value per depo for one (anode, plane). It drops depos outside the anode's sensitive volume.
- `DepoSetScaler` (gen, `IDepoSetFilter`): wraps a `Scaler`.
- `DepoSetFilterYZ` (gen): ICARUS per-response-region depo selection.

## Log

- 2026-11-12: issue opened; the map read and the planes compared (section 1).
- 2026-11-13: per plane in DepoTransform (owner); DepoTransformYZ, YZMap fix, doctest (fails before the fix, passes after), converter, jsonnet; app area at its 60 GiB quota stopped the build, so `wct-pr543/build` and `opt-pr543` were deleted (owner); muon sample made; detsim nominal vs yzmap on the opt-yz libraries (LD_PRELOAD): the per-channel SP charge ratio follows each plane's map (median ≤ 0.13 %, Y rms ≤ 0.75 %, induction 2–3.5 %).
- 2026-11-24: rebased on master f604f815, no conflicts, patches unchanged; rebuild, doctests 5/5 and 28/28, ABI check vs opt larwirecell clean, long-muon comparison byte-identical to 2026-11-13. Summary deck of the map file: `docs/46-yz-map-file-summary.pdf` (section 1); corrections: the high-C edge pixels are not low-hit, V stripes also at constant z, `dqdxHist` index is not the TPC.
- 2026-11-24: map committed to WireCell/wire-cell-data master (acbe8e5, owner's go); regenerated from the ROOT file, JSON identical.
- 2026-11-24: the other two toolkit SBND jsonnets with 5632 fixed on the branch (6fdb9371, pushed to the fork); wcsonnet: chsel0 0–5637, chsel1 5638–11275.
- 2026-11-24/25: hand-off kit `yz-sim-kit/` on the sbndcode v10_14_02_03 detsim with a toggle (off = stock, byte-identical config); long-muon check with DNN ROI; BNB CV-like 24-event G4 sample; draft workflow deck. Found: the old run-detsim.sh preload mixed WCT library copies; detsim is not bit-reproducible run to run.
