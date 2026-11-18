# prod_aurora: Aurora's WCT 0.38.0 step-2 segfaults (WCLocal2026Nov16-Aurora P5, #48)

Of 90,744 Aurora units, the deterministic step-2 segfaults are:
- 2 new ones, in the `dv2_snap` pass only (νe CC `3619`, `56a9`);
- `eb42` (BNB), also seen in aurora-r2 / dlspace;
- 5 older νe CC units, the same as in dlspace and not examined here: `58e1`, `a3f6`, `4a8d` (PARTIAL) and `cb29`, `60c5` (FAIL).

The first three reproduce on one-event step-1 tars.

## Inputs

`in/<case>.qlpctree.tar.gz` is one event, cut from the production `ql/all/qlpctree.tar.gz` by `scripts/crash-extract.py`:
- It reads the production `wct.log.gz` and finds the tensor-set ident loaded just before the `*** Break ***`.
- It copies the members `clustering_tensor[set]_<ident>_*` of that occurrence. A BNB unit spans several reco1 files, so idents repeat inside its tar; for `eb42` it takes occurrence 2 of 5.

| case | unit | crash event (ident; output-dir name) | production pass(es) that crash |
|---|---|---|---|
| `nuecc-3619-snap` | `reco1-detsim-g4-filter-gen-3619-47a2-429e-4b6c` | ident 37, `pr_evt6711558_11_37` (1st event of the unit) | snap only (split-move 6/6) |
| `nuecc-56a9-snap` | `reco1-detsim-g4-filter-gen-56a9-5a4b-0436-282e` | ident 29, `pr_evt6702488_18_29` (7th event) | snap only (split-move 8/8, snap 6/8) |
| `bnb-eb42-split` | `reco2-reco1-detsim-g4-gen-eb42-73cd-76d2-dd4f` | ident 6, 21st tensor set of the unit | both passes, every try; also in aurora-r2 (old chain), 20/42 events |

## Reproduction (debug job 9100323, 2026-11-18)

`scripts/i49-repro.pbs` runs each tar × both passes with the production setup: `scripts/step2-pass.sh`, the 0.38.0 release `opt-0.38.0`, `wct-pr.jsonnet`, `-L debug`, `GODEBUG=asyncpreemptoff=1`, aurora_space bundle, `vertex_method` `dv2_split_move` (+ space dump) or `dv2_snap`.

| case | split-move | snap | frame (`logs/<case>.<pass>.frames.txt`) | "aliased onto existing edge" |
|---|---|---|---|---|
| νe CC 3619 | **OK** (event written) | **rc 139** | `Vertex::get_graph_index` (PRVertex.h:121) ← `VertexIndexCmp` (PRGraph.h:357) ← `std::set::insert` ← `PatternAlgorithms::id_pi0_with_vertex` ← `shower_clustering_with_nv` ← `TaggerCheckNeutrino::visit` | 0 |
| νe CC 56a9 | **OK** (event written) | **rc 139** | `HasCluster<Vertex>::cluster` ← `bad_reconstruction_2_sp` (NeutrinoTaggerSinglePhoton.cxx:929) ← `PatternAlgorithms::singlephoton_tagger` | 0 |
| BNB eb42 | **rc 139** | **rc 139** | `TrackFitting::do_multi_tracking` ← `PatternAlgorithms::examine_vertices_1` ← `examine_vertices` ← `find_proto_vertex` | **1** (`edge idx=10 old nwcpts=17 new nwcpts=17`) |

All three crash at the same frame as in production (`logs/repro-results.txt`, `logs/*.before-crash.txt`).

## Reading (frames and logs only; no gdb yet)

- **3619 is the snap-path twin of bug B.** It has the same frame as FermiGrid CV `d7e5`: a null shower `start_vtx` inserted into an `IndexedVertexSet` in `id_pi0_with_vertex`.
  - Here it happens with `dv2_snap` and not with `dv2_split_move`.
  - So the placement decides whether a shower's start vertex drops out of the graph.
- **56a9 is most likely bug B through a third consumer.** `bad_reconstruction_2_sp` calls `HasCluster::cluster` on a vertex pointer that is null (or dangling).
  - It is probably the same `get_start_vertex_and_type()` → `(nullptr, …)` as `d8bb`'s `find_other_vertex`, but in the single-photon tagger.
  - The fix list for bug B ("check the other `get_start_vertex_and_type()` users") should include `NeutrinoTaggerSinglePhoton.cxx:929`.
- **eb42 looks like bug A on the old chain.** One parallel segment is aliased onto an existing edge in that event, and it then crashes in TrackFitting inside `examine_vertices_1`. That is the fifth FermiGrid signature, as for `b61a`.
  - It crashes with both vertex methods, and in aurora-r2 (old `r7`-era chain), consistent with A being independent of the vertex method.
  - Not confirmed with gdb.

## Not done

- No gdb or debug build.
- No `original` / `r7_cloud` arms on these three tars.
- The tars and `scripts/` are here for @porting_sbndbuild03's matrix: `run-step2.sh` should take them as they are (sim, 1 event each).
