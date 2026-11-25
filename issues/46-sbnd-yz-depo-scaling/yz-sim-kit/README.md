# SBND detsim with per-plane YZ charge scaling: a kit

This kit runs the **standard SBND detector simulation** (sbndcode v10_14_02_03,
`standard_detsim_sbnd.fcl`: TPC + optical + CRT) with one switch for the
Wire-Cell TPC simulation:

- **off**: the stock sbndcode Wire-Cell configuration, unchanged.
- **on**: before the signal simulation of each wire plane, the charge of every
  energy deposit is scaled by that plane's YZ map at the deposit's (y, z).

Everything downstream is standard: noise filter, signal processing with
traditional and DNN ROI, the same art products and labels. Standard reco1 and
the Wire-Cell reconstruction can read the output as usual.

Background, the map, and the component: ai-helper issue 46,
`../46-sbnd-yz-depo-scaling.md` (sections 1 to 3).

## 1. How it works

- The new Wire-Cell component is `DepoTransformYZ` (Wire-Cell branch
  `sbnd-yz-depo-scaling`, https://github.com/HaiwangYu/wire-cell-toolkit). It
  is the standard `DepoTransform` with one change: for each plane, it multiplies
  the deposit charge by the map value of that plane and TPC. The three planes
  get different factors from the same deposit. It costs no extra time.
- The map is a `YZMap` service. File:
  `sbnd/sbnd-yzmap-run2-gen2-bnblight-v1.json.bz2` (in
  [wire-cell-data](https://github.com/WireCell/wire-cell-data), master).
  - Factor = 1/C, with C = `CzyHist_<plane>_<tpc>` of
    `run_2_gen_2_BNBLight_data_v10_14_02_02_200usEast80usWest.root`.
  - Normalized to mean 1 per plane and TPC (`inv-norm`), so the overall
    charge scale does not change.
  - Pixels without data (C = 0) get 1.
  - Binning: 100 z bins × 80 y bins of 5 cm, z 0 to 500 cm, y −200 to 200 cm.
    Keys `AnodePlane:apa0` = East (TPC 0), `AnodePlane:apa1` = West (TPC 1).
- SimChannels (`simtpc2d:simpleSC`) are written **before** the scaling. They
  are the same in both modes. The scaling shows up in the TPC waveforms and
  everything after them.

## 2. Files

| file | what |
|---|---|
| `setup-yz-env.sh` | environment: sbndcode v10_14_02_03 + our larwirecell + the branch WCT libraries + kit paths |
| `run-yz-detsim.sh` | run detsim (and optionally reco1) in one mode; logs, time, memory |
| `fcl/detsim_sbnd_yz.fcl` | `standard_detsim_sbnd.fcl` + the toggle (`yz_scaling`) + the map name (`yz_map`) |
| `fcl/detsim_sbnd_yz_off.fcl`, `fcl/detsim_sbnd_yz_on.fcl` | the two modes |
| `cfg/pgrapher/experiment/sbnd/wcls-sim-drift-depoflux-nf-sp-yz.jsonnet` | copy of sbndcode's `wcls-sim-drift-depoflux-nf-sp.jsonnet` with the toggle |
| `cfg/pgrapher/experiment/sbnd/sim-yz.jsonnet` | copy of sbndcode's `sim.jsonnet`; uses `DepoTransformYZ` when a map is given |
| `scripts/check_yz_scaling.py` | did it work? measured on/off charge ratio per channel vs the map |
| `scripts/check-config-identity.sh`, `scripts/fcl_wcls_args.py` | proves "off" = stock sbndcode configuration |
| `scripts/build-wct-yz.sh` | build the Wire-Cell branch yourself (route B) |

The two jsonnet files have new names, so they hide nothing of sbndcode. Every
change in them is marked `YZ-KIT`. To see the changes:

```bash
S=/cvmfs/sbnd.opensciencegrid.org/products/sbnd/sbndcode/v10_14_02_03/wire-cell-cfg/pgrapher/experiment/sbnd
diff $S/wcls-sim-drift-depoflux-nf-sp.jsonnet cfg/pgrapher/experiment/sbnd/wcls-sim-drift-depoflux-nf-sp-yz.jsonnet
diff $S/sim.jsonnet                           cfg/pgrapher/experiment/sbnd/sim-yz.jsonnet
```

## 3. Setup

Everything runs in the SL7 container. On an SBND gpvm:

```bash
apptainer exec -B /cvmfs,/exp,/pnfs,/tmp,/opt \
    /cvmfs/singularity.opensciencegrid.org/fermilab/fnal-dev-sl7:latest bash
source <kit>/setup-yz-env.sh
```

`run-yz-detsim.sh` starts the container and sources the setup by itself, so
for the normal workflow you do not need to do this by hand.

`<kit>` = `/exp/sbnd/data/users/yuhw/wire-cell-toolkit-ai-helper/issues/46-sbnd-yz-depo-scaling/yz-sim-kit`
(readable by everyone; copy it if you want to change it).

### Route A: use our build (read-only, nothing to build)

The defaults of `setup-yz-env.sh` point to:

| | path |
|---|---|
| Wire-Cell libraries, branch `sbnd-yz-depo-scaling` | `/exp/sbnd/app/users/yuhw/opt-yz/lib` (`YZ_WCT_LIB`) |
| larwirecell v10_01_28 (branch `sbnd-wc-flatcaf` of https://github.com/HaiwangYu/larwirecell) | `/exp/sbnd/app/users/yuhw/opt/larwirecell/v10_01_28` (`YZ_LWC_DIR`) |
| the map (a wire-cell-data clone) | `/exp/sbnd/app/users/yuhw/wire-cell-data` (`YZ_MAP_PATH`) |

All of these are readable by every user. You need nothing else.

Why not the CVMFS Wire-Cell: `DepoTransformYZ` exists only in the branch, and
the branch needs a larwirecell built against a recent Wire-Cell. The CVMFS
larwirecell is built against Wire-Cell 0.32.1.

How the libraries are loaded: larwirecell has a built-in library path (RPATH)
to the Wire-Cell it was built with, and that wins over `LD_LIBRARY_PATH`. So
the detsim job runs with `LD_PRELOAD=$WCT_YZ_PRELOAD`: the branch's Wire-Cell
libraries, by name, found through `LD_LIBRARY_PATH`. Then every Wire-Cell
library in the job comes from the branch, once (checked in `/proc/<pid>/maps`).
`run-yz-detsim.sh` does this for you. By hand:

```bash
LD_PRELOAD=$WCT_YZ_PRELOAD lar -c detsim_sbnd_yz_on.fcl -s g4.root -o detsim.root
```

Do not export `LD_PRELOAD` in your shell; set it per `lar` command.

### Route B: build it yourself

B1. Build only Wire-Cell, keep our larwirecell (simplest):

```bash
# in the SL7 container; ~9 GB source+build, ~2 GB install; 12 min with 12 jobs
<kit>/scripts/build-wct-yz.sh /path/to/wire-cell-toolkit /path/to/opt-yz 8
export YZ_WCT_LIB=/path/to/opt-yz/lib
source <kit>/setup-yz-env.sh
```

The script clones branch `sbnd-yz-depo-scaling` if the source directory does
not exist, and uses the same configure options as our build.

B2. Also build larwirecell: branch `sbnd-wc-flatcaf` of
https://github.com/HaiwangYu/larwirecell, in an mrb area of larsoft v10_14_02
(e26:prof), with `WIRECELL_FQ_DIR` and `CMAKE_PREFIX_PATH` pointing at your
Wire-Cell install. Then `export YZ_LWC_DIR=<your larwirecell product dir>`
before sourcing the setup. Our notes, with the traps:
`/exp/sbnd/app/users/yuhw/wcp-porting-img/sbnd/docs/0-build-wct-larwirecell-sl7-sbnd.md`.
You only need B2 if you want to change larwirecell.

To use your own map, see section 9.

## 4. Inputs

Any SBND g4 file made with sbndcode v10_14 (it needs `ionandscint`
SimEnergyDeposits, as the standard detsim does). Ours, readable by everyone:

- 10 long single muons (5 GeV μ−, along +z, x over both TPCs):
  `/exp/sbnd/data/users/yuhw/YZ-non-uniformity/mu-test/g4.root`. Recipe:
  issue doc section 3 (`scripts/fcl/gen_mu_long.fcl` + `standard_g4_sbnd.fcl`).
- BNB CV-like neutrinos with cosmics, 24 events (GENIE BNB + CORSIKA, rockbox
  filter at generation: 70 generated, 24 kept; sbndcode v10_14_02_03):
  `/exp/sbnd/data/users/yuhw/YZ-non-uniformity/bnb-cv-10/g4.root`. Recipe:
  `make-g4.sh` in the same directory.

## 5. Run

Run the same g4 file twice, once per mode, into two directories:

```bash
K=<kit>
$K/run-yz-detsim.sh --yz off  my_g4.root  out/off  [nevents]
$K/run-yz-detsim.sh --yz on   my_g4.root  out/on   [nevents]
```

Options: `--reco1` also runs `standard_reco1_sbnd.fcl` on the detsim output;
`--nskip N` skips the first N events; `--map FILE` (with `--yz on`) uses
another map.

- You can start the two at the same time; each art job gets its own
  directory. Two art jobs in one directory fail on CephFS (`/exp/...`) with
  "disk I/O error" from art's MemoryTracker SQLite file.
- Both modes use the same libraries. So the on/off difference is the YZ
  scaling only. Note: "off" runs the stock sbndcode configuration, but with a
  newer Wire-Cell than CVMFS sbndcode's (0.32.1). "off" is therefore not
  bit-identical to a stock sbndcode detsim.
- It does not overwrite an existing `detsim.root`.

## 6. Outputs

```
out/<mode>/detsim/detsim.root     the art file (process name DetSim)
                  detsim.log      lar output; detsim.cmd the command
                  detsim.time     /usr/bin/time -v (wall time, max RSS)
                  summary.txt     wall time, max RSS, art TimeTracker and MemoryTracker tables
                  timing.db, memory.db   art's per-module SQLite tables
out/<mode>/reco1/reco1.root       with --reco1, same files
```

Wire-Cell products in `detsim.root` (all standard):

| label | type | what |
|---|---|---|
| `simtpc2d:dnnsp` | `recob::Wire` | SP with DNN ROI (production Wire-Cell reco and reco1 `gaushit` use this) |
| `simtpc2d:gauss` | `recob::Wire` | SP with traditional ROI, Gaussian filter |
| `simtpc2d:wiener` | `recob::Wire` | SP with traditional ROI, Wiener filter |
| `simtpc2d:wienersummary` | `std::vector<double>` | per-channel summary (noise threshold) of the Wiener frame |
| `simtpc2d:badchannels`, `simtpc2d:badmasks` | `std::vector<int>` | bad-channel mask map |
| `simtpc2d:simpleSC` | `sim::SimChannel` | true electrons per channel (not scaled) |

That is the full list of `simtpc2d` products (checked in our output). The
Wire-Cell config names the summary "wiener" and the mask "bad"; the art
instance names get the suffixes above.

No RawDigits, as in the standard detsim.

## 7. Check that it worked

Compare the two files channel by channel (sbndcode environment, PyROOT; ~1 min
for 10 events):

```bash
apptainer exec -B /cvmfs,/exp,/pnfs,/tmp,/opt \
    /cvmfs/singularity.opensciencegrid.org/fermilab/fnal-dev-sl7:latest bash
source <kit>/setup-yz-env.sh
python3 <kit>/scripts/check_yz_scaling.py out/off/detsim/detsim.root out/on/detsim/detsim.root \
    $YZ_MAP_PATH/sbnd/sbnd-yzmap-run2-gen2-bnblight-v1.json.bz2 out/check
```

For each channel with ≥ 20,000 true electrons and charge in both files:

- **predicted** = the map value of the channel's plane and TPC at its
  SimChannel deposits, weighted by electrons;
- **measured** = the channel's SP charge, on / off.

It prints a table per product (`dnnsp` and `gauss`), and writes
`yzcheck.json`, `yzcheck.png` and per-channel `yzcheck_<product>.tsv`.

What to expect, from our 10 long muons with THIS kit (sbndcode
configuration, section 10):

- `dnnsp`: median of measured/predicted − 1 within ±0.02 % on every plane;
  rms 0.7 % on Y, 1.1 to 1.2 % on U and V; correlation 0.89 to 0.96; plane
  totals agree with the prediction to ≤ 0.06 %.
- `gauss`: Y as `dnnsp`; U and V noisier per channel (rms 1.9 to 3.9 %,
  correlation 0.66 to 0.78; median within −0.1 %).

For comparison, the older test with the toolkit configuration (traditional
ROI only, no DNN ROI; issue doc section 3): `gauss` median within −0.13 %, rms
0.5 to 0.75 % on Y and 2.2 to 3.5 % on U and V.

On neutrino events with cosmics, a few channels near threshold get a
different ROI in the on and off runs, and their ratio is far off (tens of %).
They dominate the plain rms and correlation (BNB test: Y rms 7 to 14 %, corr
0.1 to 0.3). So the table also gives a robust rms (1.4826 × median absolute
deviation), the number of channels off by more than 5 %, and the correlation
without them (BNB test, `dnnsp`: robust rms 0.15 % on Y and 0.6 to 0.8 % on U
and V, corr 0.90 to 0.99 without the > 5 % channels).

"On = off" (ratio 1 everywhere, correlation ~0) means the scaling did not run.
Your numbers will not be exactly these: the noise realization differs between
the on and off runs, and other samples have other charge per channel.

To check that "off" is exactly stock sbndcode (no lar job; ~1 min):

```bash
<kit>/scripts/check-config-identity.sh out/config-check
```

It compiles the Wire-Cell configuration of `standard_detsim_sbnd.fcl`,
`detsim_sbnd_yz_off.fcl` and `detsim_sbnd_yz_on.fcl` with the same parameters
as lar, and compares the JSON. It must print `IDENTICAL` for stock vs off. For
stock vs on, the only changes are `DepoTransform` → `DepoTransformYZ` (same
settings + `yzmap`) for the two anodes, a new `YZMap`, and the renamed nodes in
the graph.

## 8. Resources

Long muons, 10 events, sbndbuild03, the two modes run at the same time
(section 10):

| mode | wall | max RSS | full event, mean (min–max) | `simtpc2d` per event | `opdaq` per event |
|---|---|---|---|---|---|
| off | 22:18 | 6.39 GB | 131.6 s (124–141) | 122.7 s | 8.7 s |
| on | 22:18 | 6.39 GB | 132.1 s (125–141) | 122.7 s | 9.2 s |

- `simtpc2d` (Wire-Cell sim + NF + SP with both ROI methods, DNN on CPU) is
  93 % of the time. The scaling costs nothing measurable.
- A job uses about one core. Plan ~7 GB of memory per job.
- Startup (geometry, services, the Wire-Cell configuration) is ~15 s.
- A neutrino event with cosmics has more charge than a muon, so expect more
  time per event there.

## 9. Change the map

1. Make the json.bz2 file from a calibration ROOT file with `CzyHist_<plane>_<tpc>`
   histograms, with the converter of the branch,
   `gen/test/convert-yzmap-sbnd.py` (needs python with numpy and uproot; any
   machine):

   ```bash
   python3 convert-yzmap-sbnd.py my_calib.root my-yzmap.json.bz2 [--factor inv-norm|inv]
   ```

   - `--factor inv-norm` (default): factor 1/C, scaled to mean 1 per plane
     and TPC over the pixels with data. Keeps the overall charge scale.
   - `--factor inv`: 1/C as is (changes the overall scale too).
   - Empty pixels (C ≤ 0) get 1. All other pixels are used as they are,
     including edge pixels with large C. To cap or fill pixels, change the
     converter.
   - It prints the matching binning. The jsonnet assumes 100 × 80 bins of 5 cm,
     z from 0 cm, y from −200 cm. For another binning, change the `YZMap` block
     in `wcls-sim-drift-depoflux-nf-sp-yz.jsonnet` (copy the kit first).
   - Converter: `/exp/sbnd/app/users/yuhw/wct-yz/gen/test/convert-yzmap-sbnd.py`,
     or on GitHub in the branch.
2. Run with it: `run-yz-detsim.sh --yz on --map /path/to/my-yzmap.json.bz2 ...`.
   By hand: set `physics.producers.simtpc2d.wcls_main.params.yz_map` to the file
   (a full path, or a path relative to a `WIRECELL_PATH` directory).
3. Check it with `check_yz_scaling.py ... /path/to/my-yzmap.json.bz2 ...`.

## 10. Validation (2026-11-24)

Outputs: `/exp/sbnd/data/users/yuhw/YZ-non-uniformity/kit-validation/`
(`off/`, `on/`, `check/`, `config-check/`).

**Configuration.** `check-config-identity.sh`: stock
`standard_detsim_sbnd.fcl` vs `detsim_sbnd_yz_off.fcl` give byte-identical
JSON (660,931 bytes). Stock vs on: `DepoTransform:depotransform-apa{0,1}` →
`DepoTransformYZ:depotransformyz-apa{0,1}` with the same data plus
`yzmap: "YZMap:sbnd-yz"`, `yzmap_key: ""` (= the anode name,
`AnodePlane:apa0/1`), the new `YZMap:sbnd-yz`, and the graph edges renamed
accordingly. Nothing else changes.

**Libraries.** In a running job (`/proc/<pid>/maps`), every Wire-Cell library
comes from the branch install, once; only `libWireCellLarsoft.so` comes from
the larwirecell install.

**Long muons** (10 events, `mu-test/g4.root`, 32,445 channel-events with
SimChannel charge, 18,504 with ≥ 20,000 electrons and charge in both runs).
Measured = SP charge on / off; predicted = the map at the SimChannel deposits.

`simtpc2d:dnnsp`:

| | channels | predicted rms | meas/pred − 1: median | rms | 5–95 % | corr | total meas / pred |
|---|---|---|---|---|---|---|---|
| East U | 4150 | 3.5 % | −0.00 % | 1.14 % | −1.0 … +1.0 % | 0.95 | 0.9994 / 0.9995 |
| East V | 6313 | 3.8 % | −0.02 % | 1.17 % | −1.5 … +1.6 % | 0.96 | 1.0036 / 1.0037 |
| East Y | 2404 | 1.9 % | +0.00 % | 0.66 % | −0.5 … +0.5 % | 0.94 | 0.9973 / 0.9973 |
| West U | 2228 | 2.3 % | −0.02 % | 1.13 % | −1.1 … +1.0 % | 0.89 | 0.9985 / 0.9991 |
| West V | 2274 | 4.4 % | +0.01 % | 1.23 % | −1.5 … +1.5 % | 0.96 | 1.0010 / 1.0011 |
| West Y | 1135 | 1.8 % | −0.01 % | 0.68 % | −0.5 … +0.5 % | 0.93 | 0.9982 / 0.9985 |

`simtpc2d:gauss`:

| | channels | predicted rms | meas/pred − 1: median | rms | 5–95 % | corr | total meas / pred |
|---|---|---|---|---|---|---|---|
| East U | 4150 | 3.5 % | −0.01 % | 3.87 % | −2.6 … +2.6 % | 0.66 | 1.0004 / 0.9996 |
| East V | 6313 | 3.8 % | −0.10 % | 3.42 % | −2.1 … +2.0 % | 0.71 | 1.0033 / 1.0045 |
| East Y | 2404 | 1.9 % | +0.00 % | 0.66 % | −0.5 … +0.5 % | 0.94 | 0.9973 / 0.9973 |
| West U | 2228 | 2.3 % | −0.02 % | 1.86 % | −1.8 … +1.4 % | 0.78 | 0.9989 / 0.9990 |
| West V | 2274 | 4.4 % | −0.08 % | 3.26 % | −2.3 … +1.8 % | 0.77 | 1.0000 / 1.0022 |
| West Y | 1135 | 1.8 % | −0.01 % | 0.68 % | −0.5 … +0.5 % | 0.93 | 0.9982 / 0.9985 |

- The scaling works per plane in the standard detsim, as it did with the
  toolkit configuration (issue doc section 3).
- **Y** (both products; DNN ROI is not used on Y): rms 0.66–0.68 % and
  correlation 0.93–0.94. The toolkit configuration gave 0.75 / 0.49 %.
- **U, V with DNN ROI** (`dnnsp`): rms 1.1–1.2 % and correlation 0.89–0.96.
  That is 2–3 times tighter than the toolkit configuration's `gauss`
  (2.2–3.5 %, corr 0.65–0.83). DNN ROI gives the same ROIs in the on and off
  runs more often, so the per-channel ratio is less noisy.
- **U, V `gauss`** in this configuration: like the toolkit test or a bit
  noisier (East U 3.9 % vs 2.2 %).
- **Totals:** median offsets ≤ 0.1 %; plane totals agree to ≤ 0.06 % (`dnnsp`)
  and ≤ 0.2 % (`gauss`).
- Figure: `kit-validation/check/yzcheck.png`; numbers:
  `kit-validation/check/yzcheck.json`.

**Reproducibility.** A job is not bit-reproducible: the same event, run
again with the same libraries and configuration, comes out with one of (at
least) two noise realizations. Seven runs of the first muon event fell into two groups, each
bit-identical within itself (`dnnsp`, `gauss`, `wiener` on all 11,276
channels); three of them were started at the same moment and still split 2 : 1.
The likely cause is that the two anode pipelines run in parallel and draw from
one shared random-number service, so the order of draws can change. The signal
is not affected: on channels with ≥ 20,000 electrons the summed `dnnsp` charge
of the two groups agrees to 1e-4. The kit does not touch the random-number
service or the graph, so stock sbndcode probably behaves the same (not
tested). For the on/off comparison it does not matter, because the
noise differs between on and off anyway (the scaling changes the charge
fluctuations, which shifts the random sequence).

**Route B.** `scripts/build-wct-yz.sh` (fresh clone of the branch at
6fdb9371, same flags) built in 12 min with 12 jobs, and `DepoTransformYZ` is in
its `libWireCellGen.so`. A 1-event on run with it is bit-identical to a route-A
run in the same noise group.

**`--map`.** A copy of the map under another absolute path, given with
`--map`, is read from that path and gives output bit-identical to a
default-map run in the same noise group.

## 11. Caveats

- "off" here is stock sbndcode configuration on newer Wire-Cell libraries;
  compare on vs off from this kit, not on vs a CVMFS-sbndcode detsim.
- SimChannels are not scaled (truth stays truth). Anything that uses
  SimChannel charge as "expected reco charge" will see the map as a
  reco/true difference.
- The map is from data (Run 2, gen2, BNB Light) and keeps everything the
  calibration measured, including dead-channel stripes and edge pixels with
  large corrections. Dead channels in the sim come from the channel status,
  not from the map; where the map has no data, the factor is 1.
- Runs are not bit-reproducible (section 10): rerunning an event can give
  another noise realization. Compare distributions, not single channels of
  two runs.
- The kit depends on our read-only install (route A). If we rebuild it, we
  will tell you; route B makes you independent.

## 12. Contacts

- Wire-Cell simulation, this kit, the converter: Haiwang Yu (BNL).
- Issue log, with the map study and the component tests: `../46-sbnd-yz-depo-scaling.md`.
