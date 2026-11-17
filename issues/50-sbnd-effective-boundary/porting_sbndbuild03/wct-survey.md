<!-- survey of the WCT 0.38.0 tree /exp/sbnd/data/users/yuhw/wclocal-nov16/wct, read-only, 2026-11-17 (subagent, spot-checks pending); file:line refs are into that tree -->
# Toolkit survey: fiducial volume and detector boundary code (WCT 0.38.0)

Source tree: `/exp/sbnd/data/users/yuhw/wclocal-nov16/wct` (`git describe` = `0.38.0`). I only read files and changed nothing. One background grep in `/exp/sbnd/app/users/yuhw/wcp-porting-img` was stopped before it finished, so that tree was not searched.

## TL;DR

- **The non-box form you're planning already exists.** `aux/src/PolyFiducial.cxx` says in its header that it "corresponds to 'ToyFiducial' from WC prototype". It stacks polygon slabs along an axis, which is the prototype's SCB binning. `CompositeFiducial` with `logic:'and'` combines the two planes, matching `pnpoly(XY) && pnpoly(XZ)`.
- **Two working precedents use it:**
  - PDHD and PDVD have `curved_fiducial.jsonnet`, switched by a `curved_fv` knob that defaults to false. PDHD production turns it on.
  - The compiled uboone config `clus/test/data/uboone-mabc_config.json` has separate data and MC polygon fiducials.
- **SBND tests a single box today.** `BoxFiducial:sbnd_pr_fv` spans both TPCs, and margins come in through `fv_tolerance`. The TGM, STM, FC and neutrino taggers each pick it up through their own consistent-FV switch.
- **Several boundary tests never see `sbnd_pr_fv`.** They go through the grouping's `FiducialUtils`, which SBND builds with `fiducial=dv`. That is the union of the sensitive volumes: no margin, and a hole at the cathode for |x| < 0.45 cm.
- **The metadata-based FV is box-only.** The `FV_*` keys in DetectorVolumes metadata are read by the clustering stages through `select_scope_fv`. They are plain numbers, not an `IFiducial`.

## 1. Definitions

