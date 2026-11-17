# Issue 50: an optional non-box effective boundary for SBND (plan for Sne)

Author: `porting_sbndbuild03`, 2026-11-17. This is a plan only: no WCT code was changed.

Background material, all in `porting_sbndbuild03/`:
- `paper-notes.md`: verbatim extracts of arXiv 2101.05076 §V.
- `prototype-survey.md`: the MicroBooNE prototype (`ToyFiducial`, `Cosmic_tagger.h`).
- `wct-survey.md`: the WCT 0.38.0 boundary code, with file:line references.

Paths below are relative to the toolkit tree unless absolute.

## 0. Summary

- **The machinery already exists in WCT.**
  - `PolyFiducial` stacks polygon slabs along one axis. Its header says it is the port of the prototype's `ToyFiducial`.
  - `CompositeFiducial{logic:'and'}` combines an x–y polygon and an x–z polygon. That is the paper's two-projection test.
- **PDHD is a ready template.** PDHD has two drift volumes mirrored about a cathode at x = 0, like SBND.
  - It ships a default-off `curved_fv` knob: `pdhd/curved_fiducial.jsonnet`, `curved_fiducial_profiles.jsonnet`, and `pdhd/pr.jsonnet:1415-1447`.
  - Its surface comes from a cosmic exit-end census (doc `pdhd/09`, which ports doc `pdvd/43`).
  - It has been PDHD production since 2026-09-07, at the exit-gap 90th-percentile surface plus a 3 cm cushion ("p90 + 3").
  - PDVD has the same mechanism.
- **SBND needs:**
  1. an SBND port of that jsonnet, with one profile set per TPC;
  2. one knob in `sbnd/clus.jsonnet` `pr()`, default off, so compiled configs stay byte-identical;
  3. a measured SBND surface, made with the PDHD census method on SBND cosmics, data and MC separately;
  4. doctests for the polygon fiducials;
  5. the gates in §5.
- **No C++ change is needed for the cosmic taggers.** Every consumer reaches the boundary through `IFiducial::contained`.

## 1. Where SBND's boundary comes from

The paper gives no coordinates (§V.A), and the prototype's numbers are MicroBooNE's: one TPC, cathode at 256 cm, 273 V/cm. **SBND must measure its own.**

### 1.1 The measurement: an exit-end census on SBND cosmics

This is the method of doc `pdhd/09` §5–7 (`/exp/sbnd/app/users/yuhw/wcp-porting-img/pdhd/docs/09_pdhd-space-charge-fiducial.md`), which ports doc `pdvd/43`. It is the paper's §V.A done with an end-point estimator:
- **Ends:** every end of every long (> 2 m, ≥ 40 points) cluster that is matched to light, in T0-corrected reconstructed coordinates. These are the coordinates the SBND taggers use (`sbnd/clus.jsonnet:104-110`).
- **Assign each end to one wall:** the first of the six planes that a ray from the end, along the track's outward direction, crosses. Record the signed perpendicular gap.
- **Exclude:** ends at the readout-window edges, which are incomplete. Subtract the flat non-exit floor.
- **Bin in drift distance |x|**, per TPC and per wall. Take a gap quantile per bin.
  - PDHD found p80 worse than the flat box and p90 best.
  - Regularize so the inset does not increase toward the anode (PAV), and bootstrap over ends (300).
- **Grade with the held-out exit-end miss rate:** of the ends that really exit, the fraction the boundary calls contained (`pdhd/09` §7). Use the miss rate on an independent run to pick the quantile and cushion.
- **Scripts:** the `d09_*` scripts named in `pdhd/09` §0 (`d09_exit_census.py`, `d09_quantile_surface.py`, `d09_quantile_offline.py`, `d09_fv_pdhd.py`). They hold PDHD-specific constants (§1.3) that the port must replace.

### 1.2 Samples

| | data | MC |
|---|---|---|
| sample | SBND off-beam ("beam-off", InTime-Run1) data: only cosmics, and a known set | the Gen2 BNB CV MC, which includes CORSIKA cosmics (`prodgenie_corsika_proton…`) |
| building | **only the training half** `WCLocal2026Nov16/beam-off-train` (odd runs) | any CV subset |
| grading | `beam-off-eval` (even runs) and/or a Run-3 BNB subset, so the surface is graded on runs it was not built from | a second, disjoint CV subset |
| what it shows | the real space-charge distortion and imaging edges | whatever the MC simulates |

