# SBND img-clus-match-pr production on Aurora (ALCF): setup + validation plan v2

Goal: reproduce the Polaris workflow (`polaris-img-clus-match-pr-production-plan.md`,
issue 27: local WCT `polaris-build-fixes` = master `67e2eba7` + 2 warning fixes
`9195180d`, larwirecell `dev-v10_14_02_02` `a02a1a4`, SL7 container, 1-step
`img-clus-match-pr`) on **Aurora**, validate it bit-for-bit against the FNAL and
Polaris runs, and use Aurora's ~100 cores/node and the SBND official Gen2 reco1
artROOT already on `/lus/flare` for the large scaling tests and the 1M-event
production.

v1 was written 2026-09-16 from the ALCF docs and `sbank` before anyone had
logged into Aurora. **v2 (2026-09-16, later the same day) is the review of v1
from an Aurora login node (`aurora-uan-0010`)**: everything marked **measured**
was observed there; **doc** = docs.alcf.anl.gov; **open** = needs the probe job
(nothing has run on a compute node yet). Section 0 lists what v1 got wrong.
Tracking issue: https://github.com/HaiwangYu/wire-cell-toolkit-ai-helper/issues/29

Local copies on Flare (`Y=/lus/flare/projects/neutrinoGPU/yuhw`, cloned 2026-09-16
from GitHub on the UAN, which has direct internet):

| dir | remote / branch | commit |
|---|---|---|
| `$Y/wire-cell-toolkit` | `HaiwangYu/wire-cell-toolkit` `polaris-build-fixes` | `9195180d` (= master `67e2eba7` + 2 fixes) |
| `$Y/larwirecell` | `HaiwangYu/larwirecell` `dev-v10_14_02_02` | `a02a1a4` |
| `$Y/wcp-porting-validation` | `WireCell/wcp-porting-validation` `main` | `794e470c` |
| `$Y/wire-cell-data` | `WireCell/wire-cell-data` `master` | `74ff57a` (646 MB; **lacks `uboone/weights/XGB_nue_seed2_0923.xml`**, as on Eagle) |
| `$Y/wire-cell-toolkit-ai-helper` | `HaiwangYu/wire-cell-toolkit-ai-helper` `main` | this repo |
| `$Y/cvmfsexec` | `cvmfs/cvmfsexec` `v4.53-2-gd99b7c5`, `makedist -m rhel8-x86_64 osg` done (167 MB `dist/`), `default.local` = proxy + `CVMFS_CACHE_BASE=/tmp/cvmfs-cache` (jobs `sed` it) | template, never run in place |
| `$Y/aurora-build-logs` | job `-o` files | |

Still to bring over (not in any git repo): the 19-event nc-sideband file
(`sbnd-gen2-data/nc-sideband-lynn/filtered-reco1/nc-sideband_filtered_frameshift.root`,
100 MB), the FNAL reference run dir `production-prep/r3-ncpi0-lynn-2026-09-15`,
the Polaris validated run `production-prep/ncsb-data-nuebdt-20260916-0446`
(for the 3-way check), `uboone/weights/XGB_nue_seed2_0923.xml` (199 MB) and any
other FNAL `$WCD` file missing from the GitHub wire-cell-data, and (optional,
for the binary cross-check) the Polaris `opt/`. Route: Globus
`alcf#dtn_eagle` -> `alcf#dtn_flare` (Eagle is **not** mounted on Aurora, see 1.1).

---

## 0. Review of v1: what changed and why

