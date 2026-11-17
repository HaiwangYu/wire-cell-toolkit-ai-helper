<!-- survey of /exp/sbnd/app/users/yuhw/wcp (WCP prototype), read-only, 2026-11-17; file:line refs are into that checkout -->
# WCP (MicroBooNE) effective boundary survey for an SBND port

The boundary is not a box. It is two 6-vertex polygons, one in x–y and one in x–z, and a point is inside only if it is inside both. There are two versions: a single "FV" polygon pair, and a "SCB" (space-charge boundary) pair that changes with z or y bin. I modified nothing.

File keys used below:
- **P** = `/exp/sbnd/app/users/yuhw/wcp/pid/src/ToyFiducial.cxx`
- **H** = `/exp/sbnd/app/users/yuhw/wcp/pid/inc/WCPPID/ToyFiducial.h`
- **C** = `/exp/sbnd/app/users/yuhw/wcp/pid/src/Cosmic_tagger.h` (included into P at P:19; it holds `check_tgm`, `check_boundary`, `glm_tagger`, M2, …)
- **T** = `/exp/sbnd/app/users/yuhw/wcp/2dtoy/src/ToyFiducial.cxx`
- **N** = `/exp/sbnd/app/users/yuhw/wcp/pid/src/NeutrinoID_*.h`

`pid/docs/ToyFiducial.md` is only a summary and adds nothing numeric.

## 1. How the boundary is represented

**Constructor** (H:25-26, P:32):
```cpp
ToyFiducial(int dead_region_ch_ext=3, double offset_t=800, double offset_u=0, offset_v=0, offset_w=0,
  slope_t=1./2*units::mm, slope_u=slope_v=slope_w=1./(3*units::mm), angle_u=-1.047198, angle_v=1.047198, angle_w=0,
  double boundary_dis_cut=2*units::cm, top=117*cm, bottom=-116*cm, upstream=0*cm, downstream=1037*cm,
  anode=0*cm, cathode=256*cm, int flag_data=1);
```
`m_cathode` is stored but never used in any polygon. The cathode x is hard-coded as 256 cm everywhere.

**(a) FV polygons**: `boundary_xy_{x,y}` and `boundary_xz_{x,z}` (P:117-136). Here `d` = `boundary_dis_cut`.
- **x–y polygon**, in order: (anode+d, bottom+d), (sc_bot_1_x−d, sc_bot_1_y+d), (sc_bot_2_x−d, sc_bot_2_y+d), (sc_top_2_x−d, sc_top_2_y−d), (sc_top_1_x−d, sc_top_1_y−d), (anode+d, top−d).
- **x–z polygon**: the same pattern with the upstream/downstream SC points. There is an extra ±1 cm in z (P:131-136).

Space-charge corner values, as (x, y or z) in cm:

| Corner | Data (P:64-86) | MC (P:90-112) |
|---|---|---|
| bottom_1 | (80, −116) | (34, −116) |
| bottom_2 | (256, −99) | (256, −98) |
| top_1 | (100, 116) | (70, 116) |
| top_2 | (256, 102) | (256, 100) |
| upstream_1 | (120, z=0) | (50, 0) |
| upstream_2 | (256, z=11) | (256, 14) |
| downstream_1 | (120, z=1037) | (40, 1037) |
| downstream_2 | (256, z=1026) | (256, 1023) |

With the production `d = 3 cm`, the resulting polygons are:
- **Data x–y:** (3,−113), (77,−113), (253,−96), (253,99), (97,113), (3,114)
- **Data x–z:** (3,4), (117,4), (253,15), (253,1022), (117,1033), (3,1033)

**(b) SCB polygons, binned**: `boundary_SCB_xy_*_array[index_z]` and `boundary_SCB_xz_*_array[index_y]`, 10 bins each, with no `d` applied (P:143-216). The values are the same for data and MC. All in cm:
```
YX_TOP_y1 = 116;  YX_TOP_x2 = 256
YX_TOP_x1[10] = {150.00,132.56,122.86,119.46,114.22,110.90,115.85,113.48,126.36,144.21}
YX_TOP_y2[10] = {110.00,108.14,106.77,105.30,103.40,102.18,101.76,102.27,102.75,105.10}
YX_BOT_y1 = -115; YX_BOT_x2 = 256
YX_BOT_x1[10] = {115.71,98.05,92.42,91.14,92.25,85.38,78.19,74.46,78.86,108.90}
YX_BOT_y2[10] = {-101.72,-99.46,-99.51,-100.43,-99.55,-98.56,-98.00,-98.30,-99.32,-104.20}
ZX_Up: z1=0,x1=120; z2=11,x2=256  (not binned)
ZX_Dw_z1 = 1037; ZX_Dw_x2 = 256
ZX_Dw_x1[10] = {120.00,115.24,108.50,110.67,120.90,126.43,140.51,157.15,120.00,120.00}
ZX_Dw_z2[10] = {1029.00,1029.12,1027.21,1026.01,1024.91,1025.27,1025.32,1027.61,1026.00,1026.00}
```
- **x–y vertices per bin:** (anode, bottom), (BOT_x1[i], −115), (256, BOT_y2[i]), (256, TOP_y2[i]), (TOP_x1[i], 116), (anode, top) (P:204-209).
- **x–z vertices per bin:** (anode, up+1), (120, 1), (256, 12), (256, Dw_z2[i]−1), (Dw_x1[i], 1036), (anode, down−1) (P:211-216).
- **Bin indices:** `index_z = floor(z/m)` and `index_y = floor((y/cm+116)/24)`, both clamped to 0..9 (P:1747-1750, H:48-67).
- `boundary_xy_x_array` / `xz` (the binned arrays with `d` applied, P:190-202) are built but **never used**. The call that would use them is commented out (P:1752-1753).

