# SBND img-clus-match-pr production on Aurora (ALCF): setup + validation plan v1

Goal: reproduce the Polaris workflow (`polaris-img-clus-match-pr-production-plan.md`,
issue 27: local WCT `polaris-build-fixes` = master + 2 warning fixes, larwirecell
`dev-v10_14_02_02`, SL7 container, 1-step `img-clus-match-pr`) on **Aurora**, validate
it bit-for-bit against the FNAL and Polaris runs, and use Aurora's ~100 cores/node
and the SBND official Gen2 reco1 artROOT already on `/lus/flare` for the large
scaling tests and the 1M-event production.

Written 2026-09-16 from the ALCF Aurora docs, `sbank`, and the colleagues'
Aurora-oriented tooling visible from Polaris; nothing has been run on Aurora
yet. **measured** = observed; **doc** = from docs.alcf.anl.gov; **open** = to probe.
Tracking issue: https://github.com/HaiwangYu/wire-cell-toolkit-ai-helper/issues/29

---

## 1. What we know

### 1.1 Machine (doc)

| | Aurora | Polaris (for contrast) |
|---|---|---|
| nodes | 10,624 | 560 |
| CPU | 2 x Intel Xeon Max (Sapphire Rapids), 52 cores/socket, 2 HT -> **104 cores / 208 threads**; cores 0 and 52 reserved for system services since 2025-03-31 -> **102 usable cores** | 1 x AMD Milan 7543P, 32 cores / 64 threads |
| memory | 512 GB DDR5 per socket (1 TB) + 64 GB HBM per socket | 512 GB |
| GPUs | 6 x Intel PVC (idle for us) | 4 x A100 (idle for us) |
| OS | SLES 15 (HPE Cray EX) | SLES 15 SP7 |
| scheduler | PBS Pro; `-A neutrinoGPU::<suballocation>` | same |
| filesystems on nodes | `/lus/flare` (91 PB Lustre, project dirs `/lus/flare/projects/neutrinoGPU`, **default quota 1 TB**), `/home` = Gecko (50 GB), DAOS; `-l filesystems=` accepts only `flare`, `home`, `daos_user`, `daos_perf` -> **Eagle is probably not mounted on compute nodes** (open: login nodes) | `/lus/eagle`, `/lus/grand`, `/home` |
| node-local | open (Polaris has 2.9 TB NVMe `/local/scratch`) | 2.9 TB NVMe |
| network | compute: `proxy.alcf.anl.gov:3128` only; login nodes (UANs): direct, "the proxy will not function" there | same pattern |
| containers | `module load apptainer` on compute nodes, `--fakeroot` supported | spack binaries, `--userns` |
| CVMFS | none (same as Polaris); cvmfsexec needs `/dev/fuse` + user namespaces: **open** | cvmfsexec works |

### 1.2 Queues (doc, docs.alcf.anl.gov/aurora/running-jobs-aurora)

| queue | nodes | walltime | limits |
|---|---|---|---|
| `debug` | 1-2 | <= 1 h | 64 nodes total, **non-exclusive** (shared nodes!), 1 job/user |
| `debug-scaling` | 2-256 | <= 1 h | 1 job/user |
| `prod` -> `small` | 256-1,024 | <= 12 h | 10 running + 100 queued per project |
| `prod` -> `medium` / `large` | 1,025-1,999 / 2,000+ | <= 18 h / 24 h | same |
| `capacity` | 1-16 | <= 7 days | 512 nodes across all jobs; 5 queued, 2 running per user |

Implication: the 10-24-node `small` queue we planned on Polaris does not exist
on Aurora. The natural homes for our work are `debug-scaling` (up to 256
nodes for an hour: ~256 x 100 procs = 25,600 concurrent `lar`) and `capacity`
(1-16 nodes for days). 1M events at ~45 s/event on 100 procs/node needs only
**~125 node-hours** -- e.g. one 128-node `debug-scaling` hour, or 16 `capacity`
nodes for ~8 h.

