# SBND img-clus-match-pr production on Polaris (ALCF): plan v1

Goal: run the WCT/larwirecell 1-step `img-clus-match-pr` chain on ~1M SBND
reco1 events (artROOT with `recob::Wire` + `sim::SimEnergyDeposit`) on
**Polaris** with our **local** wire-cell-toolkit (`master`) and larwirecell
(`dev-v10_14_02_02`) builds, in under a week of wall time.

Written 2026-09-10 from a survey of the machine (login node + two 1-node
`debug` probe jobs), the ALCF docs, and two colleagues' ALCF work areas
(abhat, snehadri). Everything marked **measured** was observed on this
machine today; everything marked **open** is a question we still have to
answer. Companion procedure for the FNAL side: `sbnd-1step-build-run-validate.md`.

Local copies: WCT `/lus/eagle/projects/neutrinoGPU/yuhw/wire-cell-toolkit`
(master, `67e2eba7`), larwirecell `/lus/eagle/projects/neutrinoGPU/yuhw/larwirecell`
(`dev-v10_14_02_02`, `a02a1a4`), probe scripts `/lus/eagle/projects/neutrinoGPU/yuhw/polaris-probe/`.

---

## 1. Answers to the first-round questions

### 1.1 Can we use the SL7 container like on sbndgpvm/sbndbuild?

**Yes, two ways, both measured today.** Polaris has no `apptainer` on `PATH`;
on compute nodes `module use /soft/modulefiles; module load spack-pe-base`
then `module spider apptainer` lists `apptainer/{1.2.2,1.3.2,1.4.1}` (a bare
`module load apptainer` failed in probe 1; load a version explicitly). The
spack binaries also run directly; none is setuid, so a mode flag is needed:

| binary | where it runs | mode |
|---|---|---|
| `/soft/spack/base/0.8.1/install/linux-sles15-x86_64/gcc-12.3.0/apptainer-1.3.2-o4dxrioaegfbzftm2uzazrkn6tprrang/bin/apptainer` | login node **measured** (sandbox dirs only) | `--userns` (`--fakeroot` unavailable on login: no `/etc/subuid`). On compute it **fails on `.sif`**: `exec: "unsquashfs": executable file not found` (probe 3) |
| `/soft/spack/testing/0.8.1/apptainer/install/linux-sles15-zen3/gcc-12.3.0/apptainer-1.3.6-7czfylw7oeizgfklnroabhww7kygmtjt/bin/apptainer` | login **measured** (`--userns`); compute **measured** (`--userns` and `--fakeroot`, probes 2-3) | without a flag: `starter-suid doesn't have setuid bit set`. **Use this one.** |

Also `unset LD_PRELOAD` in job scripts: PBS injects the XALT preload and every
SL7 process logs `ERROR: ld.so: object '/soft/xalt/.../libxalt_init.so' ... cannot be preloaded`.

Two container recipes are available:

- **Recipe A (Avinay/twester): `slf7.sif` + LArSoft squashfs overlays, no CVMFS.**
  Image `/lus/grand/projects/neutrinoGPU/software/containers/slf7.sif` (300 MB,
  bare SL7.9) with read-only overlays
  `/lus/eagle/projects/neutrinoGPU/larsoft_hpc/images/larsoft-v10_14_02.squashfs`
  (8.5 GB) + `sbnd-v10_14_02_0{4,5}_delta.squashfs` (4.3 GB), env from
  `/lus/eagle/projects/neutrinoGPU/larsoft_hpc/envs/sbndcode-v10_14_02_0{4,5}.env`.
  Products appear under `/lus/flare/projects/neutrinoGPU/scisoft/...` inside the
  container (path mirrored from Aurora; never bind `/lus/flare` on the host).
  Avinay ran this on Polaris `debug` nodes in Aug 2026 and on Sophia through
  Sep 2026 with `--fakeroot ... :ro`. **Measured today on a Polaris compute
  node (probes 2-3):** `apptainer exec --userns ... slf7.sif` + sourcing the
  env file + `lar --version` = `art 3.14.04` in 2-4 s wall, and
  `lar -c eventdump.fcl -s <reco1> -n 1` completed (`Art has completed ...
  status 0`, `sim::SimEnergyDeposit` collections listed) in **10.7 s wall
  including container start** on Avinay's reco1 file. Caveat for us: this stack carries
  `spdlog v1_9_2` (bundled fmt) and `wirecell v0_32_1`, i.e. exactly the
  ambient products the sbndbuild procedure had to override; a new delta with
  `spdlog v1_14_1` + `fmt v11_0_2` would have to be built with twester's
  `larsoft_hpc/scripts/create_layered_stack.sh`.
