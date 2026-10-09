# Issue 39: merge Wire-Cell `tracking-pr.root` into the flat CAF

GitHub: https://github.com/HaiwangYu/wire-cell-toolkit-ai-helper/issues/39.

**Ask (Haiwang, 2026-10-08).** For large-scale production, put the Wire-Cell standalone output (`tracking-pr.root`) into the commonly used flat CAF as a new tree, `recTreeWireCell`.
- **Task 1:** analyse an existing flat CAF: how `recTree` handles jagged content, and how it maps to `GenieEvtRecTree`.
- **Task 2:** make every `tracking-pr.root` tree per event, and carry metadata (the input artROOT path) from step 1 through `qlpctree.tar.gz`.
- **Task 3:** a 3-step workflow (reco1 → `qlpctree.tar.gz` → `tracking-pr.root` → merged CAF), with inputs found by SAM definition or path.
- **Validation:** `recTreeWireCell` identical to `tracking-pr.root`, and the cost of every step recorded.
- Steering scripts and agent instructions go in `HaiwangYu/sbnd-wirecell-production`, folder `aurora/`.

Builds on #33 (our 2-step chain), #35 (the DL dump) and #38 (production run r7 and its harness).

## Test inputs

Five reco1 / flat-CAF pairs from the gen2 CV production, `aurora_SBND2026A_gen2_BNBLight_prodgenie_corsika_proton_rockbox0p1_sbnd_CV_v10_14_02_03_{reco1,flatcaf}_sbnd`.
- The FNAL copies are under `/pnfs/sbn/data_add/sbn_nd/aurora/mc/v10_14_02_03/prodgenie_corsika_proton_rockbox0p1_sbnd/Gen2_2026/CV/{reco1,caf}/000000/000000/`. Aurora's `Gen2_2026/` holds the same production; there the CAFs are named `*.caf.root` rather than `*.flat.caf.root`.
- Staged on sbndbuild03 in `production-prep/caf-merge-dev/inputs/{reco1,caf}/`.

| id | reco1 | flat CAF | events |
|---|---|---|---|
| `f33e-e536-780d-5a11` (the example) | `reco1-detsim-g4-gen-Gen2_2026-<id>.root` | `reco2-reco1-detsim-g4-gen-Gen2_2026-<id>.flat.caf.root` | 15 |
| `0045-7b83-3292-4b82` | 〃 | 〃 | |
| `00a3-5b88-5b98-db94` | 〃 | 〃 | |
| `00d8-4843-8a75-5672` | 〃 | 〃 | |
| `0100-7286-fc4e-3030` | 〃 | 〃 | |

SAM lineage: the flat CAF's parent is the reco1 file itself, and both have the same event count (15 for `f33e`, events 1–44). So `recTree` has one entry per reco1 art event.

## Task 1: the flat CAF format

The file holds `recTree` (15 entries), `GenieEvtRecTree` (27), `globalTree` (1), the histograms `TotalPOT`, `TotalEvents`, `TotalGenEvents`, and the directories `env/` and `metadata/`. `recTree` has 2,662 branches. They come from the CAF `StandardRecord` flattened by SRProxy, all under `rec.`.

### How `recTree` stores jagged content

**One entry = one art event.** Every level of the nested `StandardRecord` is flattened into C arrays inside that one entry:

| level | example | stored as |
|---|---|---|
| per event | `rec.hdr.run` (UInt_t), `rec.nslc` (Int_t) | a scalar |
| vector in the event (slices) | `rec.slc.vertex.x` | `Float_t[rec.slc..length]`; `rec.slc..length` (Int_t) is the number of slices in this event |
| vector inside a vector (PFPs of each slice) | `rec.slc.reco.pfp.trk.len` | ONE flat array per event, `Float_t[rec.slc.reco.pfp..totarraysize]`, holding the PFPs of all slices back to back |
| its bookkeeping | `rec.slc.reco.pfp..length[rec.slc..length]`, `rec.slc.reco.pfp..idx[rec.slc..length]` | per slice: how many PFPs, and where they start in the flat array |

So the PFPs of slice *i* are `flat[idx[i] : idx[i] + length[i]]`. Deeper levels repeat the pattern: a `..length` / `..idx` pair per parent element, and one flat array sized by a scalar `..totarraysize` branch. The file has 143 `..length`, 109 `..idx` and 109 `..totarraysize` branches.

Example, `f33e` entry 0 (run 301, subrun 55, event 1): 8 slices; `rec.slc.reco.npfp` = `[3, 2, 8, 6, 3, 9, 2, 3]`; `pfp..idx` = `[0, 3, 5, 13, 19, 22, 31, 33]`; the flat `pfp.trk.len` has 36 values.

