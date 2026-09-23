# Issue 31: reco1-stage (WCT sim+SP) reproducibility, twester `sbnd_gen2_full` vs abhat reproduction

Tracking: https://github.com/HaiwangYu/wire-cell-toolkit-ai-helper/issues/31

Question (Haiwang, 2026-09-23): Thomas (twester) and Avinay (abhat) each ran
gen -> g4 -> detsim -> reco1 -> reco2 on Aurora with the same workflow.  Did the
reco1 stage see the same g4 input, do both runs carry `simtpc2d:dnnsp`
`recob::Wire`, and are the waveforms identical event by event?

Runs
- A = Thomas: `/lus/flare/projects/neutrinoGPU/twester/scratch/sbnd_gen2_full` (job of 2026-09-21, `debug` queue)
- B = Avinay: `/lus/flare/projects/neutrinoGPU/abhat/sbnd/thomas-g4-parsl-reproduction-20260921` (2026-09-22, `capacity` queue; Thomas's 20 g4 files -> detsim -> reco1 -> reco2 -> caf)

## Where WCT runs in this chain
In SBND the Wire-Cell simulation + signal processing (`simtpc2d`,
`sbnd_wcls_simsp_bothrois`, `wcls-sim-drift-depoflux-nf-sp.jsonnet`) is the
**detsim** stage (`standard_detsim_sbnd.fcl`, process `DetSim`).  Its input is
the g4 file.  reco1 (`standard_reco1_sbnd.fcl`) reads the detsim file, runs
gaushit/ophit/CRT/supera and **passes the `recob::Wires_simtpc2d_dnnsp_DetSim`
product through** (gauss and wiener are dropped by `sbnd_reco1_drops`).  So the
"reco1 wires" of the question are made in detsim; both stages are compared here.

## Answers
1. **Same g4 input: yes.**  Each of the 20 detsim jobs in both runs executed
   `lar -c standard_detsim_sbnd.fcl -s /lus/flare/projects/neutrinoGPU/twester/scratch/sbnd_gen2_full/g4/000000/000000/g4-gen-<uuid>.root`
   (command recovered from the executed Parsl wrapper kept in every
   `000000/000000/subrun_*/detsim-*.err`); the 20 paths are identical in the two
   runs, the files exist, and were last written 2026-09-21 20:30-20:34 UTC,
   before either detsim ran.  The art provenance JSONs agree (B's detsim
   `parents` = A's g4 file; each reco1's parent = its own detsim).  All four
   files of a pair (A/B x detsim/reco1) decode to the same RSE for every entry.
   -> `rse-manifest.tsv`: 88 events, run 1, subruns 0-19 (one g4 file each),
   with entry index, verdicts and the four file paths per event.
2. **Both runs carry `recob::Wires_simtpc2d_dnnsp_DetSim`** in detsim and reco1
   (11276 channels x 3427 ticks, ROIs as `lar::sparse_vector<float>`), plus
   gauss/wiener in detsim only.  Within each run reco1 dnnsp == detsim dnnsp
   byte for byte (pass-through check, 88/88).
3. **Waveforms are NOT identical for every event** -- see the table below
   (SHA-256 of the decompressed per-event basket, one basket = one event).
   Where they differ, the difference is tiny and localized: e.g. RSE 1/16/2
   differs in **one channel of 11276** (ch 342): A has one ROI at ticks
   [325,353), B has it at [321,354) -- an ROI-boundary flip, after which the
   in-ROI baseline shifts by ~2 units on 33 samples.  A different noise
   realization (different RNG call order) would change every channel; it does
   not.  The pattern (few channels, ROI edges, gauss/wiener more often than
   dnnsp, sums equal to 5-6 digits) points to floating-point-level
   non-determinism in SP (thread-order / FFT-plan dependent rounding that
   flips threshold decisions), not to the WCT `Random` seeds.

### Results (compare_wires_hash.py, 2026-09-23)
| product (Thomas vs Avinay) | byte-identical events | differing | samples differing per differing event | largest abs(A-B) |
|---|---|---|---|---|
| dnnsp (reco1 and detsim, identical verdicts) | 76/88 | 12 | 26-187 of 38.6M | 11.6 |
| gauss (detsim) | 51/88 | 37 | 24-4478 of 38.6M | 21 |
| wiener (detsim) | 51/88 | 37 | 24-3884 of 38.6M | 23.4 |

Scale: the mean dnnsp sample inside ROIs is ~20-25 units (FrameSaver q/n, e.g. 1.296e7/515163 for RSE 1/16/2) over 0.2-0.7 M ROI samples per event, so a differing event changes tens of samples by a few units, at ROI edges.
Note: Avinay's `WCT_SIM_SIGPROC_SEED_AUDIT.md` reports 76/88 identical for *all three* tags and 8/20 fully identical subruns; here gauss/wiener differ in 37/88 events (e.g. subrun 1726 events 1 and 6), confirmed independently by the FrameSaver `q`/`n` log lines, so his gauss/wiener numbers look like a comparison of dnnsp only.
Subruns with every event and every product identical: 2, 4, 18 (3/20).
Differing dnnsp events (run/subrun/event: largest abs(A-B), samples differing): 1/10/5 (2.77, 75), 1/10/6 (11.6, 187), 1/17/7 (1.7, 81), 1/17/12 (1.95, 26), 1/13/10 (1.38, 26), 1/12/10 (1.49, 37), 1/9/14 (1.89, 105), 1/9/15 (0.0513, 26), 1/19/8 (2.84, 125), 1/16/2 (2.28, 33), 1/0/11 (4.92, 65), 1/7/3 (8.22, 71).
Pass-through reco1 dnnsp == detsim dnnsp: 88/88 in both runs. RSE decoded from all four files agrees for all 88 events (run 1, subruns 0-19).
Full per-event table: `rse-manifest.tsv` (this folder); stdout of the run: `compare-summary.txt`.

Independent cross-check from the WCT `FrameSaver` lines in the detsim stderr
(charge sum `q` to 6 digits and sample count `n`, per event): dnnsp identical
77/88, gauss 51/88, wiener 51/88 -- consistent with the byte comparison.

### Everything else that was compared
- Executed wrappers (`detsim-*.err`, `reco1-*.err`) differ only in paths, the
  metadata-injector tags, and B's two extra bind mounts (`-B .../abhat`,
  `-B .../scisoft/envs`).  Same container, same
  `sbndcode-v10_14_02_05.env`, same tarball extraction to `/tmp`, same
  `FHICL_FILE_PATH`, same `lar` options (`--nevts=-1`).