- **Recipe B (snehadri, extended): cvmfsexec + the FNAL SL7 image from CVMFS.**
  `cvmfsexec sbnd.opensciencegrid.org sbn.opensciencegrid.org sbn.osgstorage.org
  larsoft.opensciencegrid.org fermilab.opensciencegrid.org
  singularity.opensciencegrid.org -- apptainer exec --userns -B /cvmfs -B /lus/eagle
  /cvmfs/singularity.opensciencegrid.org/fermilab/fnal-wn-sl7:latest bash -lc '...'`.
  This is the **same environment as sbndgpvm** (same UPS products incl.
  `spdlog v1_14_1`/`fmt v11_0_2`, same image), so the sbndbuild build recipe
  and all its gates transfer unchanged. **Measured on a compute node (probe 4,
  cold node-local cache, through the proxy):** rsync of the cvmfsexec template
  to `/local/scratch` 1 s; mount + `setup_sbnd.sh` + `setup sbndcode
  v10_14_02_0602 -q e26:prof` + `lar --version` + `lar -c eventdump.fcl -n 1`
  on the reco1 file = **65 s total**, of which the cold event dump was 21 s;
  warm `lar --version` 0.03 s, warm event dump 2.2 s; **16 concurrent** warm
  event dumps 3.7 s wall, all rc=0; CVMFS cache after all that: 916 MB.
  **Measured on the login node** (`cvmfsexec-login`, cold): 52 s end to end,
  `setup sbndcode` 34 s, `lar --version` 3 s; that stack reports
  `wirecell v0_32_1`, `larwirecell v10_01_26_01`, `spdlog v1_9_2` (the ambient
  products we override, as at FNAL).

**Recommendation: start with Recipe B** (zero new images, identical to the
validated FNAL environment); keep Recipe A as the fallback if CVMFS-over-proxy
does not scale (section 4, risk R1).

### 1.2 Is CVMFS reachable from Polaris?

There is **no `/cvmfs` mount** anywhere (login or compute), and ALCF does not
run a CVMFS squid. But unprivileged **cvmfsexec works**:

- login node: user namespaces + `/dev/fuse` + `fusermount3` present;
  `./makedist osg` took 13 s; mount + `ls` of `sbndcode v10_14_02_06`,
  `spdlog v1_14_1` in ~7 s (**measured**), stratum-1 reached DIRECT.
- compute node (probe 1, `x3016c0s1b0n0`): **no direct network at all**
  (`Network is unreachable` to GitHub, stratum-1, and `fndcadoor:1094`); with
  `CVMFS_HTTP_PROXY="http://proxy.alcf.anl.gov:3128;DIRECT"` all four repos
  mounted and listed correctly (**measured**). snehadri's Sophia attempts
  failed only because they never set the proxy.
