# Issue 10 — dashed (broken-up) track on the W plane, BEE evt 29

Status: **debug environment ready — Bokeh waveform server running, awaiting
interactive investigation.**

## Symptom

In the 1-step clustering BEE set, event index **29** shows a track that renders
as a **dashed line** (a series of short segments with gaps) instead of a
continuous track — the orange, near-vertical track circled in red in the upper
panel.

- BEE set/event: <https://www.phy.bnl.gov/twister/bee/set/84854901-3b51-4f71-81a7-1f041ad4d867/event/29/>
- Related: HaiwangYu/wire-cell-toolkit-ai-helper#4 (the 100-file MC eval that
  produced this set).

## Event identification

| item | value |
|---|---|
| BEE event index | 29 (0-based) |
| Run / SubRun / Event | **270 / 6 / 46** |
| reco1 file | `/pnfs/sbn/data_add/sbn_nd/poms_production/mc/MCP2025C_FallProduction/v10_14_02/prodgenie_corsika_proton_rockbox0p1_sbnd/CV/reco1/a5/gen_g4_detsim_reco1-a5f42e7e-aae1-243a-11b2-fad9417d6ce0.root` |
| entry in that file | **11** (`lar -n 1 --nskip 11`) |
| local single-event extract | `data/evt-270-6-46.root` (22 MB, all products) |

Cross-check: BEE `clustering-global` for idx 29 reports `eventNo=46`, and the
ordered file list of the first-30 comparison (`first30_filelist.tsv` row 29)
says `270-6-46` from `...a5f42e7e...root`; the file's `EventAuxiliary` confirms
entry 11 = 270/6/46.

### Products available in reco1 (relevant to this study)
- `recob::Wires_simtpc2d_dnnsp_DetSim` — **dnnsp only**
- `sim::SimChannels_simtpc2d_simpleSC_DetSim` — truth (ionization electrons)
- `sim::SimEnergyDeposits_ionandscint_priorSCE_G4`, `recob::Hits_gaushit__Reco1`
- **No `raw::RawDigit`** (dropped in reco1) → `gauss` / `wiener` are *not*
  available without re-running detsim+SP from the upstream gen/g4 stage.

## Debug setup (Bokeh waveform viewer)

Same tooling as `wcp-porting-img/sbnd/standalone-sample/w-gap`
(`compare_wires_viewer.py`). **Two servers are running on sbndbuild03:**

| port | file | A | B | use |
|---|---|---|---|---|
| **5010** | `data/evt-270-6-46.root` (production reco1) | dnnsp | simchannel | production dnnsp vs truth |
| **5011** | `data/evt-270-6-46_sp.root` (detsim+SP re-run) | gauss | dnnsp | SP-stage comparison |
| **5012** | `data/magnify-270-6-46.root` (Magnify) | — | — | **all 12 SP stages** (see below) |

```bash
# started with:
scripts/serve-viewer.sh 5010
scripts/serve-viewer.sh 5011 data/evt-270-6-46_sp.root data/evt-270-6-46_sp.root gauss dnnsp
```
Connect from a laptop (tunnel both):
```bash
ssh -L 5010:localhost:5010 -L 5011:localhost:5011 <user>@sbndbuild03.fnal.gov
# then open:  http://localhost:5010/compare_wires_viewer
#             http://localhost:5011/compare_wires_viewer
```
In the 5011 file the tag `dnnsp` exists from **two** processes (`DetSim` =
production, `ReDetSim` = re-run); the viewer prefers the re-processed one, so
type the tag as needed to switch between SP stages.
The viewer gives: 3 linked 2D panels (A, B, A−B; channel × tick, bipolar
colormap), click a channel → 1D waveforms with the **simchannel truth overlay
always on**, APA/plane selectors, a clickable top-|A−B| table, and zoom-range
charge integrals with A/sim and B/sim ratios. `recob::Wire` values are ×50 →
electrons so dnnsp and simchannel are directly comparable.

Restart gotcha (from the w-gap study): `pgrep -f 'bokeh serve'`, then `kill`
the pids in a **separate** shell call.

## Orientation / first findings (automated, before interactive work)

**1. The largest dnnsp−truth discrepancies are all on the W (collection) plane**
— matching the "dashed track on W" symptom:

