# Event-level GENIE truth from SBND reco1 artROOT files — for Xin's agent on wcgpu1

Xin asked for, per event: how many true neutrinos, interaction type, CC/NC, true neutrino energy, true vertex. All of it is **already inside the reco1 files** (product `simb::MCTruths_generator__GenieGen.`), so nothing extra was saved; this note says how to read it, and what we ship alongside so you do not have to.

## 1. What we ship (per MC sample, next to the reco1 files)

`<sample>/truth/<sample>-truth.tsv` — one row per **(event, true neutrino)**, made by `scripts/dump_truth.py` on FNAL:

| column | meaning |
|---|---|
| `run subrun event` | art event id (matches `Trun` in `tracking-pr.root` and the file names) |
| `n_nu` | number of GENIE `MCTruth` entries in the event (rockbox: dirt/cryostat interactions count too — see `in_active_tpc`) |
| `inu` | index of this row's neutrino within the event (0…n_nu−1) |
| `nu_pdg` | 12/−12/14/−14 |
| `ccnc` | `simb::MCNeutrino::CCNC()`: **0 = CC, 1 = NC** |
| `mode` | `simb::MCNeutrino::Mode()`: GENIE mode (0 QE, 1 Res, 2 DIS, 3 Coh, 10 MEC, …) |
| `interaction_type` | `simb::MCNeutrino::InteractionType()`: full `simb::int_type_` code (1001 CCQE, 1002 NCQE, 1003–1090 Res, 1091/1092 DIS, 1097/1098 Coh, 10 MEC, …) |
| `E_nu_MeV` | true neutrino energy |
| `vtx_x_cm vtx_y_cm vtx_z_cm t_ns` | true interaction vertex (LArSoft world coordinates, cm) and time |
| `lepton_pdg` | outgoing lepton PDG (11/13 for CC; the neutrino for NC) |
| `target_pdg` | nuclear target (1000180400 = Ar-40) |
| `n_genie_particles` | number of GENIE final-state particles in this `MCTruth` |
| `in_active_tpc` | 1 if the vertex is inside the active volume (|x|<200, |y|<200, 0<z<500 cm) |

Sanity numbers from the 50-event MC CV bench file: 84 rows for 50 events (n_nu = 1: 20 events, 2: 26, 3: 4); 20/50 events have an in-TPC neutrino — exactly the 20 events our chain reconstructs a candidate in. Expect the same ~40 % on the CV sample; ~100 % on the nueCC exclusive sample.

## 2. How the TSV was made (reproduce on any host with the `nusimdata` ROOT dictionaries)

```
# FNAL, inside the SL7 container:  source wcp-porting-validation/sbnd/setup-local-opt.sh   (ups: nusimdata, lardataobj …)
python3 scripts/dump_truth.py <out.tsv> <reco1.root> [more.root ...]
```
Bare PyROOT, no `art`/LArSoft framework: open the `Events` tree, enable `simb::MCTruths_generator__GenieGen.*` and `EventAuxiliary*`, and read the split sub-branch **`simb::MCTruths_generator__GenieGen.obj`** — that is the `std::vector<simb::MCTruth>` itself (reading the wrapper branch by its top name gives a null/opaque object in PyROOT; the `.obj` sub-branch is the reliable handle, and `TTreeReaderArray<simb::MCTruth>` on the same name works too). Per entry: `m.GetNeutrino()` → `simb::MCNeutrino` (`CCNC()`, `Mode()`, `InteractionType()`, `Nu()`, `Lepton()`, `Target()`), `Nu()` → `simb::MCParticle` (`PdgCode()`, `E()`, `Vx() Vy() Vz() T()`).

Other truth in the same files, if ever needed: `simb::GTruths_generator__GenieGen.` (GENIE kinematics), `simb::MCFluxs_generator__GenieGen.` (flux parentage), `simb::MCParticles_largeant__G4.` (Geant4 particles), `sim::SimEnergyDeposits_…` (energy deposits — what our `wclsTensorSetLabeler` uses for per-blob truth labels), and the cosmic overlay `simb::MCTruths_corsika__GenieGen.` (deliberately not in the TSV).

**Requirement:** the `simb::MCTruth`/`MCNeutrino`/`MCParticle` ROOT dictionaries (`libnusimdata_SimulationBase_dict.so` from the `nusimdata` product) must be loadable. On a host without ups/LArSoft, PyROOT cannot interpret the branch — which is why the TSV is shipped, and why §3 exists.

## 3. Doing it without LArSoft dictionaries: the `wire-cell-sbnd-reco1` pattern

[`wire-cell-sbnd-reco1`](https://github.com/WireCell/wire-cell-sbnd-reco1) reads `recob::Wire`, the `wienersummary` doubles, the bad-mask ints, `recob::OpFlash` and `sbnd::timing::FrameShiftInfo` from reco1 with **no LArSoft at all**: it declares *mirror classes* with the same names and layout as the art/LArSoft ones, builds its own ROOT dictionary for them (`dict/LinkDef.h`, `WireCellSBNDReco1Dict`), and reads the `.obj` sub-branches through those (`SBNDReco1FrameSource.cxx`: `wires.obj[iw]`, `sums.obj`, `masks.obj`). The one rule: LArSoft's own dictionaries must **not** be on `LD_LIBRARY_PATH` at the same time (duplicate `recob::Wire` dictionary → segfault; `run-reco1-dump.sh` scrubs `lardataobj|canvas|sbndcode|sbnobj|artdaq|lardataalg`).

The same approach gives a truth reader in ~200 lines: mirror `simb::MCParticle` (TLorentzVector position/momentum, pdg, status, mother, trackid), `simb::MCNeutrino` (Nu/Lepton particles + `fMode`, `fInteractionType`, `fCCNC`, `fTarget`, …), `simb::MCTruth` (`fPartList`, `fMCNeutrino`, `fNeutrinoSet`, `fOrigin`); add them to `LinkDef.h`; a component `SBNDReco1TruthSource` (an `ITensorSetSource` like `SBNDReco1OpFlashSource`) that reads `simb::MCTruths_generator__GenieGen.obj` for the entry range and emits one tensor row per neutrino with the columns above — or simply writes the TSV. Layout of the mirror classes must match `nusimdata` `v1_27_02` (the version of the production): copy the data-member lists from `nusimdata/SimulationBase/{MCParticle,MCNeutrino,MCTruth}.h` and check with `TFile::ShowStreamerInfo()` on a reco1 file that the class versions agree. This is what the 1-step's `wclsTensorSetLabeler` (`larwirecell/aiml/TensorSetLabeler.cxx`, lines ~556 ff.) does with real art handles; the standalone chain has no equivalent yet, so the TSV is the practical route for this round.

## 4. Joining truth to reconstruction

`tracking-pr.root` `Trun` carries run/subrun/event; `T_kine`/`T_tagger` do not. Join on `(run, subrun, event)`; for events with `n_nu > 1`, the reconstructed candidate is (almost always) the `in_active_tpc = 1` row — 96 % of multi-neutrino events in the bench file have exactly one in-TPC neutrino.
