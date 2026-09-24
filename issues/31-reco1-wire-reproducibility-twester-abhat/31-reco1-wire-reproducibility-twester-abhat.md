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
RSE lists (identical / non-identical dnnsp, with gauss/wiener verdicts): `dnnsp-rse-lists.md`.
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
- `compare_wires_3way.py` -- three-run version (T / A1 / A2, detsim files, ROI-structure vs values-only split, 3-way class per tag) -> `rse-manifest-3way.tsv`; ~65 min.
- `compare_wires_rse_viewer.py` + `serve-viewer.sh` -- Bokeh server viewer:
  A / B / A-B 2D panels (channel x tick, max-|v| pooled on zoom), tap for 1D
  waveforms, largest-|A-B| table, APA/plane selection, product selector
  (dnnsp reco1 / dnnsp, gauss, wiener detsim); navigation by **prev/next
  buttons, an RSE text box ("1/16/6") and a drop-down of all 88 RSEs with
  the verdict**.  Run `scripts/serve-viewer.sh 5031` on a UAN, then
  `ssh -L 5031:localhost:5031 <user>@<that uan>.alcf.anl.gov` and open
  http://localhost:5031/compare_wires_rse_viewer .

## Three-run comparison (2026-09-24): is the T vs A1 difference a config/library difference or non-determinism?

Avinay repeated his chain unchanged (same TOML except the output path, same
wrapper, same fcl, same env/tarballs, same 20 g4 files) as **A2 =
`/lus/flare/projects/neutrinoGPU/abhat/sbnd/thomas-g4-parsl-rerun-20260924`**
(PBS 8862650, node x4714c4s1b0n0; A1 ran on x4604c5s2b0n0, Thomas on
x4204c3s6b0n0).  `compare_wires_3way.py` compares T / A1 / A2 event by event
(`rse-manifest-3way.tsv`, `compare-3way-summary.txt`, tables in
`threeway-rse-lists.md`):

| tag | T vs A1 identical | T vs A2 identical | A1 vs A2 identical | 3-way: all_same / A1=A2!=T / T=A2!=A1 / T=A1!=A2 / all_differ |
|---|---|---|---|---|
| dnnsp | 76/88 | 74/88 | 72/88 | 67 / 5 / 7 / 9 / 0 |
| gauss | 51/88 | 38/88 | 42/88 | 31 / 11 / 7 / 20 / 19 |
| wiener | 51/88 | 38/88 | 42/88 | 31 / 11 / 7 / 20 / 19 |

**Verdict: hypothesis 2 (non-determinism), not hypothesis 1.**
- Avinay's own two runs differ from each other as much as, or more than, either
  differs from Thomas (A1 vs A2 gauss 46 differing events vs T vs A1 37).  A
  deterministic library/configuration difference between the two installations
  would make A1 == A2 in every event and T != A1 in a fixed set; instead every
  3-way class is populated, including "T = A2 != A1" (Thomas agrees with the
  rerun but not with run1) and "all three differ".
- 23/88 events (subrun 2 entirely) are identical in all three runs for all
  tags.  Identity is the default outcome; a difference is a rare flip.
- The flips are discrete decisions, not visible rounding noise: over all pairs
  and tags 1806 differing channels have a **different ROI (offset, length)
  list** and 118 have identical ROIs with a subset of samples changed by
  0.06-0.6 (tight-ROI / sub-ROI decisions inside the same ROI).  The
  magnitude is 1-24 units on 26-4500 samples of 38.6 M per differing event,
  1-124 channels of 11276.  gauss and wiener always flip together (same
  OmnibusSigProc path); dnnsp flips are rarer (the DNN ROI finder) and never
  in an event where gauss/wiener flip too.
- Consistent with the WCT `TbbFlow` graph run with unlimited TBB threads
  inside 102 concurrent `lar` processes on a 208-thread node (Parsl
  `cores_per_worker = 1`): the order of the Retagger output lines in the
  detsim stderr already differs between runs in 24 of 264 (event, run) cases,
  proof that the graph's task order is not fixed.  The likely mechanism is
  reduction/FFT-order dependent rounding in SP that occasionally crosses an
  ROI threshold; the raw noise itself is not the difference (a different noise
  realization would change every channel), so the fixed WCT `Random` seeds
  are not the cause.  Which step is order-dependent is not established here;
  a controlled test (one subrun, same node, `max_threads: 1` vs default,
  several repeats, and `WIRECELL_THREADS`/FFTW plan pinned) is the next step.

