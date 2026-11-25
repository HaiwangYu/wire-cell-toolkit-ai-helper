# Issue 46: why the SBND Wire-Cell detsim is not bit-reproducible, and the fix (2026-11-25)

Follow-up to the kit validation (`yz-sim-kit/README.md` §10): running the same
event twice with the same configuration and libraries gave one of two noise
realizations.

Study outputs: `/exp/sbnd/data/users/yuhw/YZ-non-uniformity/rng-study/`
(`kit-copy/` = a copy of the kit with the two study toggles, `runs/<variant>/detsim/`,
`results/*.txt`, `config-check/`). Scripts: `scripts/rng/` (copies; they point
at the study directory):

- `run-rng-job.sh <outdir> <on|off> <TbbFlow|Pgrapher> <shared|separate> <nskip> <nev> [aslr-off] [seed]`:
  one detsim job with the study kit copy. It also writes the sim RawDigits
  (`simtpc2d:daq`, outputer `wclsFrameSaver:simdigits`) so the noise can be compared.
- `rngcmp.py groups <files>`: groups files by bit-identical products (RawDigits,
  `dnnsp`, `gauss`, `wiener`, SimChannels) and counts differing channels per plane.
- `rngcmp.py noise <A> <B>`: raw-digit comparison of two events: quiet channels
  (no SimChannel charge within ±20 channels of the same plane) and near-signal channels.
- `config-check.sh`: compiles the WCT configuration of all 8 variants.
- `kit-rng-variant.diff`: the change to the kit (cfg + fcl) used here.

All jobs: `mu-test/g4.root`, sbndcode v10_14_02_03 detsim, branch WCT (opt-yz).

## 1. The cause

Three facts make the noise depend on the order in which two graph nodes run:

1. **One `Random` for everything.** sbndcode's `pgrapher/common/tools.jsonnet`
   defines one `Random` (engine `default` = `std::minstd_rand0`, seeds `[0,1,2,3,4]`).
   The compiled detsim configuration has five users of it: `Drifter`,
   `DepoTransform(YZ)` apa0 and apa1, `AddNoise` apa0 and apa1. Nothing else uses an `IRandom`.
2. **Only the two `AddNoise` actually draw.** SBND sets `sim.fluctuate: false`
   (`pgrapher/experiment/sbnd/simparams.jsonnet:77`). With it, `Drifter`
   absorbs charge without a binomial draw (`Drifter.cxx:181`), and
   `DepoTransform` does not even look up its `rng` (`DepoTransform.cxx:84-88`;
   `DepoTransformYZ` uses the same configure).
   The two noise nodes (`Normals::make_recycling(m_rng, …)` per call) are the only consumers.
3. **The order of the two `AddNoise` calls is not fixed under `TbbFlow`.** The
   two anode pipelines are parallel branches of the graph after `DepoSetFanout`.
   Whichever `AddNoise` runs first takes the first stretch of the shared
   stream. The other one takes the next stretch. Two orders give two noise realizations.

art runs with `scheduler.num_threads: 1`, and the jobs use 96–98 % of one CPU,
so in practice this is not a data race between threads. The order is decided
by the TBB scheduler, and it depends on memory addresses: with address-space
randomization turned off (`setarch -R`) all six runs fall into one group (see
below). Which container or TBB internal sets the order was not pinned down.
Candidates are the pointer-keyed containers of the WCT TBB wrapper
(`WrapperFactory::seen()` is a `std::map` keyed by node pointer,
`DataFlowGraph::m_nodes` an `unordered_set`) or TBB's own bookkeeping. With more TBB threads there would also be a real data
race on the unprotected engine, because `Gen::Random` has no mutex.

The parent's hypothesis is right, with one refinement: the Drifter and the
DepoTransforms are listed as users of the shared `Random` but never draw from
it in the SBND configuration.

### Evidence (event 1 of `mu-test`, YZ on, all products of `simtpc2d`)

| variant | runs | groups (RawDigits, dnnsp, gauss, wiener) | file |
|---|---|---|---|
| stock: `TbbFlow`, shared `Random` | 6 started together | **2 groups, 3 : 3**; every channel of both TPCs differs between the groups | `results/1b-stock-tbb-groups.txt` |
| stock, under `setarch -R` (no ASLR) | 6 together | **1 group** (the "other" stock group) | `results/1c-aslroff-groups.txt` |
| A: `Pgrapher` (serial), shared `Random` | 6 (3 + 3) | **1 group**, the same bytes as stock group 1 | `results/1-serial-groups-6.txt` |
| B: `TbbFlow`, one `Random` per consumer | 6 (3 + 3) | **1 group** | `results/2a-separate-groups-6.txt` |

SimChannels are identical in every run. Between the two stock groups the raw digits differ on
all 11,276 channels. On the quiet channels the rms of the difference is 2.2–2.7 ADC, which is
independent noise. 85–88 % of the ticks differ (`results/1d-stock-groups-noise.txt`).

### Cost

