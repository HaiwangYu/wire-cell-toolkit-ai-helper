# Issue 15 — MLDataWriters: modularise nugraph / DL-vertexing / BDT as MABC visitors

One family of ML training-data writers built on the MABC visitor pattern, so that
no extra serialization is paid and `TensorSetLabeler` stops growing.
**Planning only — nothing implemented.**

Primary document: `wcp-porting-img/sbnd/docs/7-mldatawriters-plan.html`
Work dir: `/exp/sbnd/data/users/yuhw/production-prep/mldatawriters-dev`
NOT related to the CAF project (#14).  Builds on #13.

## Short answer

**Yes, MABC + visitor is the right shape.**  There is already a working in-tree
precedent: three MABC visitors write their own output files today --
`SbndPrMagnifyTrackingVisitor` and `UbooneTaggerOutputVisitor` write ROOT,
`PrDisplayDump` writes JSON -- and the toolkit ships HDF5 via `hio` (`HDF`,
`HioTensorSink`).

**But one hard constraint shapes it:** a WCT visitor cannot reach `art::Event`,
and all three writers need truth.  So: ONE art-side truth injector plus N pure
WCT writers.  That is also what stops `TensorSetLabeler` growing.

## Why restructure

`TensorSetLabeler` is 1731 lines .cxx + 370 .h doing four separable jobs (truth
association, `truth_per_track`, several Bee families, nugraph HDF5).  Its Bee
half already needed splitting once (`bee_sets` / `label_blobs`, #13).  Two more
writers would push it past any reasonable size.

And each art-level module deserializes -> mutates -> re-serializes the tree.
Chaining writers as separate `ITensorSetFilter`s multiplies that round trip for
nothing, since they all want the same tree.

## The constraint that decides the architecture

| writer | needs | survives serialization? | visitor? |
|---|---|---|---|
| nugraph | `3d`, the six `ctpc_a{0,1}f0p{U,V,W}`, per-blob `trackid`, nu truth | **yes, all** | yes, or downstream |
| DL-vertexing | `3d` (x,y,z,q) + true nu vertex | **yes** (`3d` is a PC; `nu_vtx_*` is set metadata) | yes |
| BDT | `TaggerInfo`, `KineInfo`, PR graph / `TrackFitting` | **NO** | **visitor ONLY** |

`as_tensors` serializes only `node->value.local_pcs()`
(`aux/src/TensorDMpointtree.cxx:82`), while `TrackFitting` is a private facade
member (`Facade_Grouping.h:392`, named slots at `:393`).  Not a PC, so never
written -- it dies when `MABC::operator()` returns.

**So BDT training data can only be produced from inside the MABC pipeline.**
There is no downstream position from which it is even visible.  That settles it:
the visitor pattern is required for one of the three, and using it for all three
makes them uniform.

PCs that DO survive: `3d`, `scalar`, `cluster_scalar`, `grouping_scalar`,
`perblob`, `steiner_pc`, `corner`, `ctpc_a{0,1}f0p{U,V,W}`, `dead_winds_*`,
`dead_gap_*`, `flash`, `flashlight`, `opflash`, `light`.

## The art boundary

Visitors get `visit(Facade::Ensemble&)` and nothing else -- no art event, no
ITensorSet, not even an ident.  Truth must be INJECTED before any visitor runs.
Two channels exist and are proven:

- **blob-level `scalar` PC** carries per-blob `trackid`; verified in #13 to
  survive switch_scope / unmerge_bundle / unmerge_assoc / protect_bundle,
  because it rides the BLOB node while switch_scope erases only cluster-level
  `perblob`.
- **ensemble scalar PC** carries event-level values; MABC already stamps
  `ensemble.set_scalar<int>("runNo", ...)` so the ROOT visitors can identify
  their event (#13 §7.3).

Gap this closes: nu truth currently lives in the tensor-set METADATA (`n_nu`,
`nu_pdg`, `nu_energy`, `nu_vtx_{x,y,z}`, `nu_ccnc`, `nu_int_type`, `nu_flavor`,
`nu_edep`), which visitors cannot see.  A DL-vertexing visitor needs the vertex
re-published as an ensemble scalar -- a few lines in the injector, reusing an
existing mechanism.

## Proposed shape

```
art   larwirecell: TruthInjector          <- the ONLY art touchpoint
        MCTruth / MCParticle / SimEnergyDeposit, read once
        writes blob scalar.trackid + truth_per_track
        publishes nu truth as ensemble scalars
              |  one tree, no extra round trip
WCT   MABC pipeline (visitors, in declaration order)
        ... clustering / tagger stages ...
        NuGraphWriter    3d + ctpc_* + trackid   -> HDF5
        DLVertexWriter   3d + nu_vtx             -> HDF5
        BDTDataWriter    TaggerInfo / KineInfo   -> ROOT or HDF5
```

Which MABC each belongs to (they are not interchangeable):

- `BDTDataWriter` -> **clus_pr**, the only place TaggerInfo/TrackFitting exists.
  Must be named AFTER the BDT scorers or the scores read zero -- the exact trap
  that made the merged Bee node print `numu 0.000` against T_tagger's `-1.7148`
  (#13).
- `NuGraphWriter` -> **clus_all_apa** (where nugraph is produced today; needs
  the merged tree and the 2-D ctpc PCs).
- `DLVertexWriter` -> **clus_all_apa** (wants the assembled 3-D cloud before the
  PR stage splits clusters).

## Pitfalls to design out from the start

- **Fixed output filenames break multi-event runs.**  Not hypothetical:
  tracking-pr.root is written by two visitors sharing one filename (RECREATE +
  UPDATE), so `lar -n N` silently gives an 8 kB file with T_tagger/T_kine absent
  (#13 G9).  Handle many events per process BY CONSTRUCTION.
- **"No content" must differ from "failed".**  6 of 10 events on run 925-23 had
  no neutrino candidate, and their tracking-pr.root is byte-indistinguishable
  from the corrupted multi-event case.  Write an explicit empty record.
- **Silent fallbacks.**  The recurring failure here is plausible output computed
  the wrong way (the sp.jsonnet extVar; the DL vertex falling back to geometric
  without torch).  Assert inputs, fail loudly, and add a check per writer to
  `sbnd/check-pr-run.sh`.

## Phasing

1. **Split, do not add.**  Move nugraph out of TensorSetLabeler into
   `NuGraphWriter`, no behaviour change, gated byte-identical against the
   current `nugraph.h5`.  Proves the pattern where the right answer is known.
2. `DLVertexWriter` -- smallest new writer: `3d` + nu vertex as ensemble scalar.
3. `BDTDataWriter` -- the one that needs the visitor position.  Start from what
   UbooneTaggerOutputVisitor already reads (`tf->get_tagger_info()`,
   `get_kine_info()`).
4. Factor shared HDF5/append/empty-record plumbing once the third writer shows
   what is actually common.  Not before.

## Open questions

1. Is BDT "dump the existing 1216 features for retraining" or "a new feature
   set"?  The first is nearly free; the second is a physics project.
2. One file per writer per job, or one shared HDF5?
3. Does DL-vertexing training data need the FITTED trajectory
   (T_rec_charge-equivalent), or only blob points?  If the fit is wanted it must
   first be persisted into PCs -- `TaggerCheckSTM`'s save_stm_fit shows how
   (`cluster.local_pcs()["stm_fit"]`, `.cxx:808`); TaggerCheckNeutrino has no
   equivalent yet.
4. Production-on, or training-data jobs only?
5. Keep the name `TensorSetLabeler` for the slimmed injector, or rename to
   `TruthInjector`?  Renaming is honest but breaks every existing fcl.