- **Trap (hit today): the cache, lock files and logs live *inside* `dist/`
  (`dist/var/lib/cvmfs/`, `log/`), and the `CVMFS_CACHE_BASE` env var is
  ignored; only `dist/etc/cvmfs/default.local` counts.** A login-node test and
  a compute job sharing the Eagle `dist/` crashed each other within a minute
  (`crash cleanup handler unmounted stalled ...`, `another process holds
  ./lock_cachemgr`, `Stale file handle`) and left orphan `cvmfs2` processes.
  Rule: **one `dist/` copy per cvmfsexec instance, cache on node-local disk.**
  Layout now: `/lus/eagle/projects/neutrinoGPU/yuhw/cvmfsexec` = template
  (upstream 4.52, `default.local` with proxy + `CVMFS_CACHE_BASE=/local/scratch/cvmfs-cache`,
  never run directly); `.../cvmfsexec-login` = login-node copy
  (`CVMFS_CACHE_BASE=/home/yuhw/cvmfs-cache`, disk-backed because `/tmp` is
  tmpfs and would be charged to the 8 GiB cgroup); jobs `rsync` the template
  (137 MB) to `/local/scratch/cvmfsexec` at start (probe 4). Node-local
  storage **measured**: `/local/scratch` 2.9 TB NVMe RAID0, `/tmp` and
  `/dev/shm` 252 GB tmpfs. Do **not** mount `sbn.osgstorage.org` unless
  needed; it stalled for 15 min on the login node.

**Measured (probe 4):** on one node the cold cost is small (65 s to a first
event dump, 21 s for the cold `lar` start, 916 MB cached; 16 concurrent warm
starts in 3.7 s). **Open (R1):** the same with our full plugin set (WCT +
larwirecell + torch) and at 10-24 nodes starting simultaneously through one
proxy; measure in phase 3 and stagger start-ups if needed.

### 1.3 Are official SBND productions reachable from Polaris?

**Not directly.** No `/pnfs`, no `ifdh`, `xrdcp`, `voms-proxy-init`,
`htgettoken` or `globus` on the login node; compute nodes have no route to
Fermilab (proxy returns `403 Forbidden` for `fndca1.fnal.gov:2880`). Data
must be **staged to Eagle first**, from the login node or via Globus:

- **Proven (snehadri, Jul 2026):** `htgettoken -a htvaultprod.fnal.gov -i sbnd`
  (needs a conda env: `module load conda; pip install htgettoken`), then
  `curl -H "Authorization: Bearer $TOK" https://fndcadoor.fnal.gov:2880/<pnfs path>`
  from the login node. The xrootd door `:1094` is GSI-only. Official MCP2025B
  reco1 files were ~160-370 MB for 10-24 events, i.e. **~15 MB/event**.
- **Standard ALCF path:** Globus, ALCF collection `alcf#dtn_eagle`, path
  `/eagle/neutrinoGPU/...`. **Open (Q2):** which Fermilab collection exposes
  SBND dCache (`/pnfs/sbnd/{persistent,scratch}`), and can the SBND production
  team stage the dataset to it. SBND used Globus with FNAL+ANL certificates for
  the Theta campaign (sbndcode wiki "SBND at Theta").
- Existing SBND artROOT on Eagle: only Avinay's two reference files (3.9 GB
  each, ~50 events, reco1-level `simtpc2d:dnnsp`); twester's `sbnd_*larcvreco1*`
  trees are LArCV, not artROOT. Nothing usable for 1M events is here yet.

Volume: 1M events x ~15 MB = **~15 TB input** (range 10-25 TB depending on the
dataset). Eagle project quota is 2.72 PB used of 3.0 PB (filesystem 91 %
full); we need the PI's OK for **~20-40 TB** including outputs (**Q3**).

### 1.4 Job submission system; can it run local WCT/larwirecell builds?

**PBS Pro** (`qsub/qstat/pbsnodes`, version 2026.1). Charging is per node-hour
(whole node, 32 cores/64 threads, 512 GB, 4 A100; GPUs idle for us).
**Measured queue limits** (`qstat -Qf`):