**(c) M2 copies** (P:222-272): the same numbers stored 1-indexed in `SCB_YX_TOP/BOT_*` and `SCB_ZX_TOP/BOT_*[11]`.

**Space charge:** there is no runtime space-charge map. The SC effect is entirely in these hand-tuned vertices: the cathode-side corners are pulled toward the anode.

## 2. The point tests

**`inside_fiducial_volume(Point& p, double offset_x=0, vector<double>* tol=NULL)`** (P:1743-1805)
- Runs `pnpoly` (P:7-16, even–odd ray casting) twice: on (p.x−offset_x, p.y) against the x–y polygon and on (p.x−offset_x, p.z) against the x–z polygon. Returns `c1 && c2`.
- With `tol == NULL`, it uses the flat FV polygons (P:1754-1755).
- With `tol` given, it uses the binned SCB polygons. `tol = {x_anode, x_cathode, y_bot, y_top, z}`, and a positive value enlarges the volume. The function temporarily edits the member arrays and then reverts them (P:1757-1795), so it is not thread-safe or const.
  - Only the anode-side and cathode-side x values move. The x values of the SC kink vertices (1 and 4) are not shifted.
- The 2dtoy version takes a 4-element `{x, ybot, ytop, z}` and never shifts the anode side (T:1702-1763).
- There is no drift-window or time check inside this function. Time enters only through `offset_x`.

**`check_boundary(extreme_pts, offset_x, tol)`** (C:613-639)
- Returns −1 if any extreme point is outside the polygon enlarged by +tol.
- Otherwise it counts the PCA ends (0 and 1) that lie outside the polygon shrunk by −tol, i.e. points within ±tol of the boundary. Return values: 1 = STM-like, 2 = TGM-like.
- **Bug:** `neg_tol_vec` points to a local vector declared inside the `if` block (C:622-626), so it is a dangling pointer when used at C:631.

**`inside_x_region(extreme_pts, offset_x, x_low, x_high)`** (C:364-371): tests only the x of the two PCA ends, with limits given in cm.

**`inside1_outside0_SCB(p, offset_x, tx, ty, tz)`** (M2 version, C:2078-2150)
- Rebuilds the SCB polygons with a margin `space = tol·cm` (a positive value shrinks the volume).
- **Bug:** `space_yy` and `space_zz` both use `tolerence_x` (C:2085-2086).
- Bins: `index_z = int(z/100cm)+1`; `index_y = int((y+116)/24)+1`.

**`M2_offset_YX_x(p)`** (C:2009-2074): the x-distance from p to the cathode-side SCB edge in x–y. Used as a "no-flash" drift shift.

**`check_dead_volume(p, dir, step=1cm, offset_x)`** (P:1703-1739)
- Steps from p along `dir` while the point stays in the FV.
- Returns true once 4 or more live steps are found.
- Returns false if more than 81% of the steps are in `inside_dead_region`.

**`check_signal_processing`** (P:1655-1701)
- Same stepping. A step counts as "dead" if any U/V/W 2D hit lies within 1.2 cm, or if the point is in a dead region.
- Returns true at 5 or more good steps, and false if dead > 0.8·total.

**`inside_dead_region(p)`** (P:1807-1866)
- Converts the point to (time slice, U/V/W channel) using `offset_*`, `slope_*` and `angle_*`.
- Channel ranges are hard-coded: 0–2399, 2400–4799, 4800–8255; time slices < 2398.
- Requires 2 of the 3 planes to share a dead `mcell` and the time slice to fall inside that cell's window.
- Dead cells come from `AddDeadRegion` (P:1869), with a ±3 channel/tick extension.