| channel | decode | note |
|---|---|---|
| 9677 | APA1 **w**-plane wire 71 | largest \|A−B\| |
| 10628 | APA1 **w**-plane wire 1022 | |
| 9664 | APA1 **w**-plane wire 58 | |
| 4723 | APA0 **w**-plane wire 755 | |

**2. dnnsp is losing most of the charge on those channels.** Viewer report for
channel 9677 over the full readout:
```
integrated charge: simchannel=84090.4  A(dnnsp)=20368   ->  A/sim = 0.24
```
i.e. only ~24 % of the true ionization charge survives into dnnsp on that wire —
the signature of ROI truncation / dropped ROIs rather than a clustering problem.

**3. Dashed-looking clusters in the BEE event** (gap structure along each
cluster's principal axis; `scripts/orient.py`):

| cid | npts | length [cm] | max gap [cm] | gaps >1 cm | gaps >3 cm | gap fraction |
|---|---|---|---|---|---|---|
| **5** | 354 | 95.6 | 25.5 | 10 | 6 | **0.84** |
| **11** | 511 | 125.2 | 19.6 | 12 | 9 | **0.57** |
| 8 | 320 | 36.2 | 10.3 | 4 | 2 | 0.51 |
| 14 | 1205 | 470.6 | 347.4 | 1 | 1 | 0.74 (one big split, not "dashed") |
| others (2,3,4,7,9,12,13) | — | — | ≤0.6 | 0 | 0 | 0.000 |

Only a handful of clusters are gappy at all; **cid 5 and cid 11** are the
dashed-track candidates. Bounding boxes (cm):

| cid | x | y | z | sum q |
|---|---|---|---|---|
| 5  | −53.5 … −2.5 | 32.4 … 116.9 | 207.0 … 265.5 | 4.2e6 |
| 11 | 80.4 … 201.4 | −17.8 … 32.0 | 96.6 … 165.9 | 3.7e6 |

## Working hypothesis

The dashes are **not** a clustering/imaging artifact but missing charge on the
**W plane** at the signal-processing stage: dnnsp (DNNROI) drops or truncates
ROIs along the track, so the 3-view coincidence needed to form blobs fails in
those stretches and the track breaks into segments. This is the same family of
effect documented in the **w-gap study**
(`wcp-porting-img/sbnd/standalone-sample/w-gap/W-GAP-STUDY.md`: DNNROI
truncation, charge bias / inefficiency, SP rebaselining).

To confirm and localise, use the viewer to walk the W channels along cid 5 /
cid 11 and compare dnnsp vs simchannel per channel — the truncated ROIs should
line up with the visual gaps.

## detsim + SP re-run (done) — getting gauss / wiener

**Why:** MCP2025C ran a single chained `gen_g4_detsim_reco1_reco2_caf` job — SAM
shows the only parent is the generator fcl, so **no intermediate g4/detsim file
exists**, and reco1 keeps **no `raw::RawDigit`**. But reco1 *does* keep
`sim::SimEnergyDeposits_ionandscint_priorSCE_G4`, which is exactly what the
sim job reads (`params.inputTag = "ionandscint:priorSCE"`), so drift +
digitization + SP can be redone from the same true depositions.

```bash
scripts/rerun-detsim-sp.sh          # ~3.5 min wall, ~6.6 GB peak RSS, 1 event
# -> data/evt-270-6-46_sp.root (28 MB)
```

Products in the re-run output (both the **original** and the **re-run** SP):

| product | meaning |
|---|---|
| `recob::Wires_simtpc2d_gauss_ReDetSim` | gauss (traditional SP) |
| `recob::Wires_simtpc2d_wiener_ReDetSim` | wiener |
| `recob::Wires_simtpc2d_dnnsp_ReDetSim` | DNNROI, re-run |
| `recob::Wires_simtpc2d_dnnsp_DetSim` | **DNNROI as produced in production** |
| `sim::SimChannels_simtpc2d_simpleSC_{ReDetSim,DetSim}` | re-run / original truth |

**CAVEAT:** drift, electronics and **noise are re-simulated**, so the re-run
dnnsp is not bit-identical to production dnnsp. The value is the
self-consistent gauss vs wiener vs dnnsp vs truth comparison on the same track;
the production dnnsp is preserved in the same file for reference.

### Gotchas hit while building this (all fixed in `scripts/rerun-detsim-sp.sh`)

1. **`set -e` before `source`** — the ups/setup scripts return non-zero on their
   last command, so the script aborted *silently* (empty log, no output).
   Source first, then `set -e`.
2. **The local sbndcode checkout is stale.** `setup-local-opt.sh` puts
   `/exp/.../sbndcode/sbndcode/WireCell/cfg` on `WIRECELL_PATH`, and its
   `params.jsonnet` asks for `sbnd-wires-geometry-v0202.json.bz2`, which exists
   nowhere → `WireSchemaFile` gets an empty filename and the job dies at module
   construction with `Persist.cxx: "no such file: ."`. Fix: prepend the **CVMFS**
   cfg of the version actually in use
   (`sbndcode/v10_14_02_03/wire-cell-cfg`, wires **v0206**). This supersedes the
   older "prepend the local sbndcode cfg" note for the `elec.gain` problem.
3. **`save_track_id: "true"` requires a product reco1 dropped.** The sim jsonnet
   does `sed_label: if (savetid == 'true') then 'ionandscint' else ''`, and
   `DepoFluxWriter` then hard-fails on the *SCE-applied* `ionandscint` instance —
   reco1 keeps only `ionandscint:priorSCE`. Fix: `save_track_id: "false"`; the
   SimChannel truth (`simchan_label: 'simpleSC'`) is still written, which is what
   the viewer's truth overlay needs. (Cost: no per-SimChannel track ids in the
   re-run truth — not needed for a waveform/charge comparison.)

