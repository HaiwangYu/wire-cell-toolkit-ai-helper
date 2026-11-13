# Issue 46: SBND YZ non-uniformity in the WCT simulation (data-driven YZ map)

Goal (owner, 2026-11-12): a WCT component that scales simulated depos (`IDepo`) by an external YZ map, a jsonnet based on `cfg/pgrapher/experiment/sbnd/wcls-sim-drift-depoflux-nf-sp.jsonnet` that uses it, a doctest, and a long single-muon fcl test. The work goes on a new WCT branch from master.

Input map (from its author): `/exp/sbnd/data/users/yuhw/YZ-non-uniformity/run_2_gen_2_BNBLight_data_v10_14_02_02_200usEast80usWest.root`
- `zy_<plane>_<tpc>`: raw dQ/dx per YZ pixel; `CzyHist_<plane>_<tpc>`: correction factor that makes `zy` uniform; `zynhits_<plane>_<tpc>`: hits per pixel; `zydqdx`: ignore; `dqdxHist`: 1D dQ/dx per plane.
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
- **The structure follows each plane's wires:** stripes along the U wire direction on U, along the V wire direction on V, and at constant z (vertical) on Y. That is channel- or wire-level response, different on each plane by construction. The large-scale (45 cm smoothed) parts are also only weakly correlated (0.25–0.5).
- **Shared features:** the z ≈ 250 cm line (the middle of the wire planes) and the corners and edges.
- **Y map for all planes:** it does nothing for U and V. Their residual rms gets slightly worse (East U 3.8 → 3.9 %, V 4.3 → 4.5 %).
- **Plane-average map for all planes:** it removes about a third of each plane's non-uniformity and gives Y about 2 % rms of non-uniformity it does not have.
- **Conclusion:** one factor per depo cannot reproduce the per-plane maps. Doing it right needs the factor per (plane, depo).

Implementation note: `DepoTransform` (`gen/src/DepoTransform.cxx:212`) already calls a virtual `modify_depo(WirePlaneId, depo)` for every plane before the depo enters that plane's `BinnedDiffusion` (the default returns the depo unchanged). A subclass that scales the charge by the plane's map gives per-plane scaling with no extra simulation cost. The ICARUS approach (master: `YZMap` + `Scaler` + `DepoSetScaler`, 360 per-plane pipelines) copies the depos for each plane instead.

## 2. Implementation (owner's choice 2026-11-13: per plane, inside DepoTransform)

WCT branch `sbnd-yz-depo-scaling` from master 7710c43b, worktree `/exp/sbnd/app/users/yuhw/wct-yz`, installed to `/exp/sbnd/app/users/yuhw/opt-yz` (`scripts/build-wct-yz.sh configure|install|doctest`).

| commit | what |
|---|---|
| 26590c9e | `gen: DepoTransformYZ` + `YZMap` edge-clamp fix + doctest + converter |
| 6450d7ed | `cfg sbnd: wcls-sim-drift-depoflux-nf-sp-yzmap.jsonnet` |
| ca017a4d | `cfg sbnd: wcls-sim-drift-depoflux-nf-sp` ChannelSelector 5632 → 5638 |

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
- **Map file:** `wire-cell-data/sbnd/sbnd-yzmap-run2-gen2-bnblight-v1.json.bz2` (80 KB, `inv-norm`, not committed to wire-cell-data yet). YZMap binning: nbinsz 100, nbinsy 80, 5 cm × 5 cm, zoffset 0, yoffset 200 cm.
  - Factor rms per plane: East U 3.8 %, V 4.6 %, Y 2.7 %; West 2.6 %, 4.4 %, 2.4 %.
  - Range 0.42–1.68.
- **Note on map pixels (owner's choice: empty → 1, keep the rest):**
  - Pixels without data (C = 0: East V 52, East Y 80; mostly a V dead-channel diagonal and a Y dead-wire column) get factor 1, i.e. no YZ effect there. Dead channels themselves are the channel-status database's job, not the map's.
  - All other pixels are used as measured, including edge and corner pixels with few hits, where C reaches 1.9–2.4 (factor 0.42–0.5 before normalization). Low-hit pixels (< 100 hits): East U 9, V 64, Y 6; West none.
  - If those edges look wrong in the sim, the converter is the place to cap or fill them.
- **jsonnet:**
  - `common/sim/nodes.jsonnet`: new `make_depotransform_yz`.
  - `sbnd/sim.jsonnet`: takes an optional `yzmap` argument; when given, it uses `DepoTransformYZ`.
  - New top-level `sbnd/wcls-sim-drift-depoflux-nf-sp-yzmap.jsonnet`: the toolkit's `wcls-sim-drift-depoflux-nf-sp.jsonnet` plus the YZMap service.
- **Two things about the toolkit copy of that jsonnet:**
  - It is older than sbndcode's (`sbndcode/WireCell/cfg`): it has no DNN ROI, no `tick0_time` SimChannel window, and a different `reference_time`. The test fcls therefore use the traditional-ROI `sbnd_wcls_simsp` with the outputers `postdrift`, `simdigits` and `spsaver`.
  - Its ChannelSelector used 5632 channels per anode, but the v0206 wires have 5638. The last 6 East collection channels went to the West NF/SP, and the last 12 West ones went nowhere. This is fixed in both files (sbndcode already uses 5638). `wcls-nf-sp.jsonnet` and `wcls-sim-drift-simchannel-nf-sp.jsonnet` still have 5632.

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

## Existing WCT pieces (master 7710c43b)

- `IYZMap` / `YZMap` (gen): service. JSON `{anode_name: {plane: [[z][y]]}}`, uniform binning (`bin_width` z, `bin_height` y, offsets, nbins). Its out-of-range clamp goes to `nbins` instead of `nbins − 1`, so an edge depo reads one past the end.
- `Scaler` (gen, `IDrifter`): one map value per depo for one (anode, plane). It drops depos outside the anode's sensitive volume.
- `DepoSetScaler` (gen, `IDepoSetFilter`): wraps a `Scaler`.
- `DepoSetFilterYZ` (gen): ICARUS per-response-region depo selection.

## Log

- 2026-11-12: issue opened; the map read and the planes compared (section 1).
- 2026-11-13: per plane in DepoTransform (owner); DepoTransformYZ, YZMap fix, doctest (fails before the fix, passes after), converter, jsonnet; app area at its 60 GiB quota stopped the build, so `wct-pr543/build` and `opt-pr543` were deleted (owner); muon sample made; detsim nominal vs yzmap on the opt-yz libraries (LD_PRELOAD): the per-channel SP charge ratio follows each plane's map (median ≤ 0.13 %, Y rms ≤ 0.75 %, induction 2–3.5 %).