### 1.3 Allocation (measured, `sbank-detail-allocations -p neutrinoGPU -r aurora`, 2026-09-16)

| suballocation | balance (node-h) | access |
|---|---|---|
| 14186 (subname None, the main pot) | **6,907** | **restricted to twester** -- ask to be added, or |
| 14454 `debug2` | **472** | unrestricted -> our bootstrap pot (`-A neutrinoGPU::debug2`) |
| others (`SBNDDetVarReprocess_Fall2025` 1,228, `SBNDBulkyMC2026` 464, ...) | | restricted to twester |

All end 2026-10-01 and renew monthly (user).

### 1.4 Colleagues' Aurora infrastructure (measured on Eagle)

twester's `larsoft_hpc` tooling was designed for Aurora ("Deployment on Aurora"):
the pre-computed env files reference `/lus/flare/projects/neutrinoGPU/scisoft/larsoft/<pkg>/<ver>/slf7.x86_64.e26.prof`
(627 such paths in `sbndcode-v10_14_02_05.env`), i.e. on Aurora the **UPS
product tree lives directly on Flare** (the squashfs images are the Polaris/Sophia
transport of the same tree). The SL7 image is `slf7.sif` (300 MB, bare SL7.9,
no `-devel` headers). twester has been running SBND production on Aurora
(`SBND_Gen1_PAC_Spring2026`, `SBNDDetVarReprocess_Fall2025`, `SBNDBulkyMC2026`)
-- **the person to ask** about Flare paths, quotas, queue behaviour and the
official Gen2 reco1 location. That tree carries `spdlog v1_9_2` and
`wirecell v0_32_1` (needs overriding, as everywhere), and `sbndcode v10_14_02_04/05`
(our pairing is `v10_14_02_03` / larsoft `v10_14_02_02`).

### 1.5 What transfers from Polaris unchanged

- **Binaries.** WCT was built with generic flags (`-O3 -g -fno-omit-frame-pointer`,
  no `-march`), inside SL7, against CVMFS e26 products: x86-64 portable. The
  Polaris `opt/` + larwirecell libs can be copied to Flare and run under the
  same SL7 image + the same UPS products. We will still rebuild on Aurora for
  provenance (8 min on a node) and cross-check the two.
- **Scripts.** `issues/27-polaris-production/scripts/*` need one change: the
  hard-coded `Y=/lus/eagle/projects/neutrinoGPU/yuhw` becomes an env var
  (`Y=/lus/flare/projects/neutrinoGPU/yuhw`), plus the apptainer path (`module
  load apptainer` on Aurora) and `-l filesystems=flare:home`.
- **Gates and reference data.** The 19-event nc-sideband file (100 MB) and the
  FNAL reference run (`r3-ncpi0-lynn-2026-09-15`) give an **exact 19/19** target;
  `compare-to-fnal.sh` is the gate. Two independent CPU vendors already agree
  bit-for-bit (FNAL sbndgpvm vs Polaris AMD), so Intel SPR is expected to as well.

---

## 2. Open questions (probe job + login-node checks; the first deliverable)

- **Q1 login nodes (UANs).** Per-user cgroup limits (Polaris: 8 CPU / 8 GiB)?
  Is `/lus/eagle` mounted there (the user reports yes) and read-write? Can we
  `cp` Eagle -> Flare directly (the cheapest transfer), or must we use Globus
  (`alcf#dtn_eagle` -> `alcf#dtn_flare`)?
- **Q2 compute nodes.** `/lus/eagle` visible? node-local scratch (path, size)?
  `/dev/fuse` + `unshare -U` (cvmfsexec)? `module load apptainer` version, does
  `--userns`/`--fakeroot` work, does `.sif` exec need `unsquashfs`? Proxy
  reachability (CVMFS stratum-1, GitHub)? `debug` being non-exclusive: are
  cores/memory shared with other jobs (affects timing)?