### Interfaces
- `iface/inc/WireCellIface/IFiducial.h:10-17`: one method, `contained(const Point&)`.
- `iface/inc/WireCellIface/IDetectorVolumes.h:20-75`: `contained_by(p)` returns a wpid. Also `face_dirx`, `inner_bounds(wpid)` (the face's sensitive box), `outer_bounds` (defaults to inner, `:64`), `metadata(wpid)` and `wpident_faces`.

### IFiducial implementations (all in `aux/src`, all factory-registered)

| Component | File:line | Config keys (defaults) | Test |
|---|---|---|---|
| `BoxFiducial` | `BoxFiducial.cxx:21-48` | `bounds` = Ray `{tail,head}` (empty) | `BoundingBox::inside` |
| `PolyFiducial` | `PolyFiducial.cxx:75-146` | `axis` (0), `slabs` = `[{min,max,corners:[[a,b],...]}]` | point in bbox, then the **first** slab whose bbox and pnpoly contain it (slabs are OR-ed) |
| `CompositeFiducial` | `CompositeFiducial.cxx:68-195` | `logic` (`and`/`or`/`nand`/`nor`, default `and`), `fiducials` (list of type:name; empty list throws, `:123`) | combines the children |
| `EnvFiducial` | `EnvFiducial.cxx:219-257` | `anodes` | bbox of all faces' `sensitive()`; gaps between faces count as inside |
| `DetectorVolumes` (also an `IDetectorVolumes`) | `DetectorVolumes.cxx:22-23, 111-114` | `anodes`, `metadata`, `grid_*` | `contained_by(p).valid()`: union of per-face sensitive boxes, so gaps are holes |

PolyFiducial details:
- Corner order is `(axis+1, axis+2) mod 3` (`:66-68`). So `axis:2` takes corners as (x,y), binned in z, and `axis:1` takes corners as (z,x), binned in y. These are the prototype's `boundary_xy` and `boundary_xz` with SCB z/y bins.
- `m_bb` is the union of the slab bboxes and acts as a short-circuit (`:139`).
- A slab must have width (`:113`) and at least 3 corners (`:118`).

`DetectorVolumes::inner_bounds` returns `iface->sensitive()` (`:187-193`). `metadata(wpid)` returns the `"overall"` block when `wpid.ident()==0`, otherwise the wpid name, falling back to `"default"` (`:198-208`).

### FiducialUtils (the WCT counterpart of ToyFiducial)
- Header `clus/inc/WireCellClus/FiducialUtils.h:117-204`. The header itself says it is "approximately equivalent to WCP's ToyFiducial" (`:114`).
- Static data is `{dv, fiducial, pcts}` (`:121-125`). Dynamic data is the live and dead groupings.
- `inside_fiducial_volume(p, tolerance_vec={})`, `FiducialUtils.cxx:79-120`:
  - With an empty vector it returns `fiducial->contained(p)`.
  - Otherwise it probes six points, p shifted by ∓tol along x, y and z, and requires all six to be contained.
  - Vector size 6 means `[x_lo,x_hi,y_lo,y_hi,z_lo,z_hi]`; size ≥3 is per-axis; size ≥1 is uniform.
  - **This offsets the point, not the polygon vertices**, which differs from the prototype. `pdhd/curved_fiducial.jsonnet:38-42` already notes the difference.
- `inside_dead_region(p_raw, apa, face, minimal_views=2)` (`:35-76`): counts dead views. Returns false when apa < 0 or face < 0.
- `check_dead_volume(cluster, p, dir, step=1cm, cut_ratio=0.81, cut_value=4)` (`:123-168`): requires `inside_fiducial_volume(p)`, then walks `while(inside_fiducial_volume(temp_p))`. Points not in any face (`contained_by` invalid) count as dead.
- `check_signal_processing(... cut_ratio=0.8, cut_value=5)` (`:172-227`): the same walk, with W-plane confirmation.
- **The walks in both checks always use the FiducialUtils fiducial with no tolerance, never a tagger's own fiducial.**
- `MakeFiducialUtils` (`clus/src/make_fiducialutils.cxx:248-327`) uses the mixins `NeedDV`, `NeedFiducial` and `NeedPCTS`, with keys `live`, `dead`, `target` (all default "live"/"dead"/"live") plus `detector_volumes`, `fiducial`, `pc_transforms`. It stores the object with `grouping->set_fiducialutils` (`Facade_Grouping.h:501-502`).
- `NeedFiducial` (`ClusteringFuncsMixins.h:63-66`, `.cxx:23`) does `Factory::find_tn<IFiducial>(cfg["fiducial"])`. **Several taggers call it only when the key is present**, because the type-only fallback name "DetectorVolumes" is not instantiated in SBND (`TaggerCheckSTM.cxx:96-103`, `TaggerCheckFC.cxx:78-84`, `TaggerCheckNeutrino.cxx:662-663`).

### Metadata box FV (not an IFiducial)
- `select_scope_fv(dv, common_face_x)` at `clus/src/clustering_separate.cxx:36-139` reads `FV_{x,y,z}{min,max}` and `*_margin`, plus `vertical_dir` and `beam_dir`. It uses `"overall"` for multi-APA scopes and the per-face blocks otherwise.
- `inset_scope_fv` is at `:141`. The `ScopeFV` struct is at `ClusteringFuncs.h:353-408`.
- `validate_drift_group` (`ClusteringFuncs.cxx:108-128`) reads the per-face `FV_x*` values.
- `SimpleClusGeomHelper` (`clus/src/SimpleClusGeomHelper.cxx:37-75`, `is_in_FV`) and `UbooneGeomHelper` (`root/inc/WireCellRoot/UbooneGeomHelper.h:42-61`, uboone box defaults) are both box-only. SBND passes `clus_geom_helper=''` (`sbnd/clus.jsonnet:1800`).

### Existing polygon (non-box) uses and how each is selected
- **uboone** (compiled JSON only; I found no source jsonnet in this tree):
  - `clus/test/data/uboone-mabc_config.json:11438-11560` defines `CompositeFiducial:uboone_data_fid` and `uboone_mc_fid`, each the AND of `PolyFiducial` `fiducial_{data,mc}_xy` (axis 2) and `_zx` (axis 1).
  - Each has **one slab** (no SCB binning). Units are mm, and the vertices look inset by 3 cm. Example, data xy: `[[30,-1130],[770,-1130],[2530,-960],[2530,990],[970,1130],[30,1140]]`, z ∈ [0,10370].
  - The data/MC choice is made by name: `MakeFiducialUtils.fiducial = "CompositeFiducial:uboone_mc_fid"` (`:11733`).
  - The source `clus/test/uboone-mabc.jsonnet:99-124` contains only the `FV_*` metadata.
- **PDHD**: `cfg/pgrapher/experiment/pdhd/curved_fiducial.jsonnet` (function args at `:83-100`, polygons at `:150-198`) builds an xy and an xz polygon spanning both drift volumes, continuous across the cathode, from per-wall [|x|, inset] knots, with `cushion_*` options.
  - Profiles live in `curved_fiducial_profiles.jsonnet` (generated p80/p90).
  - Selection is in `pdhd/pr.jsonnet:1415-1447`: `local pdhd_pr_fv = if curved_fv then curved_fv_cfg.composite else pdhd_pr_fv_box`, plus `pdhd_pr_fv_uses`. When curved, the y/z margins become the cushion alone (`mgn_y`, `mgn_zmax`, `mgn_zmin`).
  - The knob defaults off (`pr.jsonnet:315`); production turns it on in `pdhd/wct-pr-perevt.jsonnet:1584`.
- **PDVD**: the same pattern in `protodunevd/pr.jsonnet:44-48, 306-328, 1454-1491`, plus `crp_gap_fiducial.jsonnet`.
- **SBND**: no polygon. `cathode_fiducial.jsonnet` is a CPA exclusion volume: the OR of 26 `BoxFiducial`s in a `CompositeFiducial` (`:97-113`). It is used only by Q/L matching.

## 2. SBND configuration vs uboone

**DetectorVolumes metadata `dvm()`** (`sbnd/clus.jsonnet:125-173`; source is the v0206 wire bbox minus 1 cm):
- overall: `FV_x ±201.05`, `FV_y ±199.312`, `FV_z [0.85, 500.15]` cm.
- overall margins: x 2 / 2, y 2.5 / 2.5, z 3 / 3 cm. Also `vertical_dir [0,1,0]`, `beam_dir [0,0,1]`.
- Per-TPC blocks: `a0f0pA` has `FV_x [-201.05, -2.5]` (`:148-149`, "data CPA face (-1.5) − 1 cm"); `a1f0pA` has `FV_x [2.5, 201.05]` (`:170-171`). y and z are copied from overall (`:157-164`).
- Per-APA `sce_field` (`:167`) and the data-only `pos_offset` (`:168, 172`) are also set here.
- uboone metadata for comparison: x [1, 255], y [-99.5, 101.5], z [15, 1022] cm, same margins (`clus/test/uboone-mabc.jsonnet:99-124`).

**FiducialUtils fiducial in the PR stage**: `cm = clus.clustering_methods(..., fiducial=dv, ...)` (`sbnd/clus.jsonnet:2464-2467`), and `fiducialutils: cm.fiducialutils()` (`:2688`; common definition at `common/clus.jsonnet:1728-1736`).
- This volume is the union of per-face sensitive boxes: |x| ≤ 201.45, |y| ≤ 199.965, z ∈ [0, 501.0], with |x| < 0.45 a hole. The comment at `:2454-2463` says so.

**Tagger box `sbnd_pr_fv`** (`sbnd/clus.jsonnet:2500-2509`):
- `BoxFiducial`, tail (-201.05, -199.312, 0.85) cm, head (201.05, 199.312, 500.15) cm. It is one box over both TPCs, so the cathode is not a boundary (`:2494-2499`).
- Margins (`:2521`): `[-x, -x, -y, -y, -zmax, -3] cm`. The comment at `:2510-2512` explains that index 4 is applied as `contained(z - tv[4])`, so with a negative value it **insets the downstream face**; index 5 insets the upstream face.
- An interior variant is at `:2533`.
- SBND values: `tgm_fv_x_margin=2.5`, `tgm_fv_y_margin=3`, `tgm_fv_zmax_margin=5`, `tgm_fv_zmax_margin_interior=3` (`:1222-1223`; driver `wct-pr-perevt.jsonnet:1065-1079`). The legacy values were 2 / 2.5 / 3 / 0.
- `tagger_uses` adds `[sbnd_pr_fv]` only when one of its consumers is in the pipeline (`:3183-3197`).

**Wiring into the taggers** (common definitions in `cfg/pgrapher/common/clus.jsonnet`):

| Tagger | Common jsonnet | SBND call | Fiducial / tolerance passed |
|---|---|---|---|
| `tagger_check_tgm` | `:538-580` | `:2823-2829` | always `sbnd_pr_fv` + margins; `interior_fv_tolerance` only if > 0 |
| `tagger_check_fc` | `:609-617` | `:2873-2876` | always `sbnd_pr_fv` + margins |
| `tagger_check_stm` | `:285-324` | `:2775-2776` | `sbnd_pr_fv` + margins when `stm_consistent_fv` (true, `:1366`; driver `:595`) |
| `tagger_check_neutrino` | `:627, 705-713` | `:2929-2930, 2956, 2962` | `sbnd_pr_fv` + margins when any of `neutrino_consistent_fv`, `cosmic_consistent_fv`, `nue_sp_consistent_fv` (all true, `:1784-1798`) |

When a key is omitted, the C++ falls back to FiducialUtils.

**C++ defaults:**
- TGM: `fiducial="DetectorVolumes"`, `fv_tolerance=[]`, `interior_fv_tolerance=[]` (`TaggerCheckTGM.cxx:234-238`; read at `:209-226`).
- STM: `fiducial=null` (meaning use FiducialUtils), `fv_tolerance=[]` (`TaggerCheckSTM.cxx:516-517`).
- Neutrino: `cosmic_consistent_fv` and `nue_sp_consistent_fv` default false (`TaggerCheckNeutrino.cxx:683-694, 1150-1151`).

**Q/L matching** (`sbnd/qlmatching.jsonnet:76-82`, key `cathode_fiducial`, C++ default `""` at `QLMatching.cxx:980`):
- SBND passes `cathode_fiducial.jsonnet(cx=cy=cz=0.5 cm).tn` (`wcls-img-clus-matching-pr-lib.jsonnet:277-291`; `wct-clus-matching-perevt.jsonnet:505-552`).

**Truth labeler**: `fiducial_box()` (`sbnd/clus.jsonnet:3461-3474`) builds `BoxFiducial:all-overall-fv` as the overall FV with margins applied. It is passed as `pf_fiducial` (`wcls-img-clus-matching-pr-lib.jsonnet:421, 455`). Its C++ consumer is not in this tree; it is probably in the larwirecell labeler.

## 3. Consumers

### Containment tests
"FU" means FiducialUtils, which in SBND is `dv`: no margin, cathode hole. All rows are SBND-relevant unless marked otherwise.

| Site | Test | Volume / tolerance |
|---|---|---|
| `Clustering_Util.cxx:75-130` `cluster_fc_check` (shared by FC, STM gate, neutrino `match_isFC`) | endpoint `inside_fv` `:146`; two-end arbitration `:238-239`; `check_signal_processing` `:200`; `check_dead_volume` `:212` | `fiducial` + `fv_tolerance` if given (6-probe), else FU. **The two walk checks always use FU.** |
| `TaggerCheckTGM.cxx:801-828` | `inside_fv` / `inside_fv_interior`: CASE A ends `:1012, :1020`; chord midpoints `:1031, :1073, :1079`; prolonged signal `:1364`; neutrino-candidate apex `:1467, :1484` | `sbnd_pr_fv` + margins |
| `TaggerCheckTGM.cxx` | `check_signal_processing` / `check_dead_volume` `:1126-1150`; `inside_dead_region` `:1340-1385` | FU |
| `TaggerCheckSTM.cxx:3620-3624` | containment gate via `cluster_fc_check` | `sbnd_pr_fv` + margins |
| `TaggerCheckSTM.cxx` | kink search `:1773, :1886`; internal TGM `:3853-3854`; one end outside `:3880`; `check_dead_volume` `:3886`; `inside_dead_region` `:1817, :1907` | **FU, no tolerance** (not switched by `stm_consistent_fv`) |
| `TaggerCheckSTM.cxx:3673-3700` `dist_to_anode`; `:2396-2420` `cathode_guard_reject` | distance to anode/cathode from `inner_bounds` and `face_dirx` | box faces only |
| `TaggerCheckFC.cxx:207-209` | `cluster_fc_check` | `sbnd_pr_fv` + margins |
| `TaggerCheckNeutrino.cxx:4580-4586` `match_isFC` | `cluster_fc_check`; also computes the legacy FU result for an audit | `sbnd_pr_fv` + margins |
| `NeutrinoTaggerCosmic.cxx:504-571` `cosmic_tagger` | `inside_fv` (flags 1-10, `:659-1354`); vertex flag 1 uses uniform -1.5 cm (`:566`) | `m_cosmic_fiducial` + `m_cosmic_fv_tolerance` when `cosmic_consistent_fv`, else FU |
| `NeutrinoTaggerNuE.cxx:396-417` `angular_cut` | -1.5 cm | `m_nue_fiducial` if `nue_sp_consistent_fv`, else FU with a 5-element vector (size-≥3 mapping trap, `:2464`) |
| `NeutrinoTaggerNuE.cxx:2493-2501` `shower_to_wall` | walk with -1.5 cm | same switch as above |
| `NeutrinoTaggerNuE.cxx:3330-3346` `bad_reconstruction_2` | -3 cm (emulates the prototype's 3 cm boundary inset) | same switch, else FU with no tolerance |
| `NeutrinoTaggerSinglePhoton.cxx:759-772` `bad_reconstruction_2_sp` | same pattern | same switch |
| `NeutrinoPatternBase.cxx:3041-3044` `break_two_end_dqdx` | both fit ends | FU |
| `NeutrinoVertexFinder.cxx` | `compare_main_vertices` `:1260, :1314`; `examine_direction` `:2188-2191`; `compare_main_vertices_global` `:4455, :4558`; `determine_overall_main_vertex_DL` `:5348` | FU, no tolerance |
| `CheckSTM_Michel.cxx:2637, 3198-3199, 4542` | `check_dead_volume`, `in_fv` with its own `fiducial` key | FU or own key. **Not SBND** (not in the SBND pipeline). `CheckBeamParticle` likewise. |

The 6-probe tolerance code is duplicated in five places: `FiducialUtils.cxx:113`, `Clustering_Util.cxx:115`, `TaggerCheckTGM.cxx:816`, `NeutrinoTaggerCosmic.cxx:509`, and `NeutrinoTaggerNuE.cxx:85` / `SinglePhoton.cxx:74`. All of them call only `IFiducial::contained`, so a polygon `IFiducial` drops in without C++ changes.

### Metadata box consumers (clustering and Q/L)
- `clustering_separate` reads `select_scope_fv` plus `fv_inset_yz` at `:2334`. SBND sets 15 cm (`sbnd/clus.jsonnet:400`). `sbnd_boundary_tag` is at `:151-225`.
- `clustering_neutrino.cxx:208-324` tests extremes against the `FV_*` values.
- `clustering_examine_x_boundary.cxx:86-123` uses `FV_x` ± margin, per face.
- `QLMatching.cxx:1475-1505` takes run bounds from `inner_bounds` plus y/z cushions. `:5175-5241` sets the containment, `close_to_PMT` and `at_x_boundary` flags. The cathode end uses `m_cathode_fv->contained` at `:5233` for SBND, otherwise a flat 1-D window. `compute_two_boundary_flag` is at `:5325`.

All of these are SBND-relevant and outside the cosmic-tagger effective-boundary scope.

## 4. Data/MC and space charge

- **The SBND FV does not depend on data vs MC.** Reality changes only `pos_offset_on` and the coordinates the scopes use:
  - `reco` at `sbnd/clus.jsonnet:921-925`: sim is `{use_sce:false, pos_offset_on:false}`, data is `{use_sce:false, pos_offset_on:true}`.
  - The PR scope is `x_t0cor, y_cor, z_cor` for data and `x_t0cor, y, z` for sim (`:104-110, 2467`).
  - The FV tests therefore run in reco space, already T0-corrected, with a data-only y/z offset. TGM assumes `offset_x = 0` because points are T0-corrected (`TaggerCheckTGM.cxx:16-17`).
- **Space charge is not applied in SBND reco.** `use_sce=false` for both realities. The SCE field exists only for an optional true-space scope and for the truth labeler (`:58-87`; `wct-pr-perevt.jsonnet:3946`).
- **No FV test has a space-charge-dependent shape today.** The only measured space-charge-shaped surfaces are the PDHD/PDVD `curved_fv` profiles.
- uboone keeps data and MC polygons and picks one by component name (§1). The PDHD and PDVD curved fiducials take no reality argument.
- **To mirror the prototype's data/MC polygons in SBND:** `reality` is a parameter of the top-level function at `sbnd/clus.jsonnet:896`, so `pr()` can see it through the closure, the same way it sees `pos_offset_on`.

## 5. Tests and keeping the compiled configs byte-identical

### Existing tests
- `aux/test/doctest_fiducials.cxx` covers `BoxFiducial` (`:12`) and a single-slab `PolyFiducial` (`:40-77`). **Multi-slab, `CompositeFiducial` and `EnvFiducial` are not tested.**
- `test/test/doctest_detectorvolumes.cxx:179-226`: DetectorVolumes as an `IFiducial`.
- `clus/test/doctest_sep_fv_inset.cxx`: `inset_scope_fv`, using the SBND per-APA FV values.
- `clus/test/doctest_pr11_guards.cxx`: sentinel guards. These are not FV logic.
- **There are no tests for `FiducialUtils::inside_fiducial_volume` tolerance probing, `cluster_fc_check`, or `TaggerCheckTGM::inside_fv_tol`.**

### Making the new option default-off with identical compiled output
- **Copy the PDHD pattern** (`pdhd/pr.jsonnet:1415-1447`):
  - Add a new `sbnd/effective_fiducial.jsonnet` that returns `{polys, composite, tn, configs}`.
  - In `pr()`, add `effective_fv=false` and rename the current box `sbnd_pr_fv_box`. Then:
    `local sbnd_pr_fv = if effective_fv then eff.composite else sbnd_pr_fv_box;`
    `local sbnd_pr_fv_uses = if effective_fv then eff.configs else [sbnd_pr_fv_box];`
  - At `:3197`, replace `[sbnd_pr_fv]` with `sbnd_pr_fv_uses`.
  - An imported but unused `local` produces no output, so off means identical output.
- **Keep the box name `'sbnd_pr_fv'`.** Every `wc.tn(sbnd_pr_fv)` reference resolves to `BoxFiducial:sbnd_pr_fv` and must stay the same when the knob is off.
- **Margins:** decide whether the polygon's built-in inset replaces part of `sbnd_pr_fv_margins` (`:2521, :2533`), as PDHD's `mgn_*` do. Only take a different branch when the knob is on.
- **SCB binning:** use several slabs inside one `PolyFiducial` (axis 2 for the z-binned xy polygon, axis 1 for the y-binned zx polygon), AND-ed by a `CompositeFiducial`. Things to watch:
  - The `m_bb` short-circuit (`:139`): a point probed outward past the slab span fails.
  - Slabs are OR-ed and boundaries are inclusive, so adjacent bins can overlap at their edges.
  - The corner order differs per axis: `axis:1` takes (z, x), not (x, z).
- **Shared FiducialUtils volume:** the FU-only sites in §3 (STM kink and internal TGM, the vertex finder, `break_two_end_dqdx`, the dead-volume and signal-processing walks) change only if `cm.fiducialutils()` gets the new fiducial instead of `dv`. Make that a separate knob, because it also moves the walk termination.
- **Tolerance semantics:** WCT shifts the point, so on slanted polygon edges the margin differs from the prototype's vertex shift. To reproduce the prototype, bake the inset into the vertices and pass a smaller tolerance.
- **Verification:** compile the SBND drivers (`wct-pr-perevt.jsonnet`, `wcls-img-clus-matching-pr-lib.jsonnet`) before and after the change with the knob off, and `cmp` the JSON. The existing "key omitted ⇒ byte-identical" comments throughout `sbnd/clus.jsonnet` use the same convention.
- **New doctests to add:** multi-slab `PolyFiducial`, `CompositeFiducial` AND, and the 6-probe tolerance against a polygon.