**Close-to-anode tests:**
- `x < 2 cm` and kink `x < 6 cm` (P:760-761, 915-916; C:1067-1068, 3321-3322). These use the raw x of the fine-tracking path, with no offset subtracted.
- `dist2anode_cut = 2 cm` (C:2371/2400, 2607/2627).

## 3. Consumers and the tolerances they pass

- **`check_tgm`** (C:1331-…): requires extreme points of two different groups to be outside the FV with `tol=NULL`, and at least one interpolated midpoint inside (C:1406-1411). If the flash type is 2, it also requires `!check_neutrino_candidate` and length > 0.45 × max. Otherwise it falls back to `check_signal_processing` / `check_dead_volume` (C:1525-1561).
- **`check_neutrino_candidate`** (C:1677-1985): kink points must be inside the FV (`tol=NULL`) and not in a dead region (C:1806, 1942, 1965).
- **`check_fully_contained`** (C:646-713): every extreme point must be in the FV (`tol=NULL`). For directions near the wire planes (U/V < 10°, W < 5°) it adds `check_signal_processing`; for angle > 60° it adds `check_dead_volume`.
- **`check_stm` / `check_stm_only` / `M2_check_stm`** (P:405-1020, C:717-…, C:2975-…): an exit candidate is an extreme point outside the FV (`tol=NULL`) or one that fails the signal-processing or dead-volume test (P:456-499). They also run a TGM sub-check with both ends outside the FV (P:756).
- **`glm_tagger`** (C:2-342). Tolerance vectors are `{x_ano, x_cat, ybot, ytop, z}` in cm:
  - Fully contained: `stm_tol = {0.0, 2.0, 2.0, 2.5, 2.0}`, `tgm_tol = {2.2, 2.8, 2.8, 2.8, 2.8}`, `tgm_nof_tol = {0.8, 1.2, 1.2, 1.2, 1.2}` (C:34-36).
  - Not fully contained: `stm_tol = {0, 1.5, 1.5, 2.0, 1.5}`, `tgm_tol = {2.0, 2.5, 2.5, 2.5, 2.5}`, `tgm_nof_tol = {0.6, 0.9, 0.9, 0.9, 0.9}` (C:64-66).
  - Tolerances are scaled ×1.3 (or ×1.3²) when `ks/ks_tol` > 2 or 3 (C:147, 161-162, 184).
  - Flash pre-cut: `inside_x_region(0−tgm_tol[0], 256+tgm_tol[1])`. STM requires `cathode_side = inside_x_region(128−…, 256+…)` (C:100, 154).
  - "TGM without flash" (C:181-311): slides x until an end touches the cathode-side SCB edge (using `get_boundary_SCB_*`), or aligns with the anode, then calls `check_boundary`.
- **`M2_cosmic_tagger`** (C:2153-2730):
  - Uses `tolerence = 2 cm` for x, y and z throughout (C:2381-2383, 2483-2485, 2603-2605).
  - The "touches the boundary" test is: outside the shrunk SCB and inside the enlarged SCB, for both ends (TGM) or one end (STM). It then requires every cluster point to be inside the enlarged SCB.
  - The no-flash variant uses `M2_offset_YX_x` as `offset_x`.
- **NeutrinoID / BDT variables:**
  - Vertex-in-FV test `cosmict_1` uses `stm_tol_vec = {−1.5 cm × 5}`, i.e. SCB shrunk by 1.5 cm (`NeutrinoID_cosmic_tagger.h:32-35`). The same vector appears in `NeutrinoID_nue_tagger.h:504/511, 1248-1249` and `NeutrinoID_singlephoton_tagger.h:783-790, 1527-1528`.
  - `tol=NULL` FV tests: `cosmict_*` at `NeutrinoID_cosmic_tagger.h:117, 179, 227, 248, 438, 457, 500, 569`; `cosmict_10` (z < 15 cm) at :803/821; `br3_2_other_fid` at `NeutrinoID_nue_tagger.h:3230`; and `NeutrinoID_track_shower.h:1653, 2217`.
- **Apps:**
  - `/exp/sbnd/app/users/yuhw/wcp/pid/apps/wire-cell-prod-stm.cxx` runs `check_stm` (:855), then `glm_tagger` (:867), `check_stm_only` (:877), `check_full_detector_dead` (:897 area) and `M2_cosmic_tagger` (:913), selected by the `-g` `flag_glm` option.
  - `/exp/sbnd/app/users/yuhw/wcp/uboone_nusel_app/apps/prod-wire-cell-matching-nusel.cxx:1538-1550` runs the 2dtoy `check_tgm` / `check_fully_contained` for in-beam-window flashes.
  - 2dtoy's own `cosmic_tagger` uses 4-element tolerances `{1.0, 1.0, 1.5, 1.0}`, `{2.0, 2.0, 3.0, 3.0}`, `{0.8, 1.0, 1.2, 1.0}` (T:65-67).