`simtpc2d` time per event (art TimeTracker, 1 event, 6 jobs at once on sbndbuild03):

| | s/event | job wall | max RSS |
|---|---|---|---|
| stock `TbbFlow` shared | 123.1–125.6 (mean 124.5) | 2:28–2:30 | 6.1 GB |
| `Pgrapher` serial | 121.0–125.4 (mean 122.9) | 2:25–2:33 | 6.2 GB |
| `TbbFlow` separate streams | 121.9–126.8 (mean 124.4) | 2:25–2:34 | 6.1 GB |

There is no measurable difference. With `num_threads: 1`, `TbbFlow` runs on one
thread inside art anyway, so the serial `Pgrapher` loses nothing here.

## 2. Fix by separate RNG streams (variant B)

The kit copy gives each consumer its own `Random` (same engine, seeds
`[0,1,2,3,4, rng_seed, stream]`, stream = 1 drift, 10/11 DepoTransform apa0/1,
20/21 AddNoise apa0/1). It keeps `TbbFlow`. The compiled configuration changes only the five `rng`
references and adds the five `Random` components. With `rng_streams: shared`
the configuration is byte-identical to the kit's, so it is still stock for "off"
(`config-check/`).

**(a) Reproducible:** six runs of the same event, three of them started together, are
bit-identical in all `simtpc2d` products (table above).

**(b) Same noise for YZ off and on.** B off vs B on, event 1
(`results/2b-B-off-vs-on-ev0.txt`):

| plane | quiet ch | quiet bit-identical | near-signal ch | median fraction of ticks off ≠ on |
|---|---|---|---|---|
| East U | 1247 | 1247 | 737 | 0.9 % |
| East V | 938 | 938 | 1046 | 0.4 % |
| East Y | 0 | – | 1670 | 0.2 % |
| West U / V / Y | 1916 / 1935 / 1597 | all | 68 / 49 / 73 | 0 |

For comparison, the noise of the two stock groups gives 85–88 % of ticks
different. The noise is therefore identical, and off − on on signal channels is the
scaled signal only: a few tens of ticks per channel where the rounded ADC
changes. Because `fluctuate` is false there is no fluctuation stream to differ between off and
on. If it were turned on, the DepoTransform streams would differ off/on, but they could no longer
leak into the noise streams.

**(c) Long muons, 10 events, `check_yz_scaling.py` on B off/on:**

`results/2c-check.txt` (B) against `results/2c-check-stock-kitvalidation.txt`.
The second file is the same script on the kit-validation `off/`, `on/` files, which
were stock shared-`Random` jobs. Same 18,504 channel-events. meas/pred − 1: rms, robust rms,
channels > 5 %:

| | dnnsp stock | dnnsp B | gauss stock | gauss B |
|---|---|---|---|---|
| East U | 1.14 / 0.46 / 21 | 0.99 / 0.48 / 25 | 3.87 / 0.67 / 224 | 3.30 / 0.69 / 237 |
| East V | 1.17 / 0.78 / 39 | 1.68 / 0.78 / 32 | 3.42 / 0.96 / 141 | 2.69 / 0.96 / 126 |
| East Y | 0.66 / 0.21 / 2 | 0.53 / 0.21 / 3 | 0.66 / 0.21 / 2 | 0.53 / 0.21 / 3 |
| West U | 1.13 / 0.53 / 16 | 1.18 / 0.54 / 20 | 1.86 / 0.64 / 61 | 2.44 / 0.65 / 71 |
| West V | 1.23 / 0.73 / 15 | 1.22 / 0.77 / 13 | 3.26 / 0.99 / 53 | 2.50 / 1.02 / 59 |
| West Y | 0.68 / 0.23 / 3 | 0.47 / 0.22 / 1 | 0.68 / 0.23 / 3 | 0.47 / 0.22 / 1 |

**The ratio does not get tighter.** The robust rms is the same to 0.04 %, and the
plain rms moves either way by a few tenths of a percent, driven by the few channels above 5 %. The reason
is that the validation off/on jobs were already in the same ordering group:
in the 9 events with one TPC free of signal, that TPC's `wiener` frames are
bit-identical off vs on. So their noise was already identical, and B just draws
another (identical off/on) noise realization. The remaining per-channel scatter
(tails > 5 %, gauss U/V) is not caused by noise mismatch. It comes from the SP and its ROI
decisions reacting to a 1–5 % change in signal on top of the same noise.

For B, all 10 events: off vs on raw digits are bit-identical on every quiet
channel (one exception: 1 of 1,478 East Y channels in event 7, which has
induced signal beyond ±20 wires). On near-signal channels 0.2–0.9 % of the ticks
differ (`results/2b-B10-off-vs-on.txt`, events 1, 4, 7, 10). Event 1 of the
10-event job is bit-identical to the 1-event runs, a seventh reproduction.

## 3. Seeding in production