- **Inputs:** the WCLocal2026Nov16 outputs (#48) already hold reconstructed clusters for all of these, through the tracking-pr tars and the qlpctree tars (`lists/*-scratch.txt`). For the census, only step 2 (clusters and Q/L) is needed, rerun with debug output.
- **Space charge on vs off (must be answered first):**
  - Does the Gen2 MC simulate space charge (larsim SCE in detsim)? Check the Gen2 fhicl.
  - If yes, MC gets its own surface (the prototype had separate data and MC FV polygons).
  - If no, the MC surface should come out flat (inset ≈ 0 on every wall). That is a closure test of the instrument, and MC keeps the box (or the flat profile).
  - The reconstruction side is fixed: SBND reco runs with `use_sce:false` for both data and MC (`sbnd/clus.jsonnet:921-925`). The surface therefore describes reconstructed space, as in the paper.
- **Expected size:** SBND drifts 2 m at 500 V/cm. MicroBooNE drifted 2.56 m at 273 V/cm with more space charge per cm. Expect a smaller inset than MicroBooNE's 10–40 cm, but measure it.
  - `SCEoffsets_SBND_E500_dualmap_CV_voxelTH3.root` (`sbnd/clus.jsonnet:66`) gives a predicted displacement map. Use it as a cross-check of the measured shape, not as the boundary.
- **Statistics gate:** at least 20 in-window exit ends per (TPC, wall, |x| bin). List any starved bins by name, as `pdhd/09` §6 does. Expect the z walls to be the starved ones, because cosmics run along y.

### 1.3 SBND constants for the port

| | SBND | source |
|---|---|---|
| anode face, both TPCs (`XW`) | 201.05 cm | `sbnd_pr_fv` box, `sbnd/clus.jsonnet:2500-2509` |
| y walls | ±199.312 cm (symmetric, like PDVD's) | the same box |
| z walls | 0.85 / 500.15 cm | the same box |
| cathode face (`CATH`) | 2.5 cm (per-face `FV_x` inner edge, `sbnd/clus.jsonnet:148-149, 170-171`) | |
| volume keys | `_tpc0` (x < 0, APA 0) and `_tpc1` (x > 0, APA 1), replacing PDHD's `_g02` / `_g13` | |
| drift bins | 4 × ~50 cm per TPC; refine if statistics allow | |
| readout-edge exclusion | the SBND readout window's raw-x early/late extremes, **measured** from the qlpctree raw x (as `pdhd/09` §5 did) and checked against ticks × drift speed | |

### 1.4 Who does what

| step | who | notes |
|---|---|---|
| answer whether Gen2 MC simulates space charge | Sne (or ask porting) | §1.2 |
| port the census scripts to SBND constants | Sne | §1.3 |
| run step 2 with debug output on `beam-off-train`, the eval subset and a CV subset | Sne on the grid or Aurora; porting_sbndbuild03 can run it on FNAL (the #48 workflow) on request | inputs from #48 |
| build and grade the surface; pick the quantile and cushion | Sne; Haiwang decides | `pdhd/09` §7, §9.6 |
| **interim boundary** | none needed: the knob ships default off, and its `flat` profile reproduces the current box (§2.3). No unmeasured curved boundary is switched on. | |

## 2. How it fits the PolyFiducial / CompositeFiducial / `curved_fv` path

### 2.1 Geometry: one polygon pair across both TPCs, with per-TPC profiles

- **One polygon pair, not two volumes.** Use one x–y polygon and one x–z polygon spanning both TPCs, continuous across the cathode, exactly as the `sbnd_pr_fv` box does today (`sbnd/clus.jsonnet:2494-2499`) and as PDHD does. A cathode-crossing track must not count as an exiter at x = 0.
  - Two separate volumes would reintroduce the cathode hole that `sbnd_pr_fv` was created to avoid.
- **Per-TPC profiles, not mirrored.** Each wall of each TPC is a knot list `[[|x|, inset], …]` from the anode face to the cathode face: 8 profiles (y+, y−, z+, z− × tpc0, tpc1). These are PDHD's `side()` / `knots()` construction (`pdhd/curved_fiducial.jsonnet:100-147`).
  - The two TPCs have separate space-charge maps (`sce_field` per APA, `sbnd/clus.jsonnet:167`) and separate electronics.
  - Mirroring (tpc1 := tpc0) is an allowed fallback **only** when the per-TPC surfaces agree within their bootstrap errors, or when a TPC's bins fail the statistics gate. Record which was used.
- **The inset is zero at the anode by construction** (`x2 ≤ XW`), as the PDHD file requires.
- **z-dependence (paper Fig. 11):**
  - v1 uses one slab per projection, the inner envelope over z (the paper's "conservatively … the inner boundary of all Z-slices").
  - Z-binned x–y slabs (several slabs in one `PolyFiducial`, axis 2) are a v2 option, needed only for a light-mismatch-style use (§4, Q/L).
  - Watch two things with multiple slabs: the slabs inside one `PolyFiducial` are OR-ed with inclusive edges, and the `m_bb` short-circuit (`PolyFiducial.cxx:139`) rejects anything past the slab span.

### 2.2 Files

- **New `cfg/pgrapher/experiment/sbnd/curved_fiducial.jsonnet`:** a port of `pdhd/curved_fiducial.jsonnet`. Change the constants (§1.3), use symmetric y walls (`±YW`, as in PDVD's version), and rename the keys to `_tpc0` / `_tpc1`.
  - It returns `{polys, composite, tn, configs, boundary_xy, boundary_xz}`.
  - It has a `profile=null` argument; `null` gives the flat walls, i.e. exactly the `sbnd_pr_fv` box.
  - **Corner order:** axis 2 → (x, y); axis 1 → (z, x) (`PolyFiducial.cxx:62-68`). PDHD's file already does this.
- **New `cfg/pgrapher/experiment/sbnd/curved_fiducial_profiles.jsonnet`:** the measured knot lists, generated by the census, one entry per chosen surface (for example `p90`), with data and MC entries if they differ. Its header lists starved bins.
- **`sbnd/clus.jsonnet` `pr()`:** the knob (§3).
- **Drivers** (`sbnd/wct-pr.jsonnet`, `sbnd/wct-pr-perevt.jsonnet`, `sbnd/wcls-img-clus-matching-pr-lib.jsonnet`): pass the knob through as TLAs whose defaults are the off values.

### 2.3 Margins and cushion

- **SBND is not like PDHD here.** PDHD's production box carried a flat 15 cm space-charge shell that the surface replaces, which is why PDHD drops its y/z margins to the cushion when `curved_fv` is on.
- SBND's `sbnd_pr_fv_margins` (`sbnd/clus.jsonnet:2521, 2533`: x 2.5, y 3, z_max 5, z_min 3 cm) are a small tolerance band, about the prototype's tagger band (`Cosmic_tagger.h:34-36`, 2.2–2.8 cm). They are not a space-charge allowance.
- **Proposed default:** with the knob on, keep `fv_tolerance` = the current SBND margins (the band), and put space charge and the cushion into the vertices.
  - Expose `curved_fv_margin_y/z` as in PDHD, but default them to the current `tgm_fv_y_margin` / `tgm_fv_zmax_margin`, so that "knob on + flat profile" equals today's box exactly.
  - Whether the band should shrink once the surface is in is a decision for after the before/after comparison (§5), not part of v1.
- **Tolerance semantics:** WCT moves the probe point by the tolerance; it does not move the polygon edge (`FiducialUtils.cxx:79-119`). On a slanted edge that differs slightly from the prototype's vertex inset, so a cushion that must be exact goes into the vertices (`cushion_*` arguments).

## 3. The knob, and keeping compiled configs byte-identical

In `sbnd/clus.jsonnet` `pr()`, copying `pdhd/pr.jsonnet:1415-1447`:

```jsonnet
// arguments (defaults = off)
curved_fv=false, curved_fv_profile='flat',
curved_fv_margin_y=null, curved_fv_margin_z=null,   // null => tgm_fv_y_margin / tgm_fv_zmax_margin

local curved_fv_cfg = (import 'pgrapher/experiment/sbnd/curved_fiducial.jsonnet')(
    name_prefix='sbndcurved',
    profile=(if curved_fv_profile == 'flat' then null else curved_fv_profiles[curved_fv_profile])),
local sbnd_pr_fv_box = { type: 'BoxFiducial', name: 'sbnd_pr_fv', data: { ... unchanged ... } },
local sbnd_pr_fv      = if curved_fv then curved_fv_cfg.composite else sbnd_pr_fv_box,
local sbnd_pr_fv_uses = if curved_fv then curved_fv_cfg.configs   else [sbnd_pr_fv_box],
```

- **Keep the box's `name: 'sbnd_pr_fv'`.** Every consumer refers to `wc.tn(sbnd_pr_fv)`, so off must still resolve to `BoxFiducial:sbnd_pr_fv`.
- **Replace `[sbnd_pr_fv]` with `sbnd_pr_fv_uses`** in `tagger_uses` (`sbnd/clus.jsonnet:3183-3197`). That is the only other edit; every tagger already reads `sbnd_pr_fv`.
- **Margins:** `local mgn_y = if curved_fv && curved_fv_margin_y != null then curved_fv_margin_y else tgm_fv_y_margin` (and the same for z). The vector at `:2521` / `:2533` uses `mgn_*` but evaluates to the old expression when off.
- **Why off is byte-identical:** an imported but unused `local` emits nothing, and every off branch is the old literal.

**How it is checked (gate G1):**
1. Compile each SBND driver before and after the change, with the knob absent and with `curved_fv=false` given explicitly, for sim and data and both production vertex passes.
   - Drivers: `wct-pr.jsonnet` with the production TLAs (as `#48 porting_sbndbuild03/scripts/config-md5.sh` does), `wct-pr-perevt.jsonnet`, and `wcls-img-clus-matching-pr-lib.jsonnet` through its fcl wrapper.
2. `cmp` the JSON outputs, and record the normalized md5s (that script's method). **Every one must be identical.**
3. Record the table in the issue, as `pdhd/09` §10 does.

**Gate G2, knob on with the flat profile:** the compiled config differs (a composite instead of a box), but the tagger results must equal the box on the §5 samples. Compare per cluster: TGM, STM and FC flags, and the neutrino-tagger flags.
- Exact equality is expected. Any difference must be traced to a point that lies exactly on a wall, where `pnpoly` and `BoundingBox::inside` treat the edge differently, and documented.
- This proves the plumbing before any measured surface is used.

## 4. Consumers: what switches

Three kinds of boundary exist in SBND today (`wct-survey.md` §1–3):
- **(a)** the tagger box `sbnd_pr_fv` with its margins;
- **(b)** the FiducialUtils volume `fiducial=dv`: the union of the sensitive volumes, no margin, with a hole at the cathode;
- **(c)** the `FV_*` numbers in the DetectorVolumes metadata (box only, not an `IFiducial`).

The knob changes (a) only.

| consumer | today | v1 (knob on) | why |
|---|---|---|---|
| **TGM**: `TaggerCheckTGM` `inside_fv` / `inside_fv_interior` (end points, chord midpoints, prolonged-signal check, neutrino-candidate apex) | (a) | **must switch** | the purpose of the issue (paper §V.B) |
| **STM containment gate** (`cluster_fc_check` in `TaggerCheckSTM:3620`, `stm_consistent_fv=true`) | (a) | **must switch** (automatic) | paper §V.C "exactly one extreme point outside" |
| STM internal tests: kink search, internal TGM, one-end-outside, `check_dead_volume` | (b) | **leave** in v1; optional v2 via a second knob | they read FiducialUtils; switching it moves the dead-volume / signal-processing walk termination for every consumer (§4.1) |
| STM `dist_to_anode`, `cathode_guard_reject` | box faces (`inner_bounds`) | **leave** | distances to the physical planes, not a containment test |
| **FC tag** (`TaggerCheckFC`) | (a) | **must switch** (automatic) | "contained" must keep one meaning for TGM and FC (`sbnd/clus.jsonnet:2513-2516`) |
| neutrino `match_isFC` (`TaggerCheckNeutrino:4580`) | (a) | **must switch** (automatic, `neutrino_consistent_fv=true`) | the same definition |
| **cosmic tagger** `cosmic_tagger` flags 1–10 (`NeutrinoTaggerCosmic:504-571`) | (a), `cosmic_consistent_fv=true` | **switches** (automatic); validate | the prototype used its polygon here too (`NeutrinoID_cosmic_tagger.h`); these are BDT inputs (`cosmict_*`) |
| **nue / single-photon tagger** `angular_cut`, `shower_to_wall`, `bad_reconstruction_2(_sp)` | (a), `nue_sp_consistent_fv=true` | **switches** (automatic); validate | BDT inputs (`br3_2_other_fid`, the shower-to-wall family) |
| BDT / kinematics inputs generally | follow the taggers above | **validate**, no separate switch | the BDT weights are MicroBooNE-trained on a polygon-based boundary, so a polygon may be closer to the training. §5 compares the input distributions. |
| PR in-volume checks: `break_two_end_dqdx` (`NeutrinoPatternBase:3041`), vertex finder (`NeutrinoVertexFinder:1260, 1314, 2188, 4455, 4558, 5348`) | (b) | **leave** | these ask whether a point is in the detector during reconstruction, not cosmic rejection; switching them moves vertexing |
| dead-volume / signal-processing walks (`FiducialUtils::check_*`) | (b) | **leave** in v1 | §4.1 |
| **neutrino-candidate FV for analysis** (selection cut on the reco vertex) | analysis-side box | **optional**, the analysts' call | the paper defines FV = 3 cm inside the effective boundary (§V.A). Providing `curved_fv_cfg` with a 3 cm cushion as a named volume is cheap; adopting it is an analysis decision. |
| **Q/L matching**: `inner_bounds` run bounds, `at_x_boundary`, `close_to_PMT`, `cathode_fiducial` (`QLMatching.cxx:1475-1505, 5175-5241`) | box + CPA exclusion | **leave** in v1; v2 candidate | the paper's light-mismatch use (§V.D) needs the **z-dependent** boundary (Fig. 11), i.e. z-binned slabs (§2.1). That is a separate project with its own Q/L validation. |
| clustering metadata FV (`select_scope_fv`, `clustering_separate`, `clustering_examine_x_boundary`, `clustering_neutrino`) | (c) | **leave** | box numbers, not an `IFiducial`; changing them needs C++ and moves clustering |
| **truth containment**: labeler `pf_fiducial` = `fiducial_box()` (`sbnd/clus.jsonnet:3461-3474`) | box | **leave on box** | truth containment defines efficiency denominators and must not depend on the reco-space distortion |

### 4.1 The second knob (v2, optional)

Pointing `MakeFiducialUtils.fiducial` (`common/clus.jsonnet:1728-1736`, set from `dv` at `sbnd/clus.jsonnet:2464-2467`) at the curved composite would switch every (b) site at once, including the STM internal tests and the walks. Two cautions:
- The walks step until the point leaves the volume. A curved volume ends them earlier near the cathode corners, which changes `check_dead_volume` and `check_signal_processing` for TGM, FC and STM together.
- `dv` currently also provides the cathode hole, and some walk logic may rely on it.

If it is ever wanted, it should be a separate default-off knob with its own A/B. **Not part of v1.**

## 5. Tests

### 5.1 Doctests (C++ tests only; no library change)

In `aux/test/doctest_fiducials.cxx`, which today covers only `BoxFiducial` and a single-slab `PolyFiducial`:
1. **Multi-slab `PolyFiducial`:** OR across slabs, inclusive slab edges, the `m_bb` short-circuit, and the corner order for axis 1 vs axis 2.
2. **`CompositeFiducial` `and` / `or`:** an x–y and an x–z polygon. A point inside both is contained; a point outside either is not.
3. **The flat SBND profile equals the box:** points on a grid, including on the walls, give the same `contained` for the flat composite and for `BoxFiducial:sbnd_pr_fv`. This pins G2 at the unit level and documents the on-wall convention.
4. **The 6-probe tolerance against a polygon** (`FiducialUtils::inside_fiducial_volume` with a size-6 vector): a negative tolerance near a slanted edge shrinks the volume, and the index-4/5 z convention matches `sbnd/clus.jsonnet:2510-2512`.

Plus a jsonnet check, a small `jsonnet -e` or `wcsonnet` assertion in the test suite:
- the SBND `curved_fiducial.jsonnet` polygons are closed, wind consistently and stay inside the box;
- `profile=null` reproduces the box corners;
- every profile in `curved_fiducial_profiles.jsonnet` has inset 0 at the anode.

### 5.2 Gates on samples

**Samples:**
- the #43 MC tars and nueCC-48 + NCπ0-19: the step-1 tars at `/exp/sbnd/data/users/yuhw/production-prep/pr543-review/inputs/`, the same set as #48 P1, run with the production step-2 TLAs (`#48 porting_sbndbuild03/scripts/run-step2.sh`);
- plus, for the boundary itself, the held-out cosmic samples of §1.2.

| gate | arms | pass |
|---|---|---|
| **G1** byte identity | knob absent; `curved_fv=false` | compiled JSON identical (`cmp`) for every driver, reality and pass (§3) |
| **G2** plumbing | knob on, `flat` profile vs knob off | identical per-cluster TGM, STM and FC flags and neutrino-tagger flags; identical `recTreeWireCell` apart from documented on-wall points |
| **G3** physics | knob on, measured profile vs off, on the #43, nueCC-48 and NCπ0-19 samples | a per-event table of TGM, STM and FC tags, the selected neutrino cluster, and the `cosmict_*` / `br*` / shower-to-wall BDT inputs. Every changed event explained (a Bee scan of a sample of them); no crash or new "DL vertex failed"; ν_e / NCπ0 signal efficiency on the MC not lowered beyond a stated tolerance. |
| **G4** boundary quality | the measured surface vs the box, on held-out data (`beam-off-eval`) | exit-end miss rate (`pdhd/09` §7) lower than the box's, overall **and** in the cathode half (the box's known imbalance); long-track (> 2 m) TGM count not lower |
| **G5** MC closure | MC surface (if MC has no space charge) | inset ≈ 0 within the bootstrap errors on every wall |

- **Known pitfall:** `pdhd/09` §9.3 found a TGM defect (`TaggerCheckTGM.cxx:1066`, two-group clusters whose ends fall outside). A tighter volume feeds it more short-cluster tags. Check whether it is present in 0.38.0 before reading the G3 TGM counts, and report short-cluster (< 10 cm) TGM tags separately.

## 6. Hand-off for Sne

**Implement, in this order** (each step is its own reviewable commit):
1. **Doctests 5.1(1, 2, 4)** for the existing `PolyFiducial`, `CompositeFiducial` and the tolerance probe. No behaviour change; they pin what follows.
2. **`sbnd/curved_fiducial.jsonnet`** with SBND constants and per-TPC keys (§1.3, §2.2), and the jsonnet check (§5.1). Nothing imports it yet, so configs are still byte-identical.
3. **The knob in `sbnd/clus.jsonnet` `pr()`** plus the driver TLAs (§3).
   - **Acceptance:** G1 (byte identity, recorded table) and G2 (knob on + flat = box on the §5.2 samples), and doctest 5.1(3).
4. **The census port** (`d09_*` → SBND, §1.1, §1.3) and the space-charge-in-MC answer (§1.2).
   - **Acceptance:** the statistics gate passes or starved bins are listed; the MC closure G5 if it applies.
5. **The data surface** from `beam-off-train`, graded on `beam-off-eval`. Choose the quantile and cushion by G4; Haiwang decides the operating point.
   - Write `curved_fiducial_profiles.jsonnet`, with data and MC entries if they differ, and select by `reality` in `pr()`, which `pr()` already sees (`sbnd/clus.jsonnet:896`).
6. **G3** on the #43, nueCC-48 and NCπ0-19 samples. Every changed event explained.
7. Only then: propose turning the knob on in a production driver, as PDHD did in `wct-pr-perevt.jsonnet`. The `pr()` default stays off.

**Files:**
- **new:** `sbnd/curved_fiducial.jsonnet`, `sbnd/curved_fiducial_profiles.jsonnet`, the census scripts, test additions in `aux/test/doctest_fiducials.cxx` (plus `clus/test` for the tolerance probe);
- **edited:** `sbnd/clus.jsonnet` (`pr()` arguments, `sbnd_pr_fv` / `sbnd_pr_fv_uses` / `mgn_*`, `tagger_uses`), and the three SBND drivers (TLA pass-through);
- **not touched in v1:** any C++ outside tests; `MakeFiducialUtils`; Q/L; clustering metadata; the truth labeler.

**Open questions (for Haiwang / Sne):**
1. Does the Gen2 MC simulate space charge? This decides whether MC gets its own surface (§1.2).
2. Which quantile and cushion? PDHD chose p90 + 3. SBND decides by G4 on its own data.
3. With the surface in, should the SBND tolerance band (2.5 / 3 / 5 / 3 cm) stay, or shrink? Default: stay (§2.3).
4. Per-TPC vs mirrored profiles if one TPC is short of statistics (§2.1).
5. Should the analysis neutrino FV adopt "3 cm inside the effective boundary" (paper §V.A)? That is the analysts' call (§4).
6. Is the z-binned boundary for Q/L (paper §V.D) wanted as a v2 project (§4)?
7. Is the `TaggerCheckTGM.cxx:1066` short-cluster defect (`pdhd/09` §9.3) present in SBND 0.38.0? It should be fixed or measured before G3 is read.