- **Constructor arguments in every production app:** `d = 3 cm`, top 117 (nusel: 116), bottom −116, z 0–1037, x 0–256. Examples: `/exp/sbnd/app/users/yuhw/wcp/pid/apps/wire-cell-prod-nue.cxx:414-417` and `/exp/sbnd/app/users/yuhw/wcp/uboone_nusel_app/apps/prod-wire-cell-matching-nusel.cxx:896-899`.

## 4. Data vs MC, and how flash time enters

- **`flag_data` choice per app:**
  - prod-nue, prod-pi0 and prod-bee pass `flag_data=0` for overlay and full MC (`wire-cell-prod-nue.cxx:81-82`).
  - prod-stm hard-codes `flag_data=1` for all tiers (`wire-cell-prod-stm.cxx:73`).
  - nusel uses `flag_data=1` for reconstruction ("no difference" comment, :100-103). Its truth FV uses `flag_truth=0` (:608-616).
- **Scope of the data/MC switch:** it changes only the flat FV corners (§1a). The SCB arrays and M2 arrays are identical for data and MC.
- **`flag_match_data`** (MC → false) affects only the dead-PMT handling in `calculate_pred_pe`. In prod-stm it is also passed into M2's `flag_data` slot (:913).
- **Flash time:**
  - `offset_x = (t_flash − time_offset)·2/nrebin·time_slice_width`, with `time_slice_width = nrebin·unit_dis·0.5 mm` (C:21-22, 93; `wire-cell-prod-nue.cxx:179`, `wire-cell-prod-stm.cxx:815`).
  - Every test then uses `x − offset_x`. Each candidate flash in a tagger supplies its own `offset_x`.
- **Beam windows:** these are trigger-bit dependent and gate which flashes are considered (`prod-wire-cell-matching-nusel.cxx:1253-1259`, `wire-cell-prod-stm.cxx:204-210`). They are not part of the point test.
- **Other places 0/256 cm is hard-coded:** `calculate_pred_pe` x cuts of 0/256 cm with extensions −2/+1.2 cm (C:385-390), and `check_full_detector_dead` x range −10 to 266 cm with a > 8000 channel threshold (P:287, 314).

## 5. What a port needs, and what is MicroBooNE-specific

**Minimal parameter set per TPC (per drift volume):**
- Anode x, cathode x and drift sign.
- y and z extents.
- Flat FV vertices: 2 kink points per edge (bottom, top, upstream, downstream), with data and MC variants.
- `boundary_dis_cut`.
- Optional binned SCB polygons: bin edges in z (for x–y) and in y (for x–z), with per-bin kink vertices.
- Tolerance vectors per consumer.
- The drift-speed and `time_offset` convention used to build `offset_x`.

**Hard-coding to generalize for SBND:**
- **Single TPC, anode at x=0, drift toward +x.** Vertices are written as "anode + d" and "kink_x − d", `x − offset_x` assumes +x drift, and "near anode" means `x < 2 cm`. SBND needs one polygon set per TPC: anodes at about ±200 cm and the shared cathode at x=0, with mirrored x and an `offset_x` sign that depends on the TPC.
- **Cathode = 256 hard-coded** in the SCB arrays (P:148, 155, 160, 167, 225-240), `inside_x_region` calls (C:100, 154), `calculate_pred_pe` (C:385) and `check_full_detector_dead` (P:287). `m_cathode` itself is unused.
- **Fixed binning:** `index_z = floor(z/m)` with 10 bins (assumes 0–10.37 m), `index_y = (y+116)/24`, and M2's `z/100cm+1`, `≤1037`, `<−116`, `≤117` (P:1747-1750, H:48-67, C:2021-2030, 2117-2143).
- **Channel and tick constants** in `inside_dead_region` / `AddDeadRegion` (2400 / 4800 / 8256 / 2398; P:1813-1823, 1888-1918). Plane angles of ±60° are hard-coded in direction checks (C:655-657, P:412-415).
- **MicroBooNE PMT geometry** (C:78, 2187-2232, `1037 −` at C:2301/2662) and the PE thresholds (C:2249-2262).
- **Defects to fix rather than copy:**
  - The dangling `neg_tol_vec` (C:622-631).
  - `space_yy`/`space_zz` using the x tolerance (C:2085-2086).
  - `inside_fiducial_volume` mutating member state (P:1764-1795).
  - Unused `boundary_*_array` (P:190-202).
  - Inconsistent sign conventions: a positive tolerance enlarges the volume in `inside_fiducial_volume` but shrinks it in `inside1_outside0_SCB`.