| queue | nodes | walltime | notes |
|---|---|---|---|
| `debug` | 1-2 | 5 min - 1 h | 1 running job per user; 24 nodes total |
| `debug-scaling` | 1-10 | 5 min - 1 h | 1 job per user queued/running |
| `prod` (routing) -> `small` | 10-24 | <= 3 h | 10 running/accruing + 100 queued per **project** |
| -> `medium` | 25-99 | <= 6 h | same |
| -> `large` | 100-496 | <= 24 h | same |
| `preemptable` | 1-10 | <= 72 h | may be killed by `demand`; use `-r y` |
| `backfill-*` | as prod | as prod | opportunistic |

Required flags: `-A neutrinoGPU::<suballocation>` (**submanagement is enabled:
a bare `-A neutrinoGPU` is rejected**, measured), `-l select=N`,
`-l walltime=`, `-l filesystems=home:eagle[:grand]`, `-q`. Allocation state
today (`sbank-detail-allocations`):

| suballocation | balance (node-h) | ends | access |
|---|---|---|---|
| 17256 (subname None, unrestricted) | **4,483** | **2026-10-01** | all members |
| 14453 `debug` (unrestricted) | 232 | 2026-10-01 | used for the probes |
| others (`SPINE_*`, `ICARUS*`, ...) | 0 or negative | 2026-10-01 | restricted |

Running local builds from PBS is straightforward: the job script mounts
cvmfsexec once per node and `apptainer exec`s the SL7 image with `/lus/eagle`
bound in; our `opt/` on Eagle is prepended to `LD_LIBRARY_PATH`,
`CET_PLUGIN_PATH`, `FHICL_FILE_PATH`, `WIRECELL_PATH` exactly as
`setup-local-opt.sh` does on sbndbuild. No Kerberos, no ticket renewal (the
sbndbuild §5 trap disappears). What changes: no `wait -n` issues (host bash is
5.x, container bash is 4.2 as before), and the node has no network, so
nothing may fetch at run time (Bee upload, `dl_weights` download, jsonnet
imports from URLs).

### 1.5 Interactive tests on polaris-login-01

**Hard cgroup limits per user, measured** (`/sys/fs/cgroup/users/yuhw`):
**8 CPUs (`cpu.max 800000/100000`), 8 GiB memory, 256 pids**. The node itself
is 128 cores / 512 GB, load ~60 with 34 users. No walltime limit is enforced,
but ALCF policy reserves login nodes for editing, building and job control.
Consequences:

- a `-j8` WCT build inside the SL7 container fits (expect ~30-45 min instead of
  10-15 on sbndbuild03's 16 threads);
- at most **2-3 concurrent `lar` processes** (2.1 GB RSS each, measured at FNAL;
  1.8 GB measured by Avinay on Sophia) before the 8 GiB cgroup OOM-kills them;
- for anything bigger use an interactive debug job:
  `qsub -I -A neutrinoGPU::debug -q debug -l select=1 -l walltime=01:00:00 -l filesystems=home:eagle`
  gives a full node for an hour (1 such job at a time).

### 1.6 Other critical questions (added)

- **Q1 dataset.** Exact SAM/metacat definition(s), event and file counts,
  per-event size, and a check that the files carry `sim::SimEnergyDeposit`
  (Avinay found the standard `detsim_drops`/`reco1_drops` remove
  `ionandscint:priorSCE`) and the `recob::Wire` tags our fcl expects
  (`simtpc2d`). Which "Gen2" production: MC or data? Data needs the
  `FrameShift` product added first (sbndbuild §5).
- **Q4 allocation timing.** 4,483 node-hours is ample (section 2) but the
  pot **expires 2026-10-01**, three weeks from now. Either the production
  runs by Sept 30 or we confirm the follow-on allocation with the PI.
- **Q5 queue wait.** 550/560 nodes were job-exclusive at survey time; the
  `small` queue had 17 queued jobs. Wall time is dominated by waiting, not
  computing. Measure with the phase-3 job before promising a date.
- **Q6 outputs.** What to keep per event (tracking-pr.root, Bee zips,
  nugraph.h5, ART output?) and their sizes; Avinay's 48-event ART output was
  1.8 GB (37 MB/event), which would double the storage need. Where do results
  go afterwards (back to FNAL via Globus?).
- **Q7 DL vertex dependency.** The 1-step's DL vertex (`dl_weights`, SCN)
  needs libtorch and a weights file; confirm both are available in the SL7 +
  CVMFS environment and that the weights are on Eagle (no network on compute).
- **Q8 file granularity.** At 10-24 events/file, 1M events is 50k-100k input
  files and as many output sets. Needs a manifest-driven task queue with
  idempotent per-file completion markers, outputs grouped by run/subrun, and
  per-node tarring to keep Lustre file counts sane.
- **Q9 validation.** Repeat the sbndbuild gates (operating point resync,
  `prod_prjob.json` byte-identical, RPATH strip) and a 300-event cross-machine
  comparison against the FNAL reference; expected residuals are the
  `T_rec_charge:{q,reduced_chi2}` ~1e-12 class only.

---

## 2. Sizing

Per-event cost of the chain, single-threaded `lar`:

| source | stage | time/event | RSS |
|---|---|---|---|
| Avinay, Sophia (AMD Rome), 48 events | sig2img+clus+match+pr | 29 s avg (10.6-77 s) | 1.8 GB |
| sbndbuild03 campaign (FNAL) | same 1-step | - | 2.1 GB peak |

Assume **30-60 s/event, 2.1 GB** on Polaris (Milan 2.8 GHz). Per node, 32
processes (one per core; try 48-64 with SMT, memory allows 64 x 2.1 GB):

| | 30 s/event | 60 s/event |
|---|---|---|
| events per node-hour | ~3,800 | ~1,900 |
| node-hours for 1M events | ~260 | ~530 |
| one `small` job (24 nodes x 3 h) | ~274k events | ~137k events |
| jobs for 1M events | 4 | 8 |

Budget with 2x contingency: **500-1,000 node-hours**, well inside 4,483.
Compute wall time is ~12-24 h of node time; the schedule is set by queue
waits and by the input transfer (15 TB at 100-500 MB/s = 8-40 h).

---

## 3. Phased plan

**Phase 0 (now): decisions.** Answer Q1-Q4 with the user/SBND production;
open the tracking issue; pin the WCT commit and larwirecell branch.

**Phase 1: environment + build on Polaris (login node, Recipe B).**
1. Wrapper `in-polaris-sl7.sh <cmd>` = cvmfsexec (6 repos, proxy-aware) ->
   `apptainer exec --userns -B /cvmfs -B /lus/eagle -B /tmp fnal-wn-sl7` ->
   `setup-local-opt.sh` equivalent. Mirrors `in-gpvm-sl7.sh`.
2. Build WCT `master` with `configure-wct.sh` (spdlog v1_14_1 + fmt v11_0_2 from
   CVMFS, `-DSPDLOG_FMT_EXTERNAL`), `-j8`; apply all §1 gates incl. the RPATH
   strip (§1a) and `miniz.h`.
3. Build larwirecell `dev-v10_14_02_02` against it (cmake or MRB as in §2 of the
   procedure, `WIRECELL_FQ_DIR` set); hand-deploy libs.
4. Resync the PR operating point (§3) and run the config gates (§4).
5. Run 1 event on the login node (1 process, under the 8 GiB cgroup) on
   Avinay's reference file; check `tracking-pr.root` has 8 trees.

**Phase 2: correctness.** 300 events in a `debug` job; compare with the
FNAL reference set with `deep_compare.py`/branch census (Q9). Also verify
Recipe A as a fallback if time permits.

**Phase 3: scaling.** (a) 1 node x 32 and x 64 `lar` from a node-local
cvmfs cache: measure cold start, events/node-hour, RSS, failures. (b) One
`small` job, 10 nodes x 3 h (~30-100k events): measure proxy/CVMFS behaviour
and queue wait. Decide packing and job size; write the task-queue driver
(manifest -> per-node `xargs -P`, completion markers, `timeout -k`, retry list).

**Phase 4: staging.** Transfer the dataset to
`/lus/eagle/projects/neutrinoGPU/yuhw/sbnd-prod/<dataset>/` (Globus or token
WebDAV, parallel streams), verify checksums against the SAM metadata, build the
manifest (file, nevents, run/subrun).

**Phase 5: production.** Submit 4-10 `prod` jobs (10 running per project
max), monitor with `qstat` + the summary CSV, re-run failures, tar outputs
per run, record provenance (WCT/larwirecell commits, fcl/jsonnet SHA,
`prod_prjob.json`).

**Phase 6: hand-off.** Outputs back to FNAL or consumers on Eagle; update
this doc with measured numbers; delete staged inputs.

---

## 4. Risks

- **R1 CVMFS through one HTTP proxy at scale.** Mitigations: node-local NVMe
  cache, one cvmfsexec per node, stagger start-ups, `CVMFS_TIMEOUT` fail-fast;
  fallback = Recipe A squashfs with a rebuilt `sbnd-v10_14_02_0x` delta that
  includes `spdlog v1_14_1`/`fmt v11_0_2` (twester's tooling), or a
  `cvmfs_shrinkwrap` of just the products we load.
- **R2 Allocation expiry 2026-10-01** (Q4).
- **R3 Data transfer** rate/route not yet demonstrated at TB scale (Q2).
- **R4 Eagle space** (Q3) and Lustre small-file load (Q8).
- **R5 Silent config drift**: same trap as at FNAL; the `git checkout`-changes-
  `WIRECELL_PATH` gate and the operating-point resync apply unchanged.
- **R6 Walltime kills** at 3 h/6 h: per-file granularity + `-r y` + idempotent
  restarts; never a single multi-hour `lar` over many files.

---

## 5. Probe record (2026-09-10)

Probe 1 (`7602957`, `debug`, node `x3016c0s1b0n0`, 12 s): SLES 15 SP7,
kernel 6.4, 64 threads/32 cores, 503 GB, 4x A100-40GB, `/local/scratch`
2.9 TB, `/tmp` and `/dev/shm` 252 GB tmpfs, no cgroup limits, direct network
unreachable, proxy `http://proxy.alcf.anl.gov:3128` works for GitHub and the
CVMFS stratum-1, cvmfsexec mounted sbnd/larsoft/fermilab/singularity repos,
`module load apptainer` failed, dCache `:2880` via proxy -> 403.

Probe 2 (`7602966`/`7602969`): `module spider apptainer` lists 1.2.2-1.4.1;
Recipe A `lar --version` OK in 2-4 s with `--fakeroot`; Recipe B not reached
(script bug: apptainer launched without `--userns`; then the shared `dist/`
collision with a login-node test hung it).

Probe 3 (`7603037`, `x3016c0s13b0n0`): apptainer 1.3.2 (`base`) fails on
`.sif` (no `unsquashfs`); 1.3.6 (`testing`) works with `--userns` and
`--fakeroot`. Recipe A event dump of the reco1 file: rc=0, 10.7 s wall,
`sim::SimEnergyDeposit` present. Recipe B hung on the shared `dist/` (killed).

Probe 4 (`7603068`, `x3010c0s13b1n0`, 71 s): private `dist/` on
`/local/scratch`; Recipe B cold: 65 s end to end, cold event dump 21 s, warm
2.2 s, 16 concurrent warm dumps 3.7 s, cache 916 MB. **Both recipes work on
Polaris compute nodes.**

Login node (`cvmfsexec-login`): Recipe B cold 52 s; `setup sbndcode` 34 s.

Scripts: `/lus/eagle/projects/neutrinoGPU/yuhw/polaris-probe/probe{,2,3,4}.pbs`
(copied to `docs/polaris-probes/` with the two `default.local` files).
