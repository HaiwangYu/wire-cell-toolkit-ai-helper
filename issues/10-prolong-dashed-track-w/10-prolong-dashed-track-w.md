# Issue 10 — dashed (broken-up) track on the W plane, BEE evt 29

Status: **four fixes shipped and validated on 10 MC + 10 data events**
(2026-08-12; both legs re-validated 2026-08-13 at the production ROI
thresholds, see Part 6). The prolonged-W-signal defect is fixed end to end;
two of the three originally dashed clusters remain unexplained (see Next
steps). Toolkit and sbndcode changes are **committed on `ap-yuhw` /
uncommitted on `wcp-porting` respectively, awaiting review** — this repo holds
only the documentation and scripts.

## BEE sets

Every set below shares the same index order, so **index *n* is the same physical
event in all four** — open ours and production at the same index to compare.

| set | link |
|---|---|
| MC, **ours** (all four fixes) | <https://www.phy.bnl.gov/twister/bee/set/185a6466-9926-4b8d-9727-2e9b3d6fd676/event/list/> |
| MC, **production** (pre-fix) | <https://www.phy.bnl.gov/twister/bee/set/ad1f4703-a047-46b2-be3f-d0eea8d69721/event/list/> |
| data, **ours** (all four fixes) | <https://www.phy.bnl.gov/twister/bee/set/1b13567d-7553-427b-a41a-c0f4b9df7eed/event/list/> |
| data, **production** (pre-fix) | <https://www.phy.bnl.gov/twister/bee/set/19951d4e-03bb-4b66-82d7-fcb9d2bfa1f4/event/list/> |

Both "ours" sets are the **2026-08-13 re-run at the production ROI
thresholds**. The superseded 2026-08-12 sets, which ran at troi 5.0/3.0 while
production ran 3.0/1.8, were MC `f21829e8-4e3e-427c-bdaa-9e871ce727b3` and
data `03b41975-7f1b-4069-976c-33ba7e9e8b30`; see Part 6 for what that changed
and what it did not.

idx 0–9, MC: 270/6/{11,12,13,14,30,33,34,37,38,46} —
data: 18259/1/{107100,107386,107694,107716,107738,107892,108882,109762,109960,110026}.

Earlier single-event A/B sets from the NF investigation:
with-NF `8db09746-6cfc-46a1-bde9-4f79ef864666`, no-NF
`528e80f1-489d-41f9-ae11-d1168fcba5ba`, all-fixes
`9d174713-c6da-4e30-b386-778c814fb823` (all index 0 = run 270/6/46), and the
original symptom set `84854901-3b51-4f71-81a7-1f041ad4d867` event 29.

## The four fixes, in one place

| # | change | file | why |
|---|---|---|---|
| 1 | `partial_enable: false` | `sbnd/nf.jsonnet` (sim) | disables the IS_RC false positive; keeps RC-RC deconvolution on every channel |
| 1b | `partial_enable: false` | `sbnd/nf-data.jsonnet` | same, for the data chain — a *different* file from nf.jsonnet, and one the toolkit lacked entirely until 2026-08-13 |
| 2 | `max_rms_cut: 30 → 100` (W) | `sbnd/chndb-base.jsonnet` | **required**: without it the un-flattened signal trips `NoisyFilterAlg` and the channel is zeroed |
| 3 | `roi_mad_rms: true` | `sbnd/sp.jsonnet` | MAD-based `ROI_formation::cal_RMS` |
| 4 | `r_break_roi_loop_planes: [2,2,0]` | `sbnd/sp.jsonnet` | no BreakROI on collection |

Plus `Microboone.{h,cxx}`: `OneChannelNoise` becomes `IConfigurable`
(`partial_enable`, `partial_signal_blind`, `partial_nfreqs`, `partial_maxpower`)
and records a `partial` mask on all planes.

**Where they live.** All four are in both trees as of 2026-08-13, and
`sp.jsonnet` is now byte-identical between them (Part 6):
`wire-cell-toolkit` on branch `ap-yuhw`, committed —
`b8086bd6` (the four fixes + the C++), `13ed5167` (`nf-data.jsonnet`),
`06a02ccb` (the `sp.jsonnet` merge); `sbndcode` on `wcp-porting`,
**uncommitted**, touching `sp.jsonnet`, `nf.jsonnet`, `nf-data.jsonnet`,
`chndb-base.jsonnet` and `wcls-nf-sp.jsonnet`. The two trees are a permanent
fork — sync knob-by-knob, never file-by-file.

