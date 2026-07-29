# Issue #1 — Update `larwirecell/aiml/TensorSetLabeler.cxx`

Status: **done & validated** (2026-07-28).

`wclsTensorSetLabeler` (larwirecell `aiml/`) sits between the all-APA
MultiAlgBlobClustering and its TensorFileSink in `wcls-img-clus-matching-xin.fcl`
(MC only, `reality=='sim'`). It attaches truth to the clustering, emits the Bee
"mc" tree + the SED pseudo-sim point sets, and writes the pynuml HDF5 graph.

## Changes

1. **Readout cut on `sed-smear_readout`.** The readout-window cut is now
   evaluated on the **full pseudo-sim (SCE + drift) apparent time** `x_app`
   (same as `sed-sce_drift_smear_readout`), while the point itself stays at the
   **true** `x0,y0,z0`. Internally `dump_ball()` gained a separate `x_cut`
   (used for the readout cut) vs `x_point` (used for the deposited position).

2. **`nu_idx` per SED point.** Each SED point carries a neutrino-interaction
   index derived from its `|trackid|` → beam-nu `MCTruth` key:
   - `0` = non-neutrino activity (cosmics, etc.)
   - `1, 2, …` = beam-neutrino interactions (1-based; `nu_index + 1`).

3. **`mc.json` neutrino-node text.** Now
   `"<nu_idx> <flavor> Etot <total nu E> MeV Edep <deposited> MeV"`, e.g.
   `1 numu Etot 841.4 MeV Edep 528.4 MeV`. `nu_idx` uses the same 1-based
   scheme as the SED sets; `Etot` is the incoming neutrino total energy
   (`nu.Momentum(0).E()`), `Edep` the interaction's deposited (visible) energy.

4. **`q` and `e` per SED point.** Each SED point stores both
   `q = SimEnergyDeposit::NumElectrons()` and `e = SimEnergyDeposit::Energy()`
   (MeV), each split across the `nsample` diffusion-ball samples.
   (Note: for the current deposet `NumElectrons()` is 0 — only energy is
   stored — so `q = 0` and `e` carries the value.)

Task 4 + the `nu_idx` field required extending WCT `Bee::Points`
(`WireCellUtil/Bee.h`, `Bee.cxx`) with an
`append(p, q, clid, real_clid, e, nu_idx)` overload that emits `e` / `nu_idx`
arrays in the point JSON; existing point clouds are unchanged.

## Commits (local, not yet pushed to those upstreams)

| repo | branch | commit |
|---|---|---|
| wire-cell-toolkit | `master` | `2edf0a88` Bee::Points: optional per-point energy (e) and nu_idx |
| larwirecell (MRB `srcs/larwirecell`) | `dev-v10_14_02_02` | `42f4759` TensorSetLabeler: sed-set nu_idx/q/e, readout cut, mc Etot |

Built into `/exp/sbnd/app/users/yuhw/opt` (WCT `libWireCellUtil.so`) +
hand-copied `libWireCellAIML.so` into `opt/larwirecell/.../lib`.

## Validation

Work area: `/exp/sbnd/app/users/yuhw/wcp-porting-img/sbnd/TensorSetLabeler/nugraph-sample-v3`

Run recipe (SL7 + `setup-ap.sh`):
```bash
export FHICL_FILE_PATH=/exp/sbnd/app/users/yuhw/wcp-porting-img/sbnd:$FHICL_FILE_PATH
# MC (labeler on):
lar -n 10 -c wcls-img-clus-matching-xin.fcl \
    -S /exp/sbnd/app/users/yuhw/2025-fall-prod-sample/round2-patrec/mc_paths-v10_14_02_03-100files.lst \
    --no-output
# data (DATA mode, evt 269774):
lar -n 1 --nskip 20 -c wcls-img-clus-matching-xin-data.fcl \
    -s .../samples/filtered-reco1/data_..._frameshift.root --no-output
```

Results:
- **Smoke** — 1 MC + 1 data (evt 269774): both `LAR_RC=0`, nugraph written.
- **Full** — 10 MC + 10 data: both `rc=0`, 10 nugraph records each, no crash.
- SED sets carry `q,e,nu_idx` (a rockbox event shows `nu_idx ∈ {0,2,3}`);
  mc nodes read `1 numu Etot …`, `2 numu Etot …`, `3 numu Etot …`.

Output locations (under `nugraph-sample-v3/`):

| dir | content |
|---|---|
| `mc-10evt-v10_14_02_03/` | 10-evt MC (v10_14_02_03 sample): `mabc.zip`, `nugraph.h5` |
| `data-10evt/` | 10-evt data (evt 269774 file): `mabc.zip`, `nugraph.h5` |
| `data/`, `mc-10evt/` | 1-evt data smoke; 10-evt MC from the older round1 sample |

Bee (10-event MC, v10_14_02_03):
https://www.phy.bnl.gov/twister/bee/set/d82a3ae7-927e-478f-a8e5-d06ec74b0254/event/list/