This is ROOT's variable-length array mechanism: a leaf `x[n]` whose size `n` is another scalar leaf of the same entry. Nesting is resolved by flattening and keeping offsets. It needs no `vector<vector<>>` dictionaries, and `uproot` / `awkward` read it directly as jagged arrays.

### `recTree` vs `GenieEvtRecTree`

- **`GenieEvtRecTree` has one entry per simulated neutrino interaction**, the GENIE `GHepRecord`s (`GenieEvtRec.*`, plus `GENIEEntry` and `SourceFileHash`). An event can hold several: the gen2 CV sample overlays the beam neutrino with rockbox / dirt interactions. In `f33e`, 15 events hold 27 interactions.
- **`recTree` has one entry per event.** Its truth block is `rec.mc.nu[rec.mc.nu..length]`; `rec.mc.nnu` is the same count.
- **The link is `rec.mc.nu.genie_evtrec_idx`:** the entry number in `GenieEvtRecTree` of that neutrino. For `f33e`, event 1 has `genie_evtrec_idx = [0, 1]` with E = 0.682, 1.839 GeV, and GENIE entries 0 and 1 carry exactly those energies. Event 3 has `[2, 3]`, event 4 has `[4]`, and so on. The sum of `rec.mc.nnu` over the file is 27, equal to `GenieEvtRecTree`'s entry count.
- **Reco objects point at truth by index too.** `rec.slc.tmatch.index[rec.slc..length]` is the index into `rec.mc.nu` of the slice's matched neutrino, or -999.

### What this means for `recTreeWireCell`

Follow the same convention: one entry per art event, aligned with `recTree` by run / subrun / event.
- A `tracking-pr.root` tree with N rows per event becomes arrays sized by `wc.<tree>..length`.
- A per-row vector becomes `..length` / `..idx` / `..totarraysize` plus a flat array.
- `vector<vector<>>` gets one more level of the same.
- Cross-references keep the existing index columns (`nu_index`, `cluster_id`, `call_index`, …), just as CAF uses `tmatch.index`.

### What `tracking-pr.root` holds (r7, one file per event)

| tree | rows per event | branch types |
|---|---|---|
| `Trun` | 1 | Int_t, Double_t, string (6) |
| `T_kine`, `T_tagger` | one per neutrino candidate | Float_t, Int_t, vector<float>, vector<int> |
| `T_bundle` | one per flash bundle | Int_t, Float_t |
| `T_cluster` | one per cluster | Int_t, Double_t |
| `T_flash` | one per flash | Int_t, Float_t |
| `T_segment` | one per PR segment | Int_t, Float_t |
| `T_rec_charge` | one per fitted point | Int_t, Double_t |
| `T_bad_ch` | one per bad-channel range | Int_t |
| `T_proj_data` | 1 | vector<int>, vector<vector<int>> |
| `T_proj` | 1 | none |
| `T_truth_nu`, `T_truth_pf` (MC) | one per neutrino / truth particle | Int_t, Double_t |
| `T_dlvtx_call` | one per DL network call | Int_t, Double_t, vector<float/int/double> |
| `T_dlvtx_cloud` | one per network-input point | Int_t, Float_t |

There are only eight value types in all: Int_t, Float_t, Double_t, string, vector<int>, vector<float>, vector<double>, vector<vector<int>>. So a generic, exact conversion is possible.

## Design

- **Step 1 (larwirecell).** The WCT art module forwards art's `respondToOpenInputFile(FileBlock)` to the visitors. `wclsTruthInformationAttacher` stamps `input_file` (the art input path, `FileBlock::fileName()`) into the set metadata, next to the RSE, so it travels in `qlpctree.tar.gz`. No fcl or driver change is needed.
- **Step 2 (toolkit).**
  - The PR MABC exposes its input set metadata to the visitors.
  - `SbndPrMagnifyTrackingVisitor` writes `Trun.input_file`.
  - A new visitor runs last in the PR pipeline. It reads back the per-event `tracking-pr.root` and writes `recTreeWireCell`: 1 entry, every tree in the CAF flat layout above, plus `wc.run` / `wc.subrun` / `wc.evt`.
  - It is a `pr()` knob, default off, so every compiled config stays byte-identical until switched on. The row trees stay in the file, for existing tools and for validation.
- **Step 3 (production repo).** The merger copies the flat CAF unchanged and adds `recTreeWireCell`.
  - Its entries follow `recTree`'s order, matched by run / subrun / event.
  - An event without Wire-Cell output (crashed or not run) gets an empty entry with `wc.valid = 0`.
  - Pairs are found by SAM definition (`samweb`, the CAF's parent is the reco1) or by path, from the name mapping `reco1-X.root` ↔ `reco2-reco1-X.{flat.,}caf.root`.

## Log

- 2026-10-08: scope; Task 1 analysis (above); 5 test pairs staged; issue #39 opened.