- **Q3 software delivery at scale.** Recipe B (cvmfsexec) is the fastest
  bootstrap but funnels 25,000 processes' cold starts through one HTTP proxy at
  256 nodes. Recipe A' = a **Flare-resident UPS tree** (our exact product set,
  incl. `spdlog v1_14_1`, `fmt v11_0_2`, `patchelf`, `cmake`, `sbndcode v10_14_02_03`)
  needs no network at run time. Which to use for production? (Recommendation
  in section 3.)
- **Q4 inputs.** Path, dataset name, file count, events/file and total size of
  the official Gen2 reco1 on Flare; MC or data (data needs `FrameShift`); are
  the products (`recob::Wire` tags, `OpFlash` labels, `SimEnergyDeposit`) what
  the fcl expects? Who owns the directory (read permission)?
- **Q5 Flare quota.** Default 1 TB; our software + wire-cell-data + MRB area is
  ~5 GB, outputs are ~7 MB/event (7 TB for 1M events if everything is kept).
  Request a quota under the project, or write under an existing project area
  (twester's).
- **Q6 job granularity.** On Polaris we ran 1 `lar` per event (startup ~20 s +
  62 s first torch import per process). At 100 procs/node the per-process
  start-up is a large fraction of a 45 s event: consider **one `lar` per input
  file** (10-24 events, `-n -1`) with per-event RSE bookkeeping from `Trun`
  (Xin's group mode was gated byte-identical to per-event in sbnd_xin doc 109).
  Decide before the scaling test.
- **Q7 queue behaviour.** Measured wait for `debug`, `debug-scaling` at 8 / 64 /
  256 nodes, and `capacity`. (Polaris `debug`: 3-87 s.)
- **Q8 allocation.** Use `debug2` (472 h) for everything up to the first
  production, and ask twester for access to 14186 (or a new suballocation) for
  the 1M run.

---

## 3. Plan

**Phase A0 (login node, minutes).** `hostname`, cgroup limits, `mount | grep lus`
(eagle? rw?), `lfs quota -p`/`-g` on `/lus/flare/projects/neutrinoGPU`, `module
avail apptainer`, `which fusermount3`, `ls -l /dev/fuse`, `unshare -U -r true`,
`sbank-detail-allocations -r aurora`, `qstat -Q`, `pbsnodes -a | grep state | sort | uniq -c`.
Create `/lus/flare/projects/neutrinoGPU/yuhw/` and copy from Eagle (if mounted)
or Globus: `cvmfsexec` template (137 MB), `wire-cell-data` (706 MB + the 199 MB
nue XGB file), `wcp-porting-validation`, `wire-cell-toolkit` (checkout),
`larwirecell`, the ai-helper repo, the 19-event nc-sideband file, and the FNAL
reference dir.

**Phase A1 (probe job, `debug`, 1 node, 30 min).** `issues/29-aurora-production/scripts/probe-aurora.pbs`:
node facts (cores, memory, local scratch, `/lus/eagle`?), proxy, `module load
apptainer` + modes, cvmfsexec through the proxy (private dist on node-local or
`/tmp`), Recipe A' check (`slf7.sif` + twester's Flare UPS tree: `setup sbndcode`,
`lar --version`), and a `lar -c eventdump.fcl -n 1` on the nc-sideband file.
Output answers Q2/Q3 mechanics.

**Phase A2 (software).** Decide B vs A' from A1:
- if cvmfsexec works on compute: port `in-polaris-sl7.sh` ->
  `in-aurora-sl7.sh` (Y on Flare, `module load apptainer`, `--userns` or
  `--fakeroot` as measured, proxy, uboone repo), build WCT + larwirecell with
  `build-wct-lwc.pbs` on an Aurora node (gates as on Polaris), deploy to
  `/lus/flare/.../yuhw/opt`;
- in parallel prepare **A'**: a Flare UPS tree with exactly our products.
  Two ways: (i) `pullProducts` (twester's parallel version in
  `larsoft_hpc/scripts`) of `sbnd-v10_14_02_03 e26 prof` + the extra manifest
  lines (`spdlog v1_14_1`, `fmt v11_0_2`, `patchelf 0.13.1`, `cmake v3_27_4`,
  the uboone `scn v01_00_00` venv) from scisoft.fnal.gov, run on a UAN
  (direct internet); or (ii) `rsync` the same product directories out of CVMFS
  via cvmfsexec on the **Polaris** login node into Eagle, then Eagle -> Flare.
  Gate: `ups depend sbndcode v10_14_02_03 -q e26:prof` resolves entirely inside
  the tree; `lar --version`; the operating-point gate compiles identically.
  Size: expect 15-25 GB.

**Phase A3 (validation).** Same 19 nc-sideband events with `smoke.pbs`
(`FCL=...-data.fcl`); `compare-to-fnal.sh` against the FNAL run **and** against
the Polaris run `ncsb-data-nuebdt-20260916-0446` -> exact 19/19 both ways, Bee
set uploaded and linked in the issue. Then 50-100 events of the Gen2 reco1
sample on Flare (MC fcl or data fcl as appropriate) compared with the same
events run on Polaris (copy that one input file to Eagle).

**Phase A4 (scaling).** (a) 1 node x 100 procs (memory 100 x 2.2 GB = 220 GB,
fine) -> events/node-hour, RSS, start-up cost, per-file vs per-event
granularity (Q6). (b) `debug-scaling` 8 nodes, then 64, then 256 nodes for 1 h:
CVMFS-proxy (B) or Flare-metadata (A') behaviour under 800 / 6,400 / 25,600
simultaneous `lar` start-ups, staggered if needed; measured queue waits (Q7).
(c) one `capacity` job (16 nodes, several hours) as the long-running alternative.

**Phase A5 (production).** Manifest of the Gen2 reco1 files on Flare;
per-file task queue with completion markers; outputs tarred per run/subrun on
Flare; provenance (commits, fcl/jsonnet SHA, compiled config); results back to
Eagle/FNAL via Globus. Node-hour budget ~125-250 for 1M events.

---

## 4. Sizing on Aurora

| | per event 30 s | 45 s | 60 s |
|---|---|---|---|
| events per node-hour (100 procs) | 12,000 | 8,000 | 6,000 |
| node-hours for 1M events | 83 | 125 | 167 |
| 1M events on 128 `debug-scaling` nodes | 39 min | 59 min | 78 min (2 jobs) |
| 1M events on 16 `capacity` nodes | 5.2 h | 7.8 h | 10.4 h |

Memory: 100 x 2.2 GB = 220 GB of ~1 TB. Inputs: ~15 MB/event -> ~15 TB for
1M events (already on Flare per the user); outputs ~7 MB/event -> ~7 TB (Q5).

## 5. Risks

- **R1 Eagle not on compute nodes** -> everything the job touches must be on
  Flare (or DAOS); the 1 TB default quota then bites immediately (Q5).
- **R2 cvmfsexec impossible on Aurora nodes** (no FUSE/userns) -> Recipe A' is
  mandatory, not optional; build on Polaris and copy binaries, or build inside
  A' on Aurora.
- **R3 25,600 cold starts through one proxy** -> A' for production; stagger.
- **R4 `debug` is non-exclusive** -> timing numbers from `debug` are not clean;
  use `debug-scaling` (2 nodes minimum) for measurements.
- **R5 allocation access** -> `debug2` covers bootstrap + validation + a 128-node
  hour twice over; the production pot needs twester.
- **R6 FP differences on Intel** -> the exact 19/19 gate tells us immediately;
  the known acceptable residual classes are listed in the procedure doc §7.

## 6. Decisions needed from the user

1. Path/dataset of the official Gen2 reco1 on Flare (Q4), and which sample(s)
   make up the 1M events.
2. OK to ask twester for Flare quota/space and for access to the main Aurora
   pot (Q5, Q8)?
3. Per-file vs per-event job granularity for production (Q6).
4. Whether to stand up Recipe A' (Flare UPS tree) now or only if cvmfsexec fails.