3 and 4 already existed upstream
(Xin's PDHD commit `50239595`) and were simply never enabled for SBND.

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

## NF investigation — state, and how to resume

**Status: the NF defect is diagnosed and reproduced; the fix in
`wire-cell-toolkit/sigproc/src/Microboone.cxx` is NOT written yet.**
The RC-RC deconvolution in NF is wanted, so the NF must stay — only the
`IS_RC`/adaptive-baseline branch needs fixing.

### The defect
`Microboone::OneChannelNoise::apply(int ch, signal_t&)` (~line 918):

```cpp
bool is_partial = m_check_partial(spectrum);        // Xin's "IS_RC()"
if (!is_partial) { shrink(spectrum, rcrc(ch)); }    // RC-RC deconv SKIPPED when partial
...
if (is_partial) { SignalFilter(signal); RawAdapativeBaselineAlg(signal); }
```
`Diagnostics::Partial` (`sigproc/inc/WireCellSigProc/Diagnostics.h`,
`sigproc/src/Diagnostics.cxx`) fires when the 5 lowest non-DC FFT bins are large
and monotonically falling — the signature of a long, large ionisation pulse:

```cpp
mag0 = |spec[1]|;
for (ind=1..nfreqs) if (mag0 <= |spec[ind+1]|) return false;
return sum/(nfreqs+1) > maxpower;      // nfreqs=4, maxpower=6000, HARD-CODED in the ctor
```
`RawAdapativeBaselineAlg` then applies a **20-tick (~10 µs) sliding-window
baseline**, removing anything slower that `SignalFilter` (|x| > 4×robust-RMS,
±8-tick pad) did not flag. On collection the code records **no mask**
(`if (iplane != 2)`), so the damage leaves no trace downstream.

### Reproduction numbers (run 270/6/46)
| | |
|---|---|
| channels tripping IS_RC | **5**: 4214, 4219 (W/APA0); 10038, 10039, 10040 (W/APA1) |
| ch 10038 truth-restricted `|raw|/|orig|` | **0.098** (2.9e6 e⁻, 1038 signal ticks) |
| ch 10039 | 0.567 (817 ticks) |
| ch 4214 / 4219 / 10040 (≤325 ticks) | 0.99 / 1.03 / 0.91 — unaffected |
| all other W channels (n=1060) | **1.0007** median |
| ch 10038 `gauss` sum, NF on → NF removed | **1.086e5 → 4.604e5 (4.2×)** |

Damage scales with signal **duration**, exactly as a 20-tick window predicts.

### Files to resume from
```
data/magnify-270-6-46.root        with-NF magnify dump (12 SP stages)
data/magnify-270-6-46-nonf.root   no-NF dump (no `raw` stage; NF removed)
data/evt-270-6-46_sp.root         with-NF SP (roi=both, has dnnsp_ReDetSim)
data/evt-270-6-46_nonf_sp.root    no-NF SP
data/evt-270-6-46_magnifyjob.root SimChannel truth matched to the with-NF dump
cfg/…/wcls-sim-drift-depoflux-nf-sp.jsonnet   currently has nf_pipes REMOVED
cfg/…/*.with-nf.bak                            the with-NF version of that cfg
scripts/nf_signal_loss.py         truth-restricted loss metric (Test 2)
scripts/run-nonf.sh, run-img-clus.sh, img-clus-rerun.fcl   the A/B chain
```
**To restore NF** for testing a fix: `cp cfg/…/wcls-sim-drift-depoflux-nf-sp.jsonnet.with-nf.bak`
over the working copy (or re-run `scripts/make-magnify-cfg.sh`, which regenerates
it from CVMFS with the magnify sinks enabled and NF intact).

### Verification recipe for any fix
1. rebuild WCT on `ap-yuhw` (`scripts/build_wct.sh` pattern; ~5 min, run it
   **foreground with a long timeout** — backgrounded builds got killed),
2. re-run `scripts/run-magnify-dump.sh` (NF restored) and check ch 10038:
   `is_partial` should be false, `raw` should keep the pulse, and `gauss` should
   approach the no-NF **4.6e5** while the RC deconvolution still runs,
3. regression: the other four channels unchanged, and non-partial channels still
   at `|raw|/|orig|` ≈ 1.0007.

### Not the dashed-track cause
A full A/B with `nf_pipes` deleted leaves the dashes identical (~95 cm track
11→13 gaps, gapfrac 0.860→0.827; ~124 cm 10→10; ~60 cm 5→5). BEE: no-NF
`528e80f1-489d-41f9-ae11-d1168fcba5ba`, with-NF `8db09746-6cfc-46a1-bde9-4f79ef864666`.
The dashes come from downstream (ROI/DNNROI or the imaging 3-view coincidence).

## The fix — shipped, verified (2026-08-11)

Two changes, both **uncommitted, for review**. WCT tree
`/exp/sbnd/app/users/yuhw/wire-cell-toolkit` (branch `ap-yuhw`).

### 1. Expose the IS_RC knobs and turn the branch off for SBND

`sigproc/{inc/WireCellSigProc,src}/Microboone.{h,cxx}` — `OneChannelNoise` gains
an `IConfigurable` implementation so the magic numbers buried in
`Diagnostics::Partial`'s constructor become configuration:

| knob | default | meaning |
|---|---|---|
| `partial_enable` | `true` | `false` disables the branch, so the RC-RC deconvolution runs on **every** channel |
| `partial_signal_blind` | `false` | judge IS_RC on a signal-suppressed copy instead of the raw spectrum |
| `partial_nfreqs` | `4` | former `Diagnostics::Partial` ctor arguments |
| `partial_maxpower` | `6000` | |

`Diagnostics.h` is deliberately **not** touched — its `Partial` has const members
and is shared by Protodune/ProtoduneHD/ProtoduneVD/DuneCrp/Icarus/Microboone.
Also added `ret["partial"][ch]` on **all** planes: the pre-existing `lf_noisy`
mask is induction-only, so a rewritten collection channel left no trace anywhere
— that is why this went unnoticed for so long. No maskmap sends `partial` to
`bad`, so it changes no behaviour.

`cfg/pgrapher/experiment/sbnd/nf.jsonnet` sets **`partial_enable: false`**.

**On `partial_signal_blind`: implemented, but defaulted OFF, and it does not
work here.** The probe suppresses signal with `SignalFilter` before judging.
That cleared four of the five false positives (10039, 10040, 4214, 4219 all
flip True→False, and 10036/10037 correctly stay False), but **fails on 10038**,
the very channel it was written for: the pulse is broad enough that
`CalcRMSWithFlags` returns 49.6 ADC, so the 4× threshold of 198 ADC flags
*nothing* and the probe equals the raw waveform. Estimators immune to that
feedback fail the other way — `median|first difference|` is pinned at 1 by ADC
quantisation, and an HF-band RMS reads ~0.9 against a true ~2–3 because SBND
noise is LF-dominated; both then mask 75–98 % of even a quiet channel, i.e. they
disable the test by stealth. **Within one channel, a big slow ionisation pulse
and an RC-droop pathology are not reliably separable.** Doing so needs
cross-channel coherence (unavailable in the per-channel `apply` overload) or a
requirement that the slow structure span the whole readout.

### 2. Raise the W-plane `max_rms_cut` (this one is required)

Turning the partial branch off alone made ch 10038 **worse — zeroed entirely**.
With the signal no longer flattened by the adaptive baseline, it reached
`NoisyFilterAlg`, whose RMS also comes from `CalcRMSWithFlags`, so the *same*
signal-inflated estimator fired the noisy cut → `maskmap noisy:"bad"` → channel
deleted. The old code was, in effect, saving the channel from the noisy cut by
destroying its signal first.

Measured over the whole event: every live W channel sits at **2.0–10.1**, and
ch 10038 is the **only** channel anywhere above 30 — at 49.0, purely from
signal. So `chndb-base.jsonnet` sets `max_rms_cut: 100.0` on the W block
(still ~10× the noise floor, with headroom above any real pulse).

### Verification (`data/magnify-270-6-46-fixed.root`, both fixes in)

| ch | orig-NF `gauss` | fixed `gauss` | no-NF `gauss` |
|---|---|---|---|
| 10038 | 1.086e5 | 3.29e4 | 4.604e5 |
| 10039 | 5.728e5 | **9.077e5** | 8.356e5 |
| 10040 | 3.00e5 | **3.427e5** | 3.254e5 |
| 4214 | 7.598e5 | **7.962e5** | 7.361e5 |
| 4219 | 7.177e5 | **7.277e5** | 6.788e5 |

- Four of five channels now match or exceed the no-NF reference, **with** the RC
  deconvolution applied.
- ch 10038's `raw` is preserved (p-p 228 vs orig 245; was 112) and its RC droop
  is correctly removed (baseline-subtracted 100-tick blocks: orig tail
  −40…−1 → fixed −5…−8). Its `decon_charge` recovers 3.07e5 → **3.08e6**
  (no-NF 3.39e6). **The NF is doing the right thing on this channel now.**
- No channel is newly zeroed (W/APA0 43→43, W/APA1 9→9). The ±20–30 U/V churn
  between runs is noise-realisation jitter — the sim is not seed-reproducible,
  totals 329→327.
- Globally neutral: total `sum|gauss|` = 2.9571e8 (orig-NF), **2.9587e8**
  (fixed), 2.9600e8 (no-NF) — 0.1 % spread.

### Residual, and it is NOT in the NF

ch 10038's `gauss` is still low because its ROI now dies in **SP**, at
`break_roi_1st` (9 ticks, vs 64 no-NF, 195 orig-NF). Same pathology a third
time: `ROI_formation`'s threshold is a multiple of a percentile RMS of the
deconvolved waveform, and on this channel that RMS is **2036** (fixed) / 1630
(no-NF) against 62–95 on a normal channel, so signal/RMS is 3.6–4.0 versus ~82
and almost no ROI forms. Note it is **equally punitive in the no-NF baseline**,
so it is pre-existing and not caused by these changes. The orig-NF run only
*looked* better here (195 ROI ticks) because the adaptive baseline had already
destroyed the signal, dropping the RMS to 66 — it carried 4× less charge.

So ch 10038 is a channel whose signal fills enough of the readout that **every**
percentile-based RMS estimator in the chain is inflated by the signal itself:
NF `SignalFilter` → NF `NoisyFilterAlg` → SP `ROI_formation`. The first two are
fixed; the third is a separate ticket, and it is in the same ROI stage already
suspected for the dashed track.

### Discussion point for the future (raised by HY)

`is_partial` currently *also* skips the RC deconvolution. On a false positive
that is a double penalty: the signal is flattened **and** the real RC droop is
never corrected. Since the RC deconvolution is wanted, consider applying
`shrink(spectrum, rcrc)` unconditionally and letting the partial branch affect
only the baselining. `partial_enable: false` gets SBND the same outcome today,
but the unconditional form would be the better upstream default.

## Part 3 — the SP ROI fix already existed; enabled for SBND (2026-08-11)

The residual above is the *same defect Xin already fixed for ProtoDUNE-HD*:
commit `50239595` "sigproc: MAD-based cal_RMS + collection BreakROI disable
(prolonged-W fix)", diagnosed on run 027409 evts 40920/40924 (RMS 1594/1769 vs
170/186 signal-free, ~10× inflation). It shipped two knobs, **both default ON in
the pdhd/pdvd configs and neither set by SBND**:

- `roi_mad_rms` (OmnibusSigProc, C++ default `false`) — `ROI_formation::cal_RMS`
  first pass becomes median-absolute-deviation × 1.4826, robust to 50 %
  occupancy instead of breaking past ~16 %.
- `r_break_roi_loop_planes: [2, 2, 0]` — no BreakROI on collection, where its
  valley-to-valley linear "baseline" is actually real track charge.

`cfg/pgrapher/experiment/sbnd/sp.jsonnet` now sets both. SBND uses the standard
[U, V, W] slot order on both anodes (no `filter_responses_tn` remap), so W is
slot 2; override `r_break_roi_loop_planes: [2,2,2]` to revert. Doc:
`wcp-porting-img/pdhd/docs/sp-w-collection-roi-break.md`.

### What `roi_mad_rms` actually changes

`ROI_formation::cal_RMS` estimates a channel's **noise** level, and the ROI
threshold is a multiple of it —
[`threshold = th_factor_col * rms + 1`](https://github.com/WireCell/wire-cell-toolkit/blob/50239595cfe25f3fa40f287ceae23e58aa9d4333/sigproc/src/ROI_formation.cxx#L472)
for collection (`th_factor_col` = 5 for SBND). It runs in two passes; the knob
changes only the **first**:

| | first pass (the knob) | second pass (unchanged) |
|---|---|---|
| off (legacy) | (16, 50, 84) percentile spread: `sqrt(((p84-p50)² + (p50-p16)²)/2)` | truncated second moment over the samples with `\|x\| < 5*rms` |
| on | **MAD** × 1.4826 | same |

**MAD = median absolute deviation** = `median( |xᵢ − median(x)| )`
([code](https://github.com/WireCell/wire-cell-toolkit/blob/50239595cfe25f3fa40f287ceae23e58aa9d4333/sigproc/src/ROI_formation.cxx#L369-L381)).
For Gaussian noise MAD ≈ 0.6745σ, so **1.4826 × MAD** is the σ-equivalent — the
factor exists purely so the downstream `5*rms` cut and the `th_factor`
thresholds keep the meaning they had before.

Why it matters here is the **breakdown point** — the fraction of the samples that
can be arbitrary before the estimator itself is corrupted:

- the percentile spread breaks down past **~16 %** occupancy, because the 84th
  percentile walks up into the signal and inflates `p84 - p50`;
- MAD tolerates up to **50 %**, since the median of the absolute deviations only
  moves once signal occupies half the waveform.

A prolonged W track along the drift direction fills far more than 16 % of one
channel's readout, so the legacy estimate reports the *signal* as noise, the
threshold rises above the signal's own median, and almost no ROI forms. Measured
on ch 10038 of run 270/6/46: decon RMS **2036** versus 62–95 on a normal W
channel, i.e. signal/RMS 3.6 against ~82, and `break_roi_1st` collapsed to 9
ticks. Note the second pass cannot rescue it — it is seeded from the first pass's
`rms`, so a 20× inflated seed keeps essentially every sample inside the `5*rms`
window.

Upstream source (all links pinned to commit
[`50239595`](https://github.com/WireCell/wire-cell-toolkit/commit/50239595cfe25f3fa40f287ceae23e58aa9d4333),
which is on `origin/master` and `origin/0.37.x`):

| what | link |
|---|---|
| `cal_RMS`, both passes | [`sigproc/src/ROI_formation.cxx#L364-L403`](https://github.com/WireCell/wire-cell-toolkit/blob/50239595cfe25f3fa40f287ceae23e58aa9d4333/sigproc/src/ROI_formation.cxx#L364-L403) |
| the MAD branch | [`#L369-L381`](https://github.com/WireCell/wire-cell-toolkit/blob/50239595cfe25f3fa40f287ceae23e58aa9d4333/sigproc/src/ROI_formation.cxx#L369-L381) |
| threshold use site | [`#L464-L472`](https://github.com/WireCell/wire-cell-toolkit/blob/50239595cfe25f3fa40f287ceae23e58aa9d4333/sigproc/src/ROI_formation.cxx#L464-L472) |
| `use_mad_rms` member / setter | [`sigproc/src/ROI_formation.h#L68`](https://github.com/WireCell/wire-cell-toolkit/blob/50239595cfe25f3fa40f287ceae23e58aa9d4333/sigproc/src/ROI_formation.h#L68), [`#L103`](https://github.com/WireCell/wire-cell-toolkit/blob/50239595cfe25f3fa40f287ceae23e58aa9d4333/sigproc/src/ROI_formation.h#L103) |
| `roi_mad_rms` config → setter | [`OmnibusSigProc.cxx#L96`](https://github.com/WireCell/wire-cell-toolkit/blob/50239595cfe25f3fa40f287ceae23e58aa9d4333/sigproc/src/OmnibusSigProc.cxx#L96), [`#L1858`](https://github.com/WireCell/wire-cell-toolkit/blob/50239595cfe25f3fa40f287ceae23e58aa9d4333/sigproc/src/OmnibusSigProc.cxx#L1858) |
| `r_break_roi_loop_planes` | [`OmnibusSigProc.cxx#L125-L127`](https://github.com/WireCell/wire-cell-toolkit/blob/50239595cfe25f3fa40f287ceae23e58aa9d4333/sigproc/src/OmnibusSigProc.cxx#L125-L127) |

The same estimator problem appears twice more in the NF, both on the *raw* rather
than deconvolved waveform, via
[`Microboone::CalcRMSWithFlags`](https://github.com/WireCell/wire-cell-toolkit/blob/50239595cfe25f3fa40f287ceae23e58aa9d4333/sigproc/src/Microboone.cxx#L549-L571)
— the same (16, 50, 84) spread — used by
[`SignalFilter`](https://github.com/WireCell/wire-cell-toolkit/blob/50239595cfe25f3fa40f287ceae23e58aa9d4333/sigproc/src/Microboone.cxx#L573)
(threshold 4×rms) and
[`NoisyFilterAlg`](https://github.com/WireCell/wire-cell-toolkit/blob/50239595cfe25f3fa40f287ceae23e58aa9d4333/sigproc/src/Microboone.cxx#L468)
(the `max_rms_cut` that fix #2 addresses). Those two have no MAD option — fixes
1 and 2 sidestep them rather than re-estimating.

### Validated against SimChannel truth (same job)

This is the metric that should have been used all along — the no-NF run was
**not** a valid reference, since it suffers the identical ROI pathology.

| ch | true charge (e-) | NF orig | NF fix only | **+ ROI knobs** | no-NF |
|---|---|---|---|---|---|
| 10038 | 2.934e6 | 0.04× | 0.01× | **1.01×** | 0.16× |
| 10039 | 1.332e6 | 0.43× | 0.68× | **1.01×** | 0.63× |
| 10040 | 3.382e5 | 0.89× | 1.01× | **1.01×** | 0.96× |
| 4214 | 7.881e5 | 0.96× | 1.00× | **1.00×** | 0.93× |
| 4219 | 7.282e5 | 0.99× | 1.00× | **1.00×** | 0.93× |
| 10036 | 6.068e5 | 1.01× | — | 1.01× | 0.98× |
| 10037 | 1.367e6 | 0.99× | — | 1.01× | 0.90× |

ch 10038's `gauss` goes 1.086e5 → **2.975e6** against a truth of 2.934e6. The
large jump is not an overshoot: the channel was previously reconstructing 4 % of
its charge.

### Global regression (all channels with true charge > 5e4 e-)

| plane | metric | NF fix only | **+ ROI knobs** | no-NF |
|---|---|---|---|---|
| W | total gauss/truth | 0.964 | **0.998** | 0.950 |
| W | frac channels < 0.5 | 0.010 | **0.006** | 0.008 |
| U | total gauss/truth | 0.881 | 0.881 | 0.888 |
| V | total gauss/truth | 0.983 | **0.908** | 1.010 |
| V | median gauss/truth | 1.064 | 0.991 | 1.078 |

W is the win and it is unambiguous (0.2 % from truth in total, fewer badly
reconstructed channels). U is untouched. V loses 7.5 % of total charge in
**`gauss`** — `roi_mad_rms` is a global bool applying to all planes, and on the
bipolar induction decon MAD is not the same estimator (V's *median* moves toward
truth, 1.064 → 0.991, so it is partly a trade of over-collection for
under-collection).

**That V number does NOT reach the reconstruction** — see §"What imaging
actually consumes" below. `gauss` on V is read by nothing in this chain, so no
per-plane `roi_mad_rms_planes` knob is needed on its account.

### What imaging actually consumes: `dnnsp`, and W is a shunt

`sbnd/dnnroi.jsonnet`: U (plane 0) and V (plane 1) go through the DNN with
`intags = [loose_lf, mp2_roi, mp3_roi]` + `decon_charge_tag`; **plane 2 (W) is
shunted** — `tags: ["gauss%d"]` retagged straight to `dnnsp%dw`. So the W plane
inside `dnnsp` *is* the traditional gauss, which is why these fixes propagate to
the imaging/BEE result at all. `img-clus-rerun.fcl` reads
`simtpc2d:dnnsp:ReDetSim`.

`dnnsp` vs truth per plane (`recob::Wire` × `DeconNorm` 50; truth > 5e4 e-):

| variant | U | V | W |
|---|---|---|---|
| with-NF (original) | 0.9492 | 0.9151 | 0.9638 |
| **all fixes** | 0.9507 | **0.9198** | **0.9983** |
| no-NF | 0.9613 | 0.9304 | 0.9502 |

W in `dnnsp` reproduces the gauss numbers exactly (ch 10038 0.04× → 1.01×), as
the shunt implies. **V is marginally better, not worse** (0.9151 → 0.9198): the
DNN does not consume gauss, so the gauss-V regression above is invisible here.

### Environment breakage hit during this run (not ours)

At **14:57 today** the SBN CVMFS repo republished `larcv2 v2_2_6`'s ups table
with its `e26` blocks requiring root **v6_28_10b**, while `art_root_io v1_13_06`
in the same dependency tree requires **v6_28_12**. `setup sbndcode
v10_14_02_03 -q e26:prof` then fails with *"Version conflict … root: versions
v6_28_10b vs v6_28_12"* and `lar` never reaches PATH — in a clean shell, so it
hits every SBND e26 user, not just this work. Workaround in
`wcp-porting-img/sbnd/setup-local-opt.sh`: `$UPS_PATCHES`
(`/exp/sbnd/app/users/yuhw/opt/ups-patches`) holds a larcv2 version+table copy
with the e26 lines put back to v6_28_12 (the state that worked until 14:57),
`PROD_DIR` still pointing at the CVMFS install, prepended to `PRODUCTS`
**before** `setup sbndcode`. Delete that directory to drop the workaround.
Worth reporting upstream.

## Part 4 — img/clus/matching + BEE with all fixes: the dashes (2026-08-11)

The magnify job runs `roi:"trad"` and drops `dnnsaver`, so its art output has no
`dnnsp` product and cannot feed the img chain. New `scripts/rerun-fixed-sp.fcl`
+ `scripts/run-fixed-sp.sh` re-run SP with `roi:"both"` against the same fixed
cfg override → `data/evt-270-6-46_fixed_sp.root` (27 MB), then
`scripts/run-img-clus.sh` → `data/img-clus-fixed/mabc.zip` (3.5 MB).
`run-fixed-sp.sh` moves only its own output up into `data/` — the override
jsonnet still hard-codes `magoutput=magnify-270-6-46-fixed.root`, so a blanket
`mv *.root` (as in `run-nonf.sh`) would clobber the verified magnify dump.

**BEE, all three fixes: `9d174713-c6da-4e30-b386-778c814fb823`**
(with-NF original `8db09746-6cfc-46a1-bde9-4f79ef864666`, no-NF
`528e80f1-489d-41f9-ae11-d1168fcba5ba`; all index 0 = run 270/6/46.)

### Gap scan on `clustering-global` (cids match between with-NF and all-fixes)

| cluster | with-NF (original) | **all fixes** |
|---|---|---|
| cid 15, ~124 cm | 583 pts, gapfrac **0.549**, maxgap 17.7 cm, 9 gaps >3 cm | 941 pts, gapfrac **0.311**, maxgap 11.6 cm, 6 gaps >3 cm |
| cid 7, ~97 cm | 378 pts, gapfrac 0.860, maxgap 20.7 cm | 377 pts, 0.860, 20.7 cm |
| cid 12, ~61 cm | 299 pts, gapfrac 0.720, maxgap 26.2 cm | 298 pts, 0.721, 26.2 cm |

**One of the three dashed tracks is substantially repaired** — cid 15 gains 61 %
more points and its gap fraction nearly halves. That is the track crossing the
prolonged-signal channels (10038/10039 are its W channels). **cid 7 and cid 12
are untouched**, so they have a different cause: the prolonged-signal ROI
pathology only fires where a single channel carries a long, large pulse, and
these two tracks never trigger it. Their dashes remain unexplained — the earlier
conclusion that the dashes are not an NF problem still stands for them.

## Part 5 — validation campaign, 10 MC + 10 data (2026-08-12)

> **Superseded by Part 6.** Every number in this Part was measured with SP
> running at tight-ROI thresholds 5.0/3.0 while production ran 3.0/1.8 — an
> `sp.jsonnet` divergence that failed silently. The *method* below is still
> current and the MC before/after deltas still hold (both legs shared one cfg),
> but for ours-vs-production and ours-vs-truth ratios use Part 6.

Folder `data/validation-20260812/` (gitignored): `mc/<run>-<subrun>-<event>/` and
`data/<run>-<subrun>-<event>/`, each holding `sp.root` (gauss + dnnsp + wiener),
`magnify.root` (12 SP stages), `mabc.zip`, and per-stage logs. Scripts:
`campaign-{sp,img,sp-data,img-data}.sh` (one event each), `campaign-driver.sh`
(leg-aware, `SUB=mc|data`), `campaign-bee.sh` (merge a leg's zips into one BEE
set, re-indexing 0..N-1), `campaign-splist.sh`, `campaign-validate-mc.py`,
`campaign-partial-census.py`.

**Core budget.** WCT runs `TbbFlow`, whose TBB pool defaults to *hardware
concurrency* (64 here) — `OMP_NUM_THREADS` does not bound it. Each worker is
pinned with `taskset` to a 2-core pair, 4 workers = 8 cores.

### MC leg — 10 events, all complete

`gen_g4_detsim_reco1-a5f42e7e-...root` holds only 12 events and **270/6/46 is the
last** (entry 11), so the 10 are entries 2–11, the contiguous block ending with
our event: 270/6/{11,12,13,14,30,33,34,37,38,46}.

**BEE: `f21829e8-4e3e-427c-bdaa-9e871ce727b3`** (idx 0–9 in that order).

Reconstructed charge vs SimChannel truth, channels with >5e4 e- of true charge:

| plane | channels | gauss/truth | dnnsp/truth | channels <0.5 |
|---|---|---|---|---|
| U | 7758 | 0.9726 | 0.9779 | 85 (1.10 %) |
| V | 8527 | 0.9664 | 0.9465 | 278 (3.26 %) |
| W | 6542 | **0.9891** | **0.9891** | 83 (1.27 %) |

Per-event W ranges 0.962–0.999 with per-channel median ~1.000. **W `gauss/truth`
equals `dnnsp/truth` in every single event** — an independent confirmation that
`dnnroi.jsonnet` shunts plane 2 (`dnnsp*w` *is* gauss).

### Before/after without re-running the pre-fix chain

`campaign-partial-census.py` re-applies `Diagnostics::Partial` (nfreqs=4,
maxpower=6000 — the numbers the un-patched `Microboone.cxx` hard-coded) to each
event's `orig` waveforms. Every channel it flags is one the old NF would have
flattened with `RawAdapativeBaselineAlg` *and* denied the RC deconvolution:

| event | flagged, carrying charge | now >0.8 of truth | min | median |
|---|---|---|---|---|
| 270-6-11 | 20 | 18 | 0.631 | 0.991 |
| 270-6-13 | 3 | 3 | 0.991 | 1.011 |
| 270-6-14 | 1 | 1 | 1.006 | 1.006 |
| 270-6-30 | 7 | 7 | 0.996 | 1.001 |
| 270-6-33 | 10 | 10 | 1.000 | 1.005 |
| 270-6-37 | 2 | 2 | 1.002 | 1.004 |
| 270-6-46 | 6 | 6 | 0.993 | 1.006 |
| 270-6-12 / 34 / 38 | 0 | — | — | — |

**49 channels across 10 events; 47 (96 %) now reconstruct >0.8 of truth.** The
per-event count swings 0–20, so the defect was firing on most events, not just
the one that surfaced it.

### Data leg — how it had to be built

Three discoveries, each a blocker:

1. **Production data reco1 keeps no `raw::RawDigit`** — checked the filtered file,
   its unfiltered parent, and all 495 artdaq fragment branches (generic type
   placeholders, no TPC waveforms). So NF+SP cannot be re-run on it.
2. **No decoded sample exists on tape.** `samweb get-metadata` shows the fcl chain
   `run_decoders_job.fcl/.../reco1_data.fcl/reco2_data.fcl/cafmaker...` ran as ONE
   job, and `file-lineage parents` gives the raw EventBuilder file directly —
   the same gen→reco1 chaining that forced the MC re-run.
3. **The given file's 48 events come from 47 different production files** across 12
   runs, so "10 of its events" would mean ~10 separate raw parents. Chose instead
   the 10 events of the single raw parent already verified ONLINE:
   `data_EventBuilder6_art2_run18259_14_strmBNBLight_20250219T075652.root`
   (run 18259, 50 events, 1.01 GB) — run 18259 is one of the 12.

`scripts/decode-data.fcl` decodes 10 events and applies frameshift. Two
dependencies had to be added by hand, each found by running it:
`crtstrips` (FrameShift wants `raw::TimingReferenceInfo`, which in production
comes from reco1 — frameshift itself runs in *reco2*), then the CRT service set
(`CRTGeoService`, `CRTCalibrationDatabase`; the decoder job carries only the
channel map). Output: `decoded.root`, 268 MB, with `raw::RawDigits_daq__DECODE`
and `FrameShiftInfo`.

**Do the fixes reach data?** `wcls-nf-sp-data.jsonnet` imports `chndb-base.jsonnet`
(the W `max_rms_cut`) and `sp.jsonnet` (`roi_mad_rms`, `r_break_roi_loop_planes`),
so three of four applied already. But NF for data comes from **`nf-data.jsonnet`**,
a *different file from the `nf.jsonnet` I patched* — and one that lives only in
sbndcode, not in the WCT tree. Patched copy with `partial_enable: false` is in the
override dir. **Upstream this means the SBND cfg fixes belong in sbndcode's
`wire-cell-cfg`, not (only) in wire-cell-toolkit/cfg.**

The data magnify dump needed the same jsonnet surgery as the sim one: sinks
uncommented in the `roi=="trad"` branch, `use_roi_debug_mode: true` added to the
bare `else { sparse: true }` override, `magoutput` fixed. Note `roi=="both"` also
wires `sinks.decon_pipe`, so the sp job writes a decon-only `magnify.root` that
the trad job then overwrites — run sp first.

A third blocker appeared only at the img stage: every job died with
**`OpFlashSource failed to get opflashes`**. QL matching needs `recob::OpFlash`,
built by the reco1 *optical* producers, which the decoder job does not run. No
recompute of SP was needed — `sp.root` already carries
`raw::OpDetWaveforms_pmtdecoder_*`, so `scripts/opreco-data.fcl` (process name
`OPRECO`; `wfalign, opdecopmt, ophitpmt, opflashtpc0, opflashtpc1`) builds the
flashes on top of it and img runs on the resulting `spflash.root`.

### Data leg results — 10 events, all complete

**BEE: `03b41975-7f1b-4069-976c-33ba7e9e8b30`** (idx 0–9 =
18259/1/{107100,107386,107694,107716,107738,107892,108882,109762,109960,110026}).

Data has no truth, so the reference is the **production** reco1 dnnsp for the same
events (made with the pre-fix configuration), read from
`.../reco1/bnblight/fe/data_filtered_decoded_reco1-fe6033f3-...root`
(`campaign-validate-data.py`):

| plane | ours / production, all channels | on the old-IS_RC-flagged channels |
|---|---|---|
| U | 1.0016 | — |
| V | 1.0020 | — |
| W | **1.0042** | **1.146× on 76 channels** |

So on real data the fixes are globally invisible (0.2–0.4 % on every plane) and
recover ~15 % of the charge precisely on the channels the defect was eating.
Per-event standouts: 107716 (9 flagged W channels, **2.49×**), 107892 (5, 1.93×),
109960 (12, 1.10×), 110026 (29, 1.04×).

### Production BEE sets (the pre-fix reference)

The same img → clus → QL matching chain run directly on the **production reco1**
files, event-for-event and index-for-index with our re-run sets, so BEE can be
compared side by side at the same index. Production carries everything the chain
needs — dnnsp, `wienersummary`, `badmasks`, opflashes, and for MC the
SimChannels/MCParticles the labeler wants — so no re-processing was involved.
`scripts/img-clus-prod-{mc,data}.fcl` just point the tags at the production
instances (MC: module `simtpc2d`, process **DetSim**, since SP ran inside the
chained gen_g4_detsim_reco1 job; data: module `sptpc2d`, process **Reco1**), and
`campaign-img-prod.sh` runs one event with `--nskip`.

| set | BEE |
|---|---|
| MC, ours (fixed) | `f21829e8-4e3e-427c-bdaa-9e871ce727b3` |
| MC, production (pre-fix) | **`ad1f4703-a047-46b2-be3f-d0eea8d69721`** |
| data, ours (fixed) | `03b41975-7f1b-4069-976c-33ba7e9e8b30` |
| data, production (pre-fix) | **`19951d4e-03bb-4b66-82d7-fcb9d2bfa1f4`** |

All four share the same index order (verified by diffing the index maps):
idx 0–9 = 270/6/{11,12,13,14,30,33,34,37,38,46} for MC and
18259/1/{107100,107386,107694,107716,107738,107892,108882,109762,109960,110026}
for data, so index *n* is the same physical event in every set.

### Viewing the campaign

`scripts/campaign-splist.sh` writes `sp-list.txt` (20 files, MC then data).
`compare_wires_viewer.py` now takes a list and steps through it:

```bash
scripts/serve-viewer.sh 5011 --list <campaign>/sp-list.txt gauss dnnsp
```
**Two loading modes** (`mode` selector). A and B are independent
`(file, event, tag)` triples — necessary because a production file holds a whole
run segment while each validation output holds one event at entry 0.

- **manual** — type file A/B, event A/B, tag A/B, press `Load`.
- **list** — read those six fields from a file, one comparison per row, and walk
  it with `<< prev entry` / `next entry >>`.

List format (whitespace or comma separated, `#` comments, trailing `#label`
shown while navigating):

```
fileA fileB eventA eventB tagA tagB   # label
file                                  # 1 column: A=B=file, event 0, UI tags
```
The 1-column form keeps the older `sp-list.txt` working. `< prev event` /
`next event >` still step both event indices together, each clamped to its own
file. Remember W `dnnsp` *is* `gauss` (plane-2 shunt) — the real A/B there is
against truth or production.

**Campaign comparison lists** (`campaign-cmplists.py`), A = **production**
(pre-fix), B = **our re-run**, both `dnnsp`, so the A−B panel is negative wherever
the fixes recovered charge:

| list | rows | A | B |
|---|---|---|---|
| `cmp-mc-list.txt` | 10 | `gen_g4_detsim_reco1-a5f42e7e-...root` entries 2–11 | `mc/<rse>/sp.root` entry 0 |
| `cmp-data-list.txt` | 10 | `data_filtered_decoded_reco1-fe6033f3-...root` | `data/<rse>/sp.root` entry 0 |

Both sides are matched by run/subrun/event, not by position. Spot-checked:
MC row 1 = production entry 2 and our entry 0, both 270/6/11 (ΣB/ΣA = 1.0146);
data row 1 = both 18259/1/107100 (0.9983).

```bash
scripts/serve-viewer.sh 5011 --list <campaign>/cmp-mc-list.txt dnnsp dnnsp
```

**bokeh gotcha:** `on_change` validates the callback signature *exactly* — three
required positional parameters. Neither `func(*_)` nor
`func(attr=None, old=None, new=None)` is accepted; both raise
"Callback functions must have signature func(attr, old, new)" at app build time,
which surfaces as a blank page while the HTTP request still returns 200.

**MC/data toggle** (`sample`: auto | MC | data). The WCT producer is labelled
`simtpc2d` in simulation and **`sptpc2d` in data**, and data has no
`sim::SimChannel`, so the viewer picks the producer label from this setting and
skips the truth overlay entirely for data (rather than attempting the lookup and
logging a miss on every event). `auto` decides per file — which is what the mixed
MC-then-data campaign list needs — by looking for `sptpc2d` vs `simtpc2d` wire
branches, falling back to the presence of SimChannels when both or neither are
found. The info line reports which way it resolved and whether it was forced.
Process preference when a tag exists from several processes is now
`ReDetSim` (MC re-run) then `WCLS` (data re-run), ahead of the production
`DetSim`/`Reco1` instance. Verified: MC `sp.root` → `simtpc2d..._ReDetSim`,
data `sp.root` → `sptpc2d..._WCLS`.

## Part 6 — `sp.jsonnet` merged, and the campaign re-run at production thresholds (2026-08-13)

### The two `sp.jsonnet` copies had diverged, and it cost us the campaign

The toolkit (`wire-cell-toolkit/cfg/pgrapher/experiment/sbnd/`) and sbndcode
(`sbndcode/WireCell/cfg/pgrapher/experiment/sbnd/`) copies are a permanent
fork — `funcs`/`img`/`magnify-sinks` differ by 66–72 lines and the `wcls-*`
files by 218–311. For `sp.jsonnet` the divergence was three items, and one of
them silently invalidated the data-leg numbers in Part 5.

| item | toolkit | sbndcode | merged |
|---|---|---|---|
| `rebase_planes: []` | absent | present | **kept** |
| tight-ROI thresholds | hardcoded 5.0 / 3.0 | `std.extVar('enableLowROIThresholds')` | **restructured** |
| `wiener_threshold_tag` | removed | present | **removed** |

**`rebase_planes` is a trap.** `OmnibusSigProc` reads the key only
`if (config.isMember("rebase_planes"))` and the C++ default is
`std::vector<int> m_rebase_planes{0,1,2}` (`OmnibusSigProc.h:276`). Omitting
it therefore rebaselines **all** planes, not none — the opposite of what the
w-gap study concluded SBND wants. The merged file carries the key with a
comment saying so. Note CVMFS production also omits it, so production
rebaselines all planes; only `wcp-porting` turns it off.

**The threshold switch failed silently.** The campaign in Part 5 ran with a
copy of `sp.jsonnet` derived from the toolkit, which had dropped the extVar and
hardcoded the **high** thresholds — while `rerun-fixed-sp.fcl:77` and every
production fcl asked for the **low** ones. Jsonnet ignores an extVar nobody
reads, so there was no error and no warning. The campaign ran at 5.0/3.0
against production's 3.0/1.8.

Which fcl wants which:

| fcl / config | jsonnet | `enableLowROIThresholds` |
|---|---|---|
| `standard_detsim_sbnd.fcl:100` | `wcls-sim-drift-depoflux-nf-sp` | true (low) |
| `wcsimsp_sbnd.fcl:85` `sbnd_wcls_simsp` | `wcls-sim-drift-depoflux-nf-sp` | true (low) |
| `wcsp_data_sbnd.fcl:69` `sbnd_wcls_sp_data` | `wcls-nf-sp-data` | true (low) |
| `reco1_data_lowthreshold_dnn.fcl:4` | `wcls-nf-sp-data` | true (low) |
| `wcsimsp_sbnd.fcl:147` `sbnd_wcls_sp` | `wcls-nf-sp` | **false (high)** |

So the merged `sp.jsonnet` **defaults to the low values** and the single
high-threshold path passes 5.0/3.0 through the existing `override` argument
(which callers already use for `sparse`). A caller that forgets the override
now lands on production behaviour instead of silently coarser ROIs — the
inverse of the failure mode above. One call site changed, not eleven.

### What the threshold error did and did not change

Measured directly on data event 18259-1-107100, old 5.0/3.0 → new 3.0/1.8:

| plane | gauss old | gauss new | ratio | live channels |
|---|---|---|---|---|
| U | 2.099e6 | 2.119e6 | 1.009 | 1958 → 1969 |
| V | 2.108e6 | 2.508e6 | **1.190** | 2716 → 3085 |
| W | 2.031e6 | 2.059e6 | 1.013 | 1488 → **2373** |

The low induction threshold (1.8 vs 3.0) does most of the work, which is
exactly where the Part 5 U/V numbers were least trustworthy.

### Data leg re-run — 10 events, like-for-like against production

`data/validation-20260813-lowthr/`, both sides now at 3.0/1.8, so the only
remaining difference is the four fixes.

| plane | ours / production | Part 5 (confounded) |
|---|---|---|
| U | 1.0062 | — |
| V | 1.0117 | — |
| W | **1.0144** | 1.0042 |
| W, on the 76 old-flagged channels | **1.154×** | 1.146× |

Every plane gains slightly and none loses. The flagged-channel recovery barely
moved (1.146 → 1.154), so **that headline number was robust to the threshold
error**; the suppressed one was the overall W ratio. Biggest per-event movers:
18259-1-107716 (9 ch, 2.37×) and 18259-1-107892 (5 ch, 1.83×).

**BEE (data, ours): `1b13567d-7553-427b-a41a-c0f4b9df7eed`**, same index order
as before, so it still pairs with production `19951d4e-...` at equal indices.

### MC leg re-run — 10 events vs SimChannel truth

`dnnsp`/truth is what imaging consumes (W `dnnsp` *is* `gauss` — the
`dnnroi.jsonnet` plane-2 shunt), so read that column:

| plane | nchan | gauss/T | **dnnsp/T** | Part 5 dnnsp/T (5.0/3.0) | chans < 0.5 |
|---|---|---|---|---|---|
| U | 7758 | 0.9753 | **0.9826** | 0.9507 | 87 (1.12 %) |
| V | 8527 | 1.0155 | **0.9569** | 0.9198 | 264 (3.10 %) |
| W | 6542 | 0.9931 | **0.9931** | 0.9891 | 82 (1.25 %) |

Every plane improves at the production thresholds, U and V substantially
(+3.2 and +3.7 points) — they were the ones the high-threshold run was
penalising. W lands at 0.9931 of truth. V `gauss` now slightly *over*-collects
(1.0155) at the low induction threshold, but nothing downstream reads V
`gauss`.

**BEE (MC, ours): `185a6466-9926-4b8d-9727-2e9b3d6fd676`**, idx 0–9 =
270/6/{11,12,13,14,30,33,34,37,38,46}, pairing with production
`ad1f4703-...` at equal indices.

### Campaign scripts are now relocatable

All campaign scripts honour `CAMPAIGN_DIR` (default unchanged, so Part 5
reproduces as written):

```bash
export CAMPAIGN_DIR=.../data/validation-20260813-lowthr SUB=data
bash scripts/campaign-driver.sh $CAMPAIGN_DIR/data-worklist.txt
```

Also fixed: `campaign-driver.sh`'s `data` case pointed at
`campaign-img-data.sh`, which has no opflashes and dies on every event with
`OpFlashSource failed to get opflashes`. It now uses `campaign-opreco-data.sh`,
the script the working chain actually used.

## Next steps

- [x] ~~Decide on V~~: moot — the 7.5 % loss is in `gauss`, which nothing in this
      chain reads; `dnnsp` V is marginally better (0.9151 -> 0.9198).
- [ ] cid 7 (~97 cm, gapfrac 0.860) and cid 12 (~61 cm, 0.720) are unchanged by
      all three fixes — find their gap mechanism (dead/shorted wires, DNNROI
      truncation, or imaging 3-view coincidence). Note cid 7's maxgap is 20.7 cm
      and cid 12's 26.2 cm, i.e. single large holes, not fine dashing.
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