| v1 said | v2 measured / found | consequence |
|---|---|---|
| main pot 14186 (6,907 h) restricted to twester; ask for access (Q8) | **a second, unrestricted suballocation `17257` holds 28,261.7 node-hours** (2026-08-27 -> 2026-10-01, `Restricted: 0`, `Users: None`); `debug2` (14454) 472 h also unrestricted. The project-wide net balance is only +151 h because 15 restricted suballocations are overdrawn (down to -15,607) | production has a pot without asking; but confirm with twester/PI that 17257 is meant for this and that the overdrawn subs do not block scheduling (open) |
| Flare project quota "default 1 TB" (R1, Q5) | `lfs quota -p 11449 /lus/flare`: **3.045 PB used of a 3.2 PB soft / 3.52 PB hard quota, 222.8 M files**. Flare itself is 91 PB, 67 % full (it is the old Grand hardware, mount source `/grand`) | ~155 TB headroom to the soft limit; our 7 TB of outputs fit, but the project is at 95 % and the *file count* is the real hazard -> tar outputs per file/node; coordinate with twester |
| `/lus/eagle` maybe on login nodes ("the user reports yes"), maybe on compute | **not mounted on the UAN** (`df /lus/eagle`: no such file); `-l filesystems=` only knows `flare`, `home`, `daos_*` | nothing can be `cp`'d from Eagle; git repos re-cloned from GitHub (done); the 4 non-git items go by Globus |
| login-node cgroup limits like Polaris (8 CPU / 8 GiB) | **no cgroup limits** on the UAN (104 cores, 1 TB, 78 users, load ~90); direct internet (GitHub, CVMFS stratum-1, scisoft all reachable without proxy) | builds could run on the UAN if a container could... |
| cvmfsexec on the login node as on Polaris | **impossible on the UAN: `user.max_user_namespaces = 0`** (`unshare -U` -> "No space left on device"), and `module load apptainer` (1.2.5, `/opt/aurora/26.26.0/spack/...`) ships a non-setuid `starter` only -> **no container of any kind on the login node**; `/dev/fuse` + `fusermount3` exist but are useless without the container | every SL7 step (build, compile config, run, ROOT compare) is a job; the UAN does git, Globus, Bee upload, editing |
| twester's tree has sbndcode `v10_14_02_04/05`, ours is `_03` -> mismatch | `/lus/flare/projects/neutrinoGPU/scisoft/larsoft/` **has `sbndcode v10_14_02_03` and `larsoft v10_14_02_02`** (our exact pairing), plus `cetmodules v3_24_00`, `cmake v3_27_4`, `gdb v13_1`, `libtorch v2_1_1b`, `gojsonnet`, 173 products, a plain `setup` file; twester launches it with `module load apptainer; module load fuse-overlayfs; singularity run -B /lus/flare slf7.sif` + `source .../scisoft/larsoft/setup; setup sbndcode ... -q e26:prof` (no squashfs overlays on Aurora). Missing for us: `spdlog v1_14_1`, `fmt v11_0_2` (both on scisoft as `*-sl7-x86_64-e26-prof.tar.bz2`), `patchelf` (not on scisoft), `scn v01_00_00` (uboone CVMFS only), and `-devel` headers (`slf7.sif` is bare SL7.9) | **Recipe A' becomes the primary recipe**, not the fallback: ~3 tarballs + one CVMFS product + a dev image, no network or FUSE at run time. Recipe B (cvmfsexec) is only a bootstrap convenience *if* the probe shows FUSE-in-userns works on compute nodes |
| queues from the docs | `qstat -Qf` **measured**: `debug` 1-2 nodes / 1 h, 1 running per user, 64 nodes total; `debug-scaling` **1**-256 nodes / 1 h, 1 job per user; `capacity` 1-16 nodes / 168 h, 2 running + 5 queued per user, 512 nodes total; `prod` routes >= 256 nodes to `small` (256-1,024, 12 h), `medium` (1,025-1,999, 18 h), `large` (2,000+, 24 h), 10 queued per project; `tiny` (1-512 nodes, 6 h) exists but is **disabled**. Load: 8,089 job-exclusive, 2,426 free, ~100 down/offline of 10,624; `debug` 6 running / 10 queued, `debug-scaling` 11 / 9 | the plan's queue choice (`debug-scaling` up to 256 nodes for the scaling test, `capacity` for the long production) stands; `debug-scaling` also takes 1 node, so `debug` is not needed |
| Q4: Gen2 reco1 path, dataset, size, MC/data unknown | **answered**, section 1.5 | 1M events = ~75k files = ~28 TB read in place; MC fcl |

