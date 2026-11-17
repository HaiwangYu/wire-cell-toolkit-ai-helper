# Issue 49: the five deterministic step-2 segfaults in WCT 0.38.0 `Clus::PR` (porting_sbndbuild03)

The five pairs come from WCLocal2026Nov16-FermiGrid (#48). Their crash events, all simulation:

| sample | pair | event (run/subrun/event) |
|---|---|---|
| CV | `reco1-detsim-g4-gen-Gen2_2026-d8bb-e799-f307-1327` | 4803/48/12 |
| CV | `…-d7e5-a516-3477-e682` | 8169/41/12 |
| nueCC | `reco1-detsim-g4-filter-gen-2c2d-7fef-91ef-6f3a_nuecc` | 230/90/10679 |
| nueCC | `…-b61a-f473-a953-2776_nuecc` | 259/49/7138 |
| nueCC | `…-2ce6-000e-14f2-234d_nuecc` | 206/11/5680 |

## Reproducer

**Inputs.** One-event step-1 tars, cut from the production qlpctrees (the members of that one tensor set):
`/exp/sbnd/data/users/yuhw/wclocal-nov16/issue49/in/{cv-d8bb-4803_48_12,cv-d7e5-8169_41_12,nuecc-2c2d-230_90_10679,nuecc-b61a-259_49_7138,nuecc-2ce6-206_11_5680}.qlpctree.tar.gz` (2–8 MB each).

**Command.** `scripts/run-step2.sh <tar> <outdir> sim <arm> [cpu]`. It runs the 0.38.0 release at `wclocal-nov16/` with `wct-pr.jsonnet`, one pinned CPU, 1 thread, `GODEBUG=asyncpreemptoff=1` and `-L debug`. The arms:

| arm | vertex_method | DV2 bundle |
|---|---|---|
| `split` (production pass 1) | `dv2_split_move` | `aurora_space` |
| `snap` (production pass 2) | `dv2_snap` | `aurora_space` |
| `orig` | `original` | none |
| `r7` | `dv2_split_move` | `r7_cloud` |

Each crash takes 1–4 minutes.

## Results on the one-event tars (sbndbuild03, 2026-11-17)

| event | split | snap | orig | r7 | `aliased` lines before the crash | crash frame |
|---|---|---|---|---|---|---|
| CV d8bb 4803/48/12 | 139 | 139 | **0** | **0** | 0 | `find_other_vertex` (PRGraph.cxx:362) ← `bad_reconstruction` (NeutrinoTaggerCosmic.cxx:293) ← `nue_tagger` |
| CV d7e5 8169/41/12 | 139 | (OK on the grid) | **0** | 139 | 0 | `VertexIndexCmp` in `std::set::insert` (NeutrinoShowerClustering.cxx:8154), `id_pi0_with_vertex` |
| nueCC 2c2d 230/90/10679 | 139 | 139 | 139 | 139 | 1–2 | `boost::remove_edge` (PRGraph.cxx:315) ← `remove_segment` ← `break_segment_into_two` (NeutrinoPatternBase.cxx:1933) ← `break_segments` ← `find_other_segments` |
| nueCC 2ce6 206/11/5680 | 139 | 139 | 139 | 139 | 1–3 | the same as 2c2d |
| nueCC b61a 259/49/7138 | 139 | 139 | 139 | 139 | 1–3 | `examine_segment` (NeutrinoStructureExaminer.cxx:1309) ← `examine_vertices`. The full-file run crashed nearby, in TrackFitting from `examine_vertices_1` |

- **Every crash reproduces on the single event alone**, with the same frame as in the production files and on the grid.
- **Two bugs.** The three nueCC crashes don't depend on the vertex method or the model. The two CV crashes happen only with DV2 placement.

## Bug A (the 3 nueCC): a parallel segment aliased onto an existing edge leaves a dangling descriptor

The PR graph is `adjacency_list<setS, setS, undirectedS, …>` (PRGraphType.h:91), so it refuses parallel edges.

When `PR::add_segment` connects two vertices that already have an edge (PRGraph.cxx:200-253):
1. `boost::add_edge` returns the existing descriptor with `added=false`.
2. The new segment gets that descriptor (`seg->set_descriptor(desc)`).
3. The edge's bundle is re-pointed to the new segment (`g[desc].segment = seg`).

**The old segment keeps the same descriptor and still reports `descriptor_valid()`.** Two `Segment` objects now share one edge. When either is removed, `remove_segment` calls `boost::remove_edge` and invalidates only that segment. The other segment's next `remove_segment`, `find_vertices` or `find_other_vertex` then works on a freed edge node (`_List_node_base::_M_unhook`). That is a use-after-free, so the crash site depends on what touches the stale edge first; this explains b61a's two different frames.

The code already counts this case (`g_port_audit.edge_aliased`) and logs the first 20 of each process at DEBUG: "PR::add_segment: parallel segment aliased onto existing edge (doc pr/31 F9)". The comment there says it is "counted …, not fixed".

**Evidence:**
- Each nueCC crash log has the aliasing line before the crash (275–389 log lines earlier in 2c2d / b61a). It comes right after a `do_rough_path` that builds a segment with the same endpoints and the same number of points as the existing one ("old nwcpts=10 new nwcpts=10").
- Aliasing is common and usually harmless:
  - the nueCC `2008` pair: 4 lines in 8 events, no crash;
  - the beam-off `91943619` pair: ≥20 lines (the cap) in 50 events, no crash.
- It only crashes when one of the two aliases is later removed and the other is used.

**Fix options:**
1. **Make the alias safe.** Record the orphaned segment, for example as a list on the edge bundle.
   - In `remove_segment`: if `g[desc].segment != seg`, only invalidate `seg` and leave the edge alone.
   - When the owning segment's edge is removed, invalidate every recorded alias.
   - This removes the use-after-free. Events that don't crash today could still change where an orphan's removal used to take the owner's edge with it, so it must be measured.
2. **Allow parallel edges** (`multisetS` out-edges). This matches the prototype, whose `map_vertex_segments` holds both segments. It is a bigger change in behaviour; the code comment calls it "its own escalation".
3. **Refuse the duplicate** in the caller (`find_other_segments` / `do_rough_path`) when an edge between the two vertices already exists.

To do: find the exact caller that creates the duplicate, then compare outputs with and without the fix on the #43 samples, nueCC-48 and NCπ0-19 before choosing.

## Bug B (the 2 CV): a null shower start vertex used without a check

`Shower::set_start_vertex` stores null when the vertex has no valid descriptor (PRShower.h:112-121). Two consumers then use it unchecked:
- **`id_pi0_with_vertex`** (NeutrinoShowerClustering.cxx:8151-8155) inserts each pi0 shower's `start_vtx` into an `IndexedVertexSet`. Its comparator `VertexIndexCmp` calls `get_graph_index()` on the null pointer. This is the d7e5 frame.
- **`bad_reconstruction`** (NeutrinoTaggerCosmic.cxx, from `nue_tagger` at NeutrinoTaggerNuE.cxx:1008) passes `vtx` to `find_other_vertex`. That calls `vertex->descriptor_valid()` (PRGraph.cxx:362) without checking `vertex` (or `seg`) for null. This is the d8bb frame.

Both run only after DV2 placement:
- `orig` passes on both events. `r7` passes on d8bb and crashes on d7e5.
- So the model and placement decide whether a shower ends up with a start vertex that is not in the graph.

**Fix:** null checks, as at other call sites:
- `if (!vertex || !vertex->descriptor_valid()) return nullptr;` in `find_other_vertex`;
- skip a null `start_vtx` in `id_pi0_with_vertex`;
- check the other `get_start_vertex_and_type()` users the same way.
- Then find why DV2 leaves the start vertex out of the graph: a vertex replaced by the DV2 move without updating the shower.

**Confirmed with gdb** (`scripts/gdb-step2.sh`; logs in `wclocal-nov16/issue49/gdb/`):
- d8bb: in `find_other_vertex` the argument `vertex._M_ptr = 0x0`, while `seg` is valid. In `bad_reconstruction`, `get_start_vertex_and_type()` returned `(nullptr, 0)`.
- d7e5: `Vertex::get_graph_index (this=0x0)`. In `id_pi0_with_vertex`, `start_vtx._M_ptr = 0x0` with connection type 2.

## Next
1. Bug B is confirmed with gdb. For bug A, gdb can't see the locals at `remove_segment` in the optimized build. It will be confirmed in the fix branch instead, with a check that logs when the segment being removed doesn't own its edge (`g[desc].segment != seg`).
2. Find the caller that creates the duplicate segment (A) and the step that drops the start vertex (B).
3. Fix branch on my fork, off 0.38.0. Rerun the five events, then compare before/after on the #43 samples, nueCC-48 and NCπ0-19. No WireCell PR.
4. Aurora's `eb42-73cd-76d2-dd4f` (old chain): check its log for the same aliasing line or frames. Asked prod_aurora on #49.
