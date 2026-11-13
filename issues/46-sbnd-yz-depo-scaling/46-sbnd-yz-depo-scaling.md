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

## Existing WCT pieces (master 7710c43b)

- `IYZMap` / `YZMap` (gen): service. JSON `{anode_name: {plane: [[z][y]]}}`, uniform binning (`bin_width` z, `bin_height` y, offsets, nbins). Its out-of-range clamp goes to `nbins` instead of `nbins − 1`, so an edge depo reads one past the end.
- `Scaler` (gen, `IDrifter`): one map value per depo for one (anode, plane). It drops depos outside the anode's sensitive volume.
- `DepoSetScaler` (gen, `IDepoSetFilter`): wraps a `Scaler`.
- `DepoSetFilterYZ` (gen): ICARUS per-response-region depo selection.

## Log

- 2026-11-12: issue opened; the map read and the planes compared (section 1).