Verdict on v1: the phase structure (A0-A5), the gates (exact 19/19 vs FNAL and
Polaris, operating-point gate, ldd/RPATH gates), the sizing method and the
per-file granularity idea are right and kept. The mechanics were wrong in
three places that change the work: no containers on the login node, Recipe A'
is the production recipe, and the allocation/quota picture is the opposite of
what v1 assumed (plenty of node-hours, a nearly full project quota).

---

## 1. What we know

### 1.1 Machine

| | Aurora (**measured** unless marked) | Polaris (for contrast) |
|---|---|---|
| login node | `aurora-uan-00NN`, SLES 15 SP4, 104 cores, 1 TB, no cgroup limits, direct internet; root fs and `/tmp` are a 504 GB tmpfs | SLES 15 SP7, 8 CPU / 8 GiB cgroup, direct internet |
| compute node (doc) | 2 x Xeon Max (SPR) 52 cores each, 208 threads, cores 0 and 52 reserved -> 102 usable; 1 TB DDR5 + 128 GB HBM; 6 PVC (idle for us); 10,624 nodes | 32 cores / 64 threads, 512 GB, 4 A100 |
| scheduler | PBS Pro, `-A neutrinoGPU::<sub>` (submanagement on), `-l filesystems=flare:home` | same, `home:eagle` |
| filesystems | `/lus/flare` (91 PB Lustre, project dir `/lus/flare/projects/neutrinoGPU`, quota above), `/home` (Gecko Lustre, 150 GB/user), DAOS; **no Eagle, no Grand** | Eagle, Grand, `/local/scratch` NVMe |
| node-local scratch | **open** (docs mention none; `/tmp` on the UAN is tmpfs, on compute probably too) | 2.9 TB NVMe |
| network from compute | `proxy.alcf.anl.gov:3128` only (doc + twester's scripts) | same |
| containers | `module load apptainer` (1.2.5) + `module load fuse-overlayfs`; twester runs `singularity run -B /lus/flare slf7.sif` with no mode flag and the docs use `--fakeroot` -> user namespaces are evidently **enabled on compute nodes** (off on the UAN) | spack apptainer 1.3.6 `--userns` |
| CVMFS | none; cvmfsexec **open** on compute (needs FUSE inside a userns) | cvmfsexec works |
| SL7 image on Flare | `/lus/flare/projects/neutrinoGPU/containers/slf7.sif` (bare SL7.9, no `-devel`) | same image on Grand |
| UPS tree on Flare | `/lus/flare/projects/neutrinoGPU/scisoft/larsoft` (see 0.) | squashfs images of the same tree |

### 1.2 Queues (measured, `qstat -Qf`, 2026-09-16)

| queue | nodes | walltime | per-user / per-project limits |
|---|---|---|---|
| `debug` | 1-2 | 5 min - 1 h | 1 running/user; 64 nodes total; docs: non-exclusive |
| `debug-scaling` | 1-256 | 5 min - 1 h | 1 job/user (running or queued) |
| `capacity` | 1-16 | 5 min - 168 h | 2 running + 5 queued/user; 512 nodes total |
| `prod` -> `small` | 256-1,024 | <= 12 h | 10 queued/project (`prod` itself 100) |
| `prod` -> `medium` / `large` | 1,025-1,999 / 2,000+ | <= 18 h / 24 h | same |
| `tiny` | 1-512 | <= 6 h | **disabled** |

1M events at 45 s/event on 100 procs/node is ~125 node-hours: one 128-node
`debug-scaling` hour, or 16 `capacity` nodes for ~8 h (section 4).

### 1.3 Allocation (measured, `sbank-list-allocations -p neutrinoGPU -r aurora`, 2026-09-16)

| suballocation | balance (node-h) | access | use |
|---|---|---|---|
| **17257** (alloc 17249, 2026-08-27 -> 2026-10-01) | **28,261.7** | unrestricted | scaling + production (confirm intent with twester/PI) |
| 14454 `debug2` | 472.2 | unrestricted | probe, builds, validation |
| 14186 (primary, `Subname None`) | 6,907.3 | restricted: twester | not needed |
| 15405 `SBNDDetVarReprocess_Fall2025` | 1,228.5 | restricted: twester | |
| 15 others | -12 to -15,607 | restricted | project net balance +151.2 h |

All end 2026-10-01 and renew monthly (user). **Open:** whether an overdrawn
project-wide balance affects our jobs (submit the probe on `debug2` and see).

### 1.4 Colleagues' Aurora infrastructure (measured on Flare)

- `scisoft/larsoft/`: 173 UPS products incl. `sbndcode v10_14_02_03`, `larsoft v10_14_02_02`,
  `larwirecell v10_01_26_01`, `wirecell v0_32_1`, `spdlog v1_9_2` (the ambient
  pair we override), `cetmodules v3_24_00`, `cmake v3_27_4`, `gdb v13_1`,
  `libtorch v2_1_1b`, `sbnd_data`, `gojsonnet`; `setup`, `setups`; no `fmt`, no
  `patchelf`, no `scn`. Pre-computed env files `larsoft_hpc/envs/sbndcode-v10_14_02_0{4,5}.env`
  (918 lines) avoid `setup` per job; `larsoft_hpc/` also has the parallel
  `pullProducts` and `create_env_file.sh`. Bundle manifests for `sbnd-v10_14_02_04/05`
  and `larsoft-v10_14_02_s131-e26` in `larsoft_hpc/manifest_cache/`.
- Launch pattern (`twester/share/run_fcl.sh`, `test_lar_fail.sh`): `module load apptainer;
  module load fuse-overlayfs; singularity run -B /lus/flare/ $CONTAINER <<EOF
  source /lus/flare/projects/neutrinoGPU/scisoft/larsoft/setup; setup sbndcode vX -q e26:prof; ... EOF`.
- twester runs SBND production on Aurora (Gen2 productions in 1.5, detvar
  reprocessing, raw data under `/lus/flare/projects/neutrinoGPU/sbnd/data/0180xx/`).
  **The person to ask** about 17257, quota, output location and the debug-queue
  sharing behaviour.

### 1.5 Input: the official Gen2 reco1 (measured)

`/lus/flare/projects/neutrinoGPU/twester/sbnd_gen2_prod{1,2,3}/Gen2_2026/reco1/NNNNNN/MMMMMM/`
(250 x 10 = 2,500 leaf dirs per production, 100 reco1 files each; prod1 holds
749,931 files = ~250k reco1 + hists + json).

| | value (sample: prod1 `reco1/000000/*`, 1,000 files) |
|---|---|
| sample | MC `prodgenie_corsika_proton_rockbox0p1_sbnd` (BNB nu + CORSIKA cosmics, rockbox dirt filter), `file_type: mc`, `production.name: MCP2023Blike`, `production.type: polaris` |
| software | sbndcode **v10_14_02_03** (our pairing), `standard_reco1_sbnd.fcl` <- `standard_detsim_sbnd.fcl` <- `standard_g4_rockbox_sbnd.fcl` <- gen |
| run/subrun | run 301, **one subrun per file** (subrun = file index), events sparse (dirt filter) |
| events/file | **13.24** mean (2-25) |
| size | 376 MB/file, **28.4 MB/event**; ~3.3 M events and ~94 TB per production; **1M events ~ 75.5k files ~ 28 TB**, read in place |
| products | detsim keeps `sim::SimEnergyDeposit ionandscint:priorSCE`, drops `opdaq` waveforms; reco1 drops `recob::Wire *:gauss` and `*:wiener` and RawDigits -> the surviving wires are **`simtpc2d:dnnsp`**, exactly what `wcls-img-clus-matching-xin.fcl` reads (`recobwire_tags simtpc2d:dnnsp`, `summary_tags simtpc2d:wienersummary`, `input_mask_tags simtpc2d:badmasks`, `opflashtpc0/1`, MCTruth/MCParticle/SED for the labeler). **Open:** confirm with `eventdump.fcl` in the probe (A1) |
| fcl | **MC**: `wcls-img-clus-matching-xin.fcl`; no FrameShift |
| metadata | `<file>.root.json` next to each file (`event_count`, `runs`, `mc.pot`) -> the manifest can be built without opening ROOT files |

Proposal for the 1M-event sample: prod1 `reco1/000000` .. `reco1/000075`
(76 x 1,000 files x 13.24 = 1.006 M events), or the same count spread over the
three productions if they differ in configuration (decision 1).

### 1.6 What transfers from Polaris unchanged

- **Binaries.** WCT was built with generic flags (`-O3 -g -fno-omit-frame-pointer`,
  no `-march`) against e26 products: x86-64 portable. We rebuild on Aurora for
  provenance (8 min on a node) and cross-check against the Polaris `opt/` if it
  is brought over.
- **Scripts.** `issues/27-polaris-production/scripts/*` need: `Y` on Flare (14
  `lus/eagle` references), the container launch (`module load apptainer` +
  `fuse-overlayfs`, no `--userns`, `-B /lus/flare`), `-l filesystems=flare:home`,
  `-A neutrinoGPU::debug2`, the log dir `$Y/aurora-build-logs`, and the
  environment source (A' UPS tree instead of `/cvmfs/...setup_sbnd.sh`).
- **Gates and reference data.** The 19-event nc-sideband file and the FNAL run
  `r3-ncpi0-lynn-2026-09-15` give the **exact 19/19** target; `compare-to-fnal.sh`
  is the gate (its ROOT parts run in a job now, the Bee upload on the UAN).
  Two vendors already agree bit-for-bit (FNAL vs Polaris AMD); Intel SPR is
  expected to as well.

---

## 2. Open questions (the probe job answers Q2/Q3/Q4-products; the rest are decisions)

- **Q1 login nodes.** Answered: no limits, direct internet, **no containers**.
  Eagle not mounted -> Globus (`alcf#dtn_eagle` -> `alcf#dtn_flare`, or a
  personal endpoint on the UAN restricted to `/lus/flare/projects/neutrinoGPU`).
- **Q2 compute nodes (probe).** `user.max_user_namespaces`, `unshare -U -r`,
  `/dev/fuse`, `apptainer exec slf7.sif` with no flag / `--fakeroot` / `--userns`,
  does `.sif` exec need `unsquashfs` (1.2.5 links `squashfuse`), node-local
  scratch (`/tmp` size and type, anything NVMe), `/lus/eagle` (expected absent),
  proxy reachability (GitHub, stratum-1, scisoft, DockerHub for the dev image),
  cvmfsexec through the proxy, `debug` node sharing (cpuset, other users' processes).
- **Q3 software delivery.** Recipe A' primary (1.4, 3.A2). Its only network-free
  gap is `scn v01_00_00` (uboone CVMFS) and the `fnal-dev-sl7` image for
  building; both are one-time fetches (cvmfsexec on a compute node if it works,
  else rsync from the Polaris login node -> Eagle -> Globus).
- **Q4 inputs.** Answered (1.5) except the product list (probe).
- **Q5 Flare space.** ~155 TB headroom to the project soft quota; outputs 7 TB
  fit. Tell twester; avoid millions of small files (tar per input file).
- **Q6 granularity.** **Per input file** (`lar -s <file> -n -1`, ~13 events, ~10
  min at 45 s/event): amortises the 20 s startup + 62 s first torch import over
  13 events and cuts the process count 13x; per-event RSE bookkeeping from
  `Trun` (group mode gated byte-identical to per-event in sbnd_xin doc 109).
  Per-event stays for the 19-event validation (same harness as FNAL/Polaris).
- **Q7 queue waits.** Measure: `debug2` probe, `debug-scaling` at 1 / 8 / 64 /
  128 nodes, one `capacity` job.
- **Q8 allocation.** `debug2` for A1-A3; **17257** for A4-A5 after confirming
  with twester/PI.
- **Q9 (new) start-up storm.** 100 `lar` per node x 128 nodes = 12,800 processes
  opening the same ~1,500 shared libraries + a 199 MB XGB file + torch from one
  Lustre tree. twester built squashfs images for exactly this reason ("metadata
  overhead ... prevents scaling to large node counts"). Mitigations, in order:
  stagger starts within a node (e.g. 2 s apart), per-file granularity, copy
  the hot read-only set (`opt/`, wire-cell-data, the XGB file) to node-local
  `/tmp` at job start, and finally a squashfs of `opt`+products mounted with
  `--overlay ...:ro` as twester does. Measure in A4(b) before choosing.

---

## 3. Plan

**Phase A0 (login node) -- done 2026-09-16.** Facts above; repos cloned;
cvmfsexec dist built; `$Y/aurora-build-logs` created; `gh` CLI installed in
`~/bin` (needs `gh auth login` once). Remaining A0 items: Globus transfer of the
4 non-git items (user), a look at 17257 with twester.

**Phase A1 (probe job, `debug`, 1 node, 30 min, `-A neutrinoGPU::debug2`).**
`issues/29-aurora-production/scripts/probe-aurora.pbs`, revised for v2:
node facts (cores, memory, cpuset, `/tmp`, other users' processes), userns
sysctl + `unshare`, `/dev/fuse`, proxy, `module load apptainer` +
`fuse-overlayfs`, `slf7.sif` in the three modes, Recipe A' end to end
(`setup sbndcode v10_14_02_03`, `lar --version`, `lar -c eventdump.fcl -n 1`
on a Gen2 reco1 file with a grep for `simtpc2d dnnsp/wienersummary/badmasks`,
`opflashtpc0/1`, `SimEnergyDeposit ionandscint priorSCE`, `MCTruth`), Recipe B
(cvmfsexec through the proxy, cache on `/tmp`, `fnal-dev-sl7` `lar --version`),
and `apptainer pull docker://fermilab/fnal-dev-sl7` through the proxy (the dev
image for builds, saved to `$Y/images/`). Output answers Q2/Q3/Q4-products.

**Phase A2 (software, Recipe A').**
1. Private UPS overlay `$Y/products/` with `spdlog v1_14_1` and `fmt v11_0_2`
   (scisoft `spdlog-1.14.1-sl7-x86_64-e26-prof.tar.bz2`,
   `fmt-11.0.2-sl7-x86_64-e26-prof.tar.bz2`, downloaded on the UAN), `patchelf`
   0.13.1 (GitHub release binary, or the UPS product rsync'd from CVMFS), and
   `scn v01_00_00` from `/cvmfs/uboone.opensciencegrid.org/products/scn/` (via
   cvmfsexec on a compute node if A1 says yes, else Polaris login -> Eagle ->
   Globus). `PRODUCTS=$Y/products:/lus/flare/projects/neutrinoGPU/scisoft/larsoft`.
   Gate: `ups depend sbndcode v10_14_02_03 -q e26:prof` resolves; `setup spdlog
   v1_14_1 -q e26:prof; setup fmt v11_0_2 -q e26:prof` resolve; `lar --version`.
2. Wrapper `in-aurora-sl7.sh` (port of `in-polaris-sl7.sh`): `module load
   apptainer fuse-overlayfs`, `apptainer exec --cleanenv -B /lus/flare -B /tmp
   $IMG bash -c '...'`, `unset LD_PRELOAD`, proxies, `ulimit -c 0`; `IMG` =
   `fnal-dev-sl7` `.sif` on Flare for builds, `slf7.sif` for runs (or the dev
   image for both -- one image is simpler). `setup-aurora-opt.sh` = `setup-polaris-opt.sh`
   with `Y` on Flare and `source /lus/flare/.../scisoft/larsoft/setup` instead of
   `setup_sbnd.sh`; `setup-aurora-dlvtx.sh` points at `$Y/products/scn/...`.
   Traps from Polaris §1.7 that still apply: `--cleanenv` (host `CC`/`CXX`, oneAPI
   `CPATH`/`LD_LIBRARY_PATH`), `WAF_NO_PREFORK=1`, `export -f setup`, spdlog
   pair, `mrb z` before rebuilding.
3. `build-wct-lwc.pbs` on a `debug`/`debug-scaling` node: WCT `wcb configure`
   + `install -j96`, all procedure §1 gates (19 libs, `__libc_single_threaded` 0,
   `NEEDED fmt` 0, RUNPATH spdlog v1_14_1, RPATH strip, clean `ldd`), then
   larwirecell via `mrb newDev -v v10_14_02_02 -q e26:prof` + `mrb b -j96`
   against `$Y/opt`; deploy to `$Y/opt/larwirecell/v10_01_28/slf7.x86_64.e26.prof/`.
   Gate: `WireCell_INCLUDE_DIR` = opt, `cvmfs_wirecell_refs` = 0 (now
   "scisoft-tree wirecell refs" = 0).
4. Operating-point resync + config gate (`resync-operating-point-*.sh`): 0 differences.
5. Cross-check (optional): `cmp`/`ldd` the Aurora `opt/` against the Polaris
   `opt/`, and run one event with each.

**Phase A3 (validation).** (a) 19 nc-sideband data events with `smoke.pbs`
(`FCL=wcls-img-clus-matching-xin-data.fcl`), `compare-to-fnal.sh` against the
FNAL run **and** against Polaris `ncsb-data-nuebdt-20260916-0446` -> exact 19/19
both ways; Bee set uploaded from the UAN and linked in the issue. (b) 50-100
Gen2 reco1 MC events (MC fcl) run per-event **and** per-file (`-n -1`) on
Aurora -> byte-identical `tracking-pr.root` per RSE (gates Q6), and compared
with the same events run on Polaris if that one file is moved to Eagle.

**Phase A4 (scaling).** (a) 1 node (`debug-scaling`, exclusive) x 100 `lar` per
file: events/node-hour, RSS, start-up storm (Q9), `/tmp` use. (b) `debug-scaling`
8 -> 64 -> 128 nodes for 1 h with the per-file task queue: Lustre metadata
behaviour at 800 / 6,400 / 12,800 concurrent starts, staggering, queue waits.
(c) one `capacity` job (16 nodes, several hours) as the long-running alternative.

**Phase A5 (production).** Manifest from the `.json` metadata (file, events,
run/subrun, size); per-file task queue with completion markers; outputs tarred
per input file (one tar of `mabc.zip`, `trash`, `nugraph.h5`, `tracking-pr.root`
per event inside) written to `$Y/production/<sample>/NNNNNN/`; provenance
(commits, fcl/jsonnet SHA, compiled config); results back via Globus.
Budget ~125-250 node-hours on 17257.

---

## 4. Sizing on Aurora

| | per event 30 s | 45 s | 60 s |
|---|---|---|---|
| events per node-hour (100 procs) | 12,000 | 8,000 | 6,000 |
| node-hours for 1M events | 83 | 125 | 167 |
| 1M events on 128 `debug-scaling` nodes | 39 min | 59 min | 78 min (2 jobs) |
| 1M events on 16 `capacity` nodes | 5.2 h | 7.8 h | 10.4 h |

Memory: 100 x 2.2 GB = 220 GB of ~1 TB. Inputs: 28.4 MB/event -> **~28 TB for
1M events**, read in place from twester's tree (no copy). Outputs ~7 MB/event ->
~7 TB, ~75k tar files. Per-core speed of SPR vs Milan is unknown: measure in A4(a).

## 5. Risks

- **R1 (was Eagle-on-compute) -> no containers on the UAN**: every SL7 step is
  a job; interactive debugging = `qsub -I -q debug-scaling -l select=1`.
- **R2 cvmfsexec impossible on compute nodes** -> A' is already the plan; the
  only casualties are the convenience bootstrap and the in-job fetch of `scn`
  and the dev image (use Polaris -> Globus instead).
- **R3 start-up storm on Lustre** (Q9) -> stagger, per-file, node-local copy,
  squashfs overlay; measured in A4 before A5.
- **R4 `debug` is non-exclusive** (doc) -> use `debug-scaling` (accepts 1 node)
  for anything timed.
- **R5 allocation**: 17257 intent unconfirmed; project net balance +151 h with
  overdrawn restricted subs -> ask twester; `debug2` is ours regardless.
- **R6 FP differences on Intel** -> the exact 19/19 gate tells us immediately;
  known acceptable residual classes are in the procedure doc §7.
- **R7 project quota at 95 % and 223 M files** -> tar outputs, no per-event dirs
  left on Flare, clean `production-prep/` after validation.
- **R8 monthly renewal** -> all pots end 2026-10-01 and renew (user); keep the
  scaling test before month end so the production run is not blocked by a
  renewal hiccup.

## 6. Decisions needed from the user

1. Sample for the 1M events: prod1 `reco1/000000-000075` (1.006 M events), or
   spread over prod1/2/3? Anything that distinguishes the three productions?
2. OK to use suballocation **17257** for scaling + production, and to ask
   twester about it, the quota and an output location?
3. Per-file granularity for production (recommended), per-event for validation.
4. Recipe A' as the primary recipe (recommended); Recipe B only if the probe
   shows FUSE works and only for bootstrap.
5. Who moves the 4 non-git items Eagle/FNAL -> Flare (Globus), and when.

## 7. Status (2026-09-16, end of day 1)

| step | state |
|---|---|
| A0 login-node facts, repos on Flare, cvmfsexec dist, `gh` | done |
| A1 probe (`debug`, 2 runs) | done: userns/FUSE/proxy/cvmfsexec all work on compute; `slf7.sif` runs unflagged; bare tree runs `lar` + eventdump |
| A2 Recipe A' overlay (`$Y/products`: spdlog v1_14_1, fmt v11_0_2, srproxy v00.44, scn v01_00_00; `$Y/images/fnal-dev-sl7.sif`) | done |
| A2 WCT `polaris-build-fixes` 9195180d -> `$Y/opt` | **built, all §1 gates pass** (job 8832376, 6.6 min) |
| A2 larwirecell `dev-v10_14_02_02` a02a1a4 | **built + deployed** (11 libs, 20 fcl; job 8832409) |
| operating-point gate | **0 differences** |
| A3 MC smoke (Gen2 reco1, 9 events) | **9/9 pass**, 20-79 s/event, RSS 1.45-1.88 GB, DL vertex on |
| A3 19-event data validation vs FNAL + Polaris | **blocked**: nc-sideband file, FNAL/Polaris reference runs, `XGB_nue_seed2_0923.xml` not yet on Flare (Globus) |
| A4 scaling, A5 production | not started |

Traps found on day 1 (all fixed in `issues/29-aurora-production/scripts/`): piped `module load` loses PATH; a UPS db needs `.upsfiles`; `unsetup wirecell` without `-j` drops root/python; fork clone has no tags for `git describe`; `MRB_PROJECT=larsoft` for `mrb newDev`; `clus.jsonnet` hard-codes a `/cvmfs/sbnd...` path -> bind the Flare tree there.