## Magnify dump — every SP intermediate stage (done)

`data/magnify-270-6-46.root` (600 MB) holds **72 TH2F** = 3 planes × 2 APAs ×
**12 stages**, x = channel, y = tick:

```
orig  raw  tight_lf  loose_lf  decon_charge  break_roi_1st  break_roi_2nd
shrink_roi  extend_roi  cleanup_roi  gauss  wiener
```
named `h<plane><stage><apa>`, e.g. `hw_tight_lf1`, `hw_gauss1`.

```bash
scripts/make-magnify-cfg.sh     # generate the local cfg override (once)
scripts/run-magnify-dump.sh     # ~4 min -> data/magnify-270-6-46.root
# view:
python3 ../../../wcp-porting-img/sbnd/standalone-sample/w-gap/vis_waveforms.py \
        -f data/magnify-270-6-46.root -c <channel>
```

This is the tool for the core question of this issue: walk a W channel of the
dashed track through `orig → raw → tight_lf/loose_lf → decon_charge →
break_roi → shrink/extend/cleanup_roi → gauss/wiener` and see **exactly which
ROI step drops the charge**.

### How this recipe works (it was previously undocumented)

`w-gap/sbnd-data-check.root` was made the same way in Jun 2026 but the recipe
was lost: the sink lines were uncommented in-place in the sbndcode checkout and
reverted the next day. Here the edit is kept **local and reproducible** —
`make-magnify-cfg.sh` copies the two CVMFS jsonnets into `cfg/` and patches them;
the shared sbndcode tree is untouched.

Four things must all line up, and each one silently produces *nothing* if wrong:

1. **The sinks are commented out by default.** `wcls-sim-drift-depoflux-nf-sp.jsonnet`
   builds `sinks = magnify(tools, magoutput)` but every `//sinks.*_pipe[n]` is
   commented. `magoutput` is hard-coded (`'sbnd-data-check.root'` upstream; we
   rename it) and is written **relative to the CWD**.
2. **Only the `roi=="trad"` graph branch has all four sink slots** (orig, raw,
   decon, **debug**). `roi=="both"` is a `g.intern` with explicit edges and no
   sink slots; the `multipass2` block has no debug slot. So use `roi: "trad"`.
3. **`save_simdigits` selects the graph**:
   `else if save_simdigits=="true" then graph1_trad else graph2_trad` — and only
   **`graph1_trad`** contains `fanpipe` (= the `nfsp_pipes` with the sinks).
   With `save_simdigits:"false"` the job runs `graph2_trad`, never touches the
   sinks, and exits 0 having written no magnify file at all. It also then needs
   `"wclsFrameSaver:simdigits"` in `outputers`.
4. **Tags must stay non-empty.** The `roi=="both"` override blanks
   `tight_lf_tag`, `cleanup_roi_tag`, `break_roi_loop*_tag`, `shrink_roi_tag`,
   `extend_roi_tag`; the `roi=="trad"` override is just `{sparse:true}` so
   `sp.jsonnet`'s defaults survive. We add `use_roi_debug_mode: true` (default
   false) to actually emit the debug traces, and add `decon_charge<n>` to the
   `magdebug` frame list (the stock list omits it).