Everything else between A1 and A2: the executed wrappers and fcl dumps are
identical except the output paths and JSON names; `art::RNGsnapshots`,
CRT and PMT products differ by design (`NuRandomService` policy `random`);
G4 truth branches identical; reco1 dnnsp pass-through 88/88 in A2 as well.
Avinay's report of the rerun: `<A2>/OUR_RUN1_VS_RUN2_REPRODUCIBILITY_REPORT.md`
(52/88 differing events in his count, same conclusion).

Viewer: `compare_wires_rse_viewer.py` now takes the 3-way manifest by
default; two drop-downs choose which runs are A and B (Thomas / Avinay run1
/ Avinay run2), the RSE list shows the 3-way class of the selected product,
and `--run-a/--run-b` set the start.  Restart `scripts/serve-viewer.sh` to
pick the new version up.

## Candidate causes in the WCT git history (2026-09-24)

`git log --grep` over `$Y/wire-cell-toolkit` (branch `polaris-build-fixes`,
9195180d) for random/determinism/reproducibility, checked against the
production release: sbndcode v10_14_02_05 runs **wirecell v0_32_1** (source at
`/lus/flare/projects/neutrinoGPU/scisoft/larsoft/wirecell/v0_32_1/source/wirecell-0.32.1`).
Two fixes for run-to-run non-determinism in NF/SP landed in **0.35.0** and are
**not in 0.32.1**; both bugs are verified present in the production source:

1. **47d16673 (2026-04-29) aux/FftwDFT: fix run-to-run non-determinism in FFTW plan cache.**
   The plan-cache key contained `aligned = ((src&15)|(dst&15))==0`, a function of
   heap buffer addresses, so between processes a different cached FFTW codelet
   (SIMD vs scalar) was picked, giving ULP-level differences that "propagated
   through NF coherent subtraction and SP deconvolution FFTs, producing ... up
   to ~434 ADC structural differences in SP output".  Fix: `FFTW_UNALIGNED` on
   all 7 plan creations and the bit dropped from the key.  Production
   `aux/src/FftwDFT.cxx` line 32-33 still has the `aligned` bit and no
   `FFTW_UNALIGNED`.  This mechanism matches what is seen here exactly: rare
   discrete ROI flips (a rounding difference crossing a threshold), different
   from run to run of the same binary on the same input, independent of the
   WCT `Random` seeds, and it needs no thread-order argument at all.
2. **36489a20 (2026-05-06) sigproc/OmnibusSigProc: fix uninitialized FFT-padding rows in decon_2D_looseROI.**
   Rows `m_nwires..m_fft_nwires-1` of `c_data_afterfilter` were never written;
   the inverse FFT spread heap garbage into the last `m_pad_nwires` wires of the
   plane (max|d| 692 ADC on PDVD, 12 runs -> 3 distinct outputs).  Production
   `OmnibusSigProc.cxx` `decon_2D_looseROI` still fills only
   `m_channel_range[plane]` rows (line ~1407).  Would show up as differences
   concentrated in the last ~10 wires of a plane.

Related, also post-0.32.1: dc613760/9b4ebd5f (iterator UB / use-after-free in
`ROI_refinement::BreakROIs`, 0.35.0), 43948005 + dd97c3b3 (L1SPFilterPD
determinism doc and PDVD anode-0 NF+SP regression test), e92429a6 (clustering
`cluster_less` tie-breakers, 0.33.0, clus only).  In 0.32.1 already: ec0877d7
(gen BinnedDiffusion "random fix: set not needed", 0.32.0).  The shared
`RandomT` engine without a mutex (Avinay's hypothesis) is unchanged in all
versions; AddNoise draws are not the cause here since a different noise
realization would alter every channel.

Test that would settle it: rebuild 0.32.1 + 47d16673 (+ 36489a20) and rerun one
differing subrun several times; or run the production binary twice on the same
node with ASLR disabled (`setarch -R`) -- identical output would confirm the
address-dependent plan key.  Check also whether the channels touched here sit
in the last ~10 wires of a plane (bug 2) or anywhere (bug 1).

## log
- 2026-09-24 (b): WCT git history: two NF/SP non-determinism fixes (FFTW plan-cache alignment key 47d16673, uninitialized looseROI padding rows 36489a20) are in 0.35.0 but not in production 0.32.1; bugs verified in the production source.
- 2026-09-24: Avinay's rerun A2 added; three-run comparison (section above): non-determinism confirmed, not a config difference; viewer generalized to three runs.
- 2026-09-23: explored both runs, wrote the decoder/comparison/viewer, ran the
  88-event comparison (results above), issue opened.