- **The Wire-Cell detsim does not use art's random service.** The seeds are
  the fixed `[0,1,2,3,4]` in `tools.jsonnet`. `wcls_main` passes no seed, and
  larwirecell's `WCLS` tool only calls the inputers, the app and the outputers
  per event (`Tools/WCLS_tool.cc:208-223`); no component of it reseeds. The engine
  is seeded once at configure time and keeps advancing across the events of a job.
  (`NuRandomService` with `policy: "random"` seeds only the optical and CRT sims,
  so those products differ from run to run by design.)
- **Because only `AddNoise` draws, the noise does not depend on the event.**
  Event 2 of `mu-test`, run as the first event of its own job, has noise
  **bit-identical** to event 1 run as the first event of another job (same ordering group). This holds
  on every quiet channel of all six planes (`results/3-stock-ev0r2-vs-ev1.txt`). Against the run in the
  other ordering group, every channel differs (`results/3-stock-ev0-vs-ev1-separate-jobs.txt`).
- So in stock SBND production **the k-th event of every job gets one of two
  noise frames**, whatever the physics. A sample made of N jobs × M events has
  only about 2M distinct noise realizations, and they repeat in every job. Within a job the events
  differ, because the stream advances (shown for B: events 1 and 2 of one job,
  `results/3-separate-within-job-ev0-vs-ev1.txt`, independent noise). Not tested at
  production scale: the claim follows from the configuration and the two-job test above. For noise-sensitive studies (noise-induced fakes, thresholds,
  DNN training on sim) this correlation matters. It is not caused by this kit;
  the kit inherits it from stock.
- Variant B does not change this: with fixed seeds, the first event of every job
  has the same noise (`results/3-separate-ev0-vs-ev1-separate-jobs.txt`,
  all quiet channels identical). The `rng_seed` knob works: seed 1 vs 0 gives
  independent noise (`results/3-separate-seed0-vs-seed1.txt`, 85–88 % of ticks differ).
  So per-job seeding needs only a fcl override per job, e.g.
  `physics.producers.simtpc2d.wcls_main.params.rng_seed: "<job number>"`.

## 4. Fix options

| option | reproducible run to run | same noise off/on | production independence | cost / scope |
|---|---|---|---|---|
| A. `Pgrapher` instead of `TbbFlow` | yes (serial order is fixed) | only while `fluctuate` is false; with fluctuation on, the draws before the noise depend on the charge, so off/on noise would differ | unchanged (fixed seeds) | cfg + fcl `apps`; no speed loss at `num_threads: 1`, but it gives up any future intra-event parallelism |
| B. one `Random` per consumer (cfg) | yes, under any scheduler and thread count | yes, also with `fluctuate` on | unchanged with fixed seeds; with `rng_seed` per job, fixed | cfg only (kit jsonnet), no C++; the noise realization differs from stock |
| C. mutex in `Gen::Random` | no: removes the data race (relevant with more threads) but not the order dependence | no | unchanged | C++ in WCT |
| C'. thread-local engines | no: TBB tasks are not bound to threads, so who draws what still depends on scheduling | no | unchanged | C++ in WCT |
| D. per-event reseed (e.g. from run/subrun/event, or art's `NuRandomService`) | yes, and independent of how events are split into jobs | yes, if combined with B | fixed per event, the best for production | C++ (a larwirecell `IArtEventVisitor` that reseeds, or reseed support in `Random`); for SBND/WCT upstream |

Options C and C' do not make the output reproducible; they only make it thread-safe. B is the
smallest change that fixes both reproducibility and the off/on noise
match, and it is safe if SBND ever turns `fluctuate` on. A per-job `rng_seed` (B) or
per-event reseeding (D) is needed for production independence.

## 5. Proposed change to the kit (not applied)

Add a second toggle next to `yz_scaling` (see `scripts/rng/kit-rng-variant.diff`;
the diff also carries the study-only `wct_app` knob, which the kit does not need):

- `physics.producers.simtpc2d.wcls_main.params.rng_streams: "shared" | "separate"`,
  default `"shared"`: then `check-config-identity.sh` still gives stock ==
  off byte for byte.
- `physics.producers.simtpc2d.wcls_main.params.rng_seed: "0"`, used only with
  `separate`; set a different value per grid job.
- `sim-yz.jsonnet` gets an optional `rngs` argument: `{drift, dt[anode], noise[anode]}`.
  `wcls-sim-drift-depoflux-nf-sp-yz.jsonnet` builds the five
  `Random:rng-*` components when `separate` is set.
- New wrappers, or a note in README §10, that recommend `separate` for every
  on/off comparison. README §10 should be corrected: the noise of off and on in
  stock mode is *not* different because of the scaling ("the scaling changes the charge
  fluctuations"). SBND has `fluctuate: false`, so off and on have the same noise
  whenever the two jobs fall in the same ordering group, which they did in the
  10-event validation: in the 9 events with one TPC free of signal, that TPC's
  `wiener` frames are bit-identical off vs on. They differ
  only when the jobs fall in different groups.