- The per-subrun fcl dumps are identical apart from the metadata block
  (`applicationVersion` v10_06_00_04 vs v10_14_02_05 is a stale tag in A's
  TOML, see Avinay's `THOMAS_STAGE_VERSION_AUDIT.md`; the runtime is
  v10_14_02_05 in both).  `enableLowROIThresholds: true` in both.
- `runinfo/config.toml`: B differs in queue/allocation/walltime/retries,
  `nevts = -1` vs 15, `full_keep_fraction`, `g4_input_dir`, `files_per_subrun`
  and the caf stage -- nothing that touches detsim/reco1 content.
- Avinay's own reports are in `<B>/THOMAS_G4_PARSL_REPRODUCTION_REPORT.md`,
  `<B>/comparison/*.md` (he found 76/88 byte-identical for all three wire
  tags and hypothesised TBB scheduling on the shared `RandomT` engine; his
  1-event repeat runs were bit-identical with and without `max_threads: 1`).

## scripts/
All run on an Aurora UAN with `$Y/tools/venv-wire-viewer` (python/3.12.12
module + `pip install uproot awkward bokeh numpy matplotlib`); no container,
no ROOT dictionaries (login nodes cannot run apptainer).
- `wirebytes.py` -- decodes the member-wise streamed `vector<recob::Wire>`
  basket bytes (channel, view, `sparse_vector` ROIs) and the RSE from
  `EventAuxiliary`.  Validated against WCT's own `FrameSaver q=/n=` log lines
  (charge sum and sample count agree for every event checked).  uproot cannot
  interpret these branches itself (`lar::sparse_vector<float>::datarange_t`
  typename + member-wise streaming).
- `compare_wires_hash.py` -- pairs the runs from the provenance JSONs, checks
  the RSE of all four files, hashes the per-event baskets (reco1 dnnsp,
  detsim dnnsp/gauss/wiener), decodes and records max|A-B| / #samples /
  sums, pass-through check; writes `rse-manifest.tsv` (`compare-summary.txt`
  is its stdout).  ~30 min for 88 events (file opens on Lustre dominate).
- `compare_wires_rse_viewer.py` + `serve-viewer.sh` -- Bokeh server viewer:
  A / B / A-B 2D panels (channel x tick, max-|v| pooled on zoom), tap for 1D
  waveforms, largest-|A-B| table, APA/plane selection, product selector
  (dnnsp reco1 / dnnsp, gauss, wiener detsim); navigation by **prev/next
  buttons, an RSE text box ("1/16/6") and a drop-down of all 88 RSEs with
  the verdict**.  Run `scripts/serve-viewer.sh 5031` on a UAN, then
  `ssh -L 5031:localhost:5031 <user>@<that uan>.alcf.anl.gov` and open
  http://localhost:5031/compare_wires_rse_viewer .

## log
- 2026-09-23: explored both runs, wrote the decoder/comparison/viewer, ran the
  88-event comparison (results above), issue opened.