Also note: `outputers` must match the graph — with `roi:"trad"` there is no
DNNROI branch, so `wclsFrameSaver:dnnsaver` must be removed or the job dies with
a `FactoryException` on `IArtEventVisitor` at construction.

## Magnify viewer (port 5012)

`scripts/magnify_viewer.py` + `serve-magnify-viewer.sh` — a second Bokeh app,
built for the Magnify file:

- **top**: file path text box + **Load** (any Magnify file, not just this one)
- **left**: 2D image, **channel on X, tick on Y**, for the selected
  *stage / plane / APA*.  The stage defaults to `dnnsp` if present, else
  `gauss` (Magnify files from the `roi=trad` job have no dnnsp).  Re-rendered
  server-side on zoom with sign-preserving max-|v| pooling, so single-tick
  spikes never vanish.  **Click it to pick a channel.**
- **colour limits**: `color min` / `color max` text boxes, pre-filled with
  **60 % of the selected stage's full min/max** and re-defaulted whenever the
  stage/plane/APA/file changes; edit either box to rescale (zooming keeps
  whatever you typed).  e.g. `gauss` w/APA1 spans 0 … 4.598e4 → boxes start at
  0 … 2.759e4.
- **right**: 1D waveforms of that channel for **every** stage at once.
  **Click a legend entry to hide/show** a curve.  A `normalize 1D` checkbox
  rescales all curves to a common range — useful because the stages differ by
  ~50x (`orig`/`raw` are ADC ~1e3, decon/ROI stages ~1e4–1e5).

```bash
scripts/serve-magnify-viewer.sh 5012 [magnify.root]
ssh -L 5012:localhost:5012 <user>@sbndbuild03.fnal.gov
# http://localhost:5012/magnify_viewer
```

Implementation notes (bit us during development):
- `h.GetArray()` returns a `cppyy.LowLevelView` with **no `SetSize()`** in this
  ROOT build; read it with `np.frombuffer(view, dtype, count=n)` and reshape
  `(ny+2, nx+2)` (ROOT flat bin = `binx + (nx+2)*biny`), then strip over/underflow.
- `DataRange1d.start/end` reject `None` and report **NaN** before the first
  renderer exists — always assign numbers (`reset_ranges()`) and treat
  non-finite as "full extent".
- The module guards `main()` behind `MAGNIFY_NO_SERVE` so the data layer can be
  imported and tested headlessly.

## Next steps

- [ ] Interactive pass in the viewer: find the W channels of the dashed track,
      confirm ROI truncation against truth (port 5010 for production dnnsp).
- [ ] On port 5011, compare **gauss vs wiener vs dnnsp** on those same W
      channels: if gauss/wiener hold the charge where dnnsp does not, the loss
      is in DNNROI; if all three are short, it is upstream (decon/rebaseline).
- [ ] Check whether the W-plane dead/shorted-wire map overlaps the gap
      positions.

## Files in this folder

```
10-prolong-dashed-track-w.md      this document
scripts/extract-evt.fcl|.sh       extract run270/6/46 (entry 11) -> data/
scripts/detsim-sp-rerun.fcl       detsim+SP job (from the w-gap fcl; simdigits on,
                                  save_track_id off, fixed output name)
scripts/rerun-detsim-sp.sh        run it (WIRECELL_PATH fixes inside)
scripts/compare_wires_viewer.py   Bokeh viewer (copy of the w-gap tool)
scripts/serve-viewer.sh           launch a server (port 5010 / 5011)
scripts/make-magnify-cfg.sh       generate cfg/ override enabling the magnify sinks
scripts/magnify-dump.fcl          magnify job (roi=trad, save_simdigits=true)
scripts/run-magnify-dump.sh       run it -> data/magnify-270-6-46.root
cfg/pgrapher/experiment/sbnd/     the generated override (2 patched jsonnets)
scripts/magnify_viewer.py         Bokeh Magnify browser (2D stage + 1D all-stage)
scripts/serve-magnify-viewer.sh   run it (port 5012)
scripts/orient.py                 channel decode + BEE cluster gap scan
data/                             (gitignored) extracted event, SP re-run,
                                  BEE json, logs
```
