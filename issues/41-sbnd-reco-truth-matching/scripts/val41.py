#!/usr/bin/env python3
"""ai-helper issue 41 validation (run inside SL7 with ROOT; python3 -I not needed).

    val41.py v1   <new pair dir> <r7 unit dir>     every r7 tree of every event identical in the new file
    val41.py tar  <new pair dir> <r7 unit dir>     step-1 qlpctree.tar.gz: r7 members unchanged, list the new ones
    val41.py v3   <new pair dir>                   T_overlap labels vs the step-1 Bee truth layers
    val41.py caf  <new pair dir> <old pair dir>     merged CAF recTreeWireCell: old branches identical, new ones empty (data, V2)
    val41.py v45  <work dir> <matteo csv> [<matteo truthmatch dir>]
                                                   T_match level 3 vs Matteo's r7 table (V4) and
                                                   vs his truthmatch functions on T_overlap (V5)
Prints one JSON summary line per call (last line), details above it.
"""
import collections
import glob
import io
import json
import math
import os
import sys
import tarfile
import zipfile

import ROOT

ROOT.gErrorIgnoreLevel = ROOT.kError
NEW_TREES = {"T_truth_track", "T_overlap", "T_match", "T_pf", "T_blob_truth", "recTreeWireCell"}


def events(pair_dir):
    """event -> tracking-pr.root, for both layouts: pr/<tag>/pr_evt<E> (run_pair.py) and pr/pr_evt<E> (r7)."""
    files = glob.glob(os.path.join(pair_dir, "pr", "*", "pr_evt*", "tracking-pr.root")) + \
        glob.glob(os.path.join(pair_dir, "pr", "pr_evt*", "tracking-pr.root"))
    return {int(os.path.basename(os.path.dirname(f))[len("pr_evt"):]): f for f in files}


def leaf_values(tree, names):
    out = []
    for n in names:
        v = getattr(tree, n)
        if isinstance(v, (int, float, str, bool)):
            out.append(v)
        elif hasattr(v, "size") and hasattr(v, "__getitem__"):
            try:
                out.append([list(x) if hasattr(x, "size") and not isinstance(x, str) else x for x in v])
            except TypeError:
                out.append(str(v))
        else:
            out.append(str(v))
    return out


def same(a, b):
    if isinstance(a, float) and isinstance(b, float):
        return a == b or (math.isnan(a) and math.isnan(b))
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    return a == b


def v1(new_dir, r7_dir):
    new, old = events(new_dir), events(r7_dir)
    res = dict(events_r7=len(old), events_new=len(new), missing=sorted(set(old) - set(new)),
               trees_compared=0, values_compared=0, diffs=collections.Counter(), branch_only_new=set(),
               branch_only_r7=set())
    for e in sorted(set(old) & set(new)):
        fo, fn = ROOT.TFile.Open(old[e]), ROOT.TFile.Open(new[e])
        for k in fo.GetListOfKeys():
            name = k.GetName()
            to, tn = fo.Get(name), fn.Get(name)
            if not to.InheritsFrom("TTree"):
                continue
            if not tn:
                res["diffs"]["%s missing" % name] += 1
                continue
            bo = [b.GetName() for b in to.GetListOfBranches()]
            bn = [b.GetName() for b in tn.GetListOfBranches()]
            res["branch_only_r7"] |= {"%s.%s" % (name, b) for b in bo if b not in bn}
            res["branch_only_new"] |= {"%s.%s" % (name, b) for b in bn if b not in bo}
            common = [b for b in bo if b in bn]
            res["trees_compared"] += 1
            if to.GetEntries() != tn.GetEntries():
                res["diffs"]["%s entries" % name] += 1
                continue
            for i in range(to.GetEntries()):
                to.GetEntry(i)
                tn.GetEntry(i)
                for b, x, y in zip(common, leaf_values(to, common), leaf_values(tn, common)):
                    res["values_compared"] += 1
                    if not same(x, y):
                        res["diffs"]["%s.%s" % (name, b)] += 1
        for k in fn.GetListOfKeys():
            if k.GetName() not in NEW_TREES and not fo.Get(k.GetName()):
                res["diffs"]["extra tree %s" % k.GetName()] += 1
    res["diffs"] = dict(res["diffs"])
    res["branch_only_new"] = sorted(res["branch_only_new"])
    res["branch_only_r7"] = sorted(res["branch_only_r7"])
    return res


def tar_members(path):
    """datapath -> (metadata without the sequence-dependent keys, array bytes).  Tensor files are
    numbered in write order (clustering_tensor_<ident>_<k>_*), so new arrays shift k: key by datapath."""
    raw = {}
    with tarfile.open(path) as t:
        for m in t.getmembers():
            if m.isfile():
                raw[m.name] = t.extractfile(m).read()
    out = {}
    for n, b in raw.items():
        if not n.endswith("_metadata.json"):
            continue
        md = json.loads(b)
        arr = raw.get(n[:-len("_metadata.json")] + "_array.npy", b"")
        dp = md.get("datapath", n)
        if dp in out:   # set-level metadata of several sets
            dp = dp + "#" + n
        out[dp] = (json.dumps({k: v for k, v in md.items() if k not in ("arrays",)}, sort_keys=True), arr)
    return out


def tarcmp(new_dir, r7_dir):
    a = tar_members((glob.glob(os.path.join(r7_dir, "ql", "qlpctree.tar.gz")) +
                     glob.glob(os.path.join(r7_dir, "ql", "*", "qlpctree.tar.gz")))[0])
    b = tar_members(glob.glob(os.path.join(new_dir, "ql", "*", "qlpctree.tar.gz"))[0])
    changed_arr = sorted(n for n in a if n in b and a[n][1] != b[n][1])
    changed_md = sorted(n for n in a if n in b and a[n][0] != b[n][0])
    new_only = sorted(n for n in b if n not in a)
    kinds = collections.Counter(n.split("/")[-1] if "/arrays/" in n else n.split("/")[0] for n in new_only)
    return dict(tensors_r7=len(a), tensors_new=len(b), missing=sorted(n for n in a if n not in b)[:10],
                changed_arrays=len(changed_arr), changed_arrays_first=changed_arr[:10],
                changed_metadata=len(changed_md), changed_metadata_first=changed_md[:5],
                new_tensors=len(new_only), new_kinds=dict(kinds))


def bee_layer(zf, idx, layer):
    names = [n for n in zf.namelist() if n.endswith("/%d-%s.json" % (idx, layer))]
    return json.loads(zf.read(names[0])) if names else None


def v3(new_dir):
    evs = events(new_dir)
    zf = zipfile.ZipFile(glob.glob(os.path.join(new_dir, "ql", "*", "mabc.zip"))[0])
    res = dict(events=0, total_match=0, labeled_match=0, per_track_match=0, details=[])
    for i, e in enumerate(sorted(evs)):
        f = ROOT.TFile.Open(evs[e])
        to, tt = f.Get("T_overlap"), f.Get("T_truth_track")
        if not to:
            res["details"].append("evt %d: no T_overlap" % e)
            continue
        bee_of = {r.trackid: r.bee_trackid for r in tt}
        n_tot = n_lab = 0
        per = collections.Counter()
        for r in to:
            n_tot += r.n_points
            if r.trackid >= 0:
                n_lab += r.n_points
                per[bee_of.get(r.trackid, r.trackid)] += r.n_points
        lab, unl = bee_layer(zf, i, "truth_trackid_labeled"), bee_layer(zf, i, "truth_unlabeled")
        if lab is None or unl is None:
            res["details"].append("evt %d: bee index %d lacks the truth layers" % (e, i))
            continue
        res["events"] += 1
        b_lab, b_unl = len(lab["x"]), len(unl["x"])
        bper = collections.Counter(lab["cluster_id"])
        ok_t, ok_l, ok_p = (n_tot == b_lab + b_unl), (n_lab == b_lab), (dict(per) == dict(bper))
        res["total_match"] += ok_t
        res["labeled_match"] += ok_l
        res["per_track_match"] += ok_p
        if not (ok_t and ok_l and ok_p):
            res["details"].append("evt %d: overlap %d/%d labeled, bee %d/%d, tracks differ %d" % (
                e, n_lab, n_tot, b_lab, b_lab + b_unl, sum(1 for k in set(per) | set(bper) if per[k] != bper[k])))
    return res


def level_rows(f, level):
    reco, truth = {}, {}
    for r in f.Get("T_match"):
        if r.level != level:
            continue
        d = dict(obj=r.obj, nu_index=r.nu_index, cluster_id=r.cluster_id, kine_index=r.kine_index,
                 truth_nu_idx=r.truth_nu_idx, truth_trackid=r.truth_trackid, size_n=r.size_n,
                 n_unlabeled=r.n_unlabeled, mutual=r.mutual, match_obj=list(r.match_obj),
                 match_iou_n=list(r.match_iou_n), match_shared_n=list(r.match_shared_n))
        (reco if r.side == 0 else truth)[r.obj] = d
    return reco, truth


def truth_label(t):
    if t["truth_nu_idx"] >= 0 and t["truth_trackid"] < 0:
        return "nu%d" % (t["truth_nu_idx"] + 1)          # Matteo: k >= 1 = interaction k
    return "cosmic%d" % t["truth_trackid"]


def v45(work, csv_path, tm_dir=None):
    import csv
    rows = [x for x in csv.DictReader(open(csv_path)) if x["row_kind"] == "candidate"]
    ref = {(int(x["run"]), int(x["subrun"]), int(x["event"]), int(float(x["nu_index"]))): x for x in rows}
    spine = None
    if tm_dir:
        sys.path.insert(0, tm_dir)
        import truthmatch as spine   # noqa: E402  (Matteo's module, read-only)
        import pandas as pd          # noqa: E402
    res = collections.Counter()
    details = []
    for pair in sorted(glob.glob(os.path.join(work, "*", "pr"))):
        for e, fn in sorted(events(os.path.dirname(pair)).items()):
            f = ROOT.TFile.Open(fn)
            if not f.Get("T_match"):
                continue
            tr = f.Get("Trun")
            tr.GetEntry(0)
            rse = (tr.runNo, tr.subRunNo, tr.eventNo)
            for level in (2, 3):
                reco, truth = level_rows(f, level)
                for r in reco.values():
                    if r["nu_index"] < 0:
                        continue
                    key = rse + (r["nu_index"],)
                    best = truth[r["match_obj"][0]] if r["match_obj"] else None
                    mine = dict(ct_n=r["size_n"], ct_n_unlabeled=r["n_unlabeled"],
                                ct_match=truth_label(best) if best else "",
                                ct_iou=r["match_iou_n"][0] if best else 0.0,
                                ct_n_shared=r["match_shared_n"][0] if best else 0.0, ct_mutual=r["mutual"])
                    if level == 3:
                        res["candidates"] += 1
                        x = ref.get(key)
                        if x is None:
                            res["not_in_matteo"] += 1
                            continue
                        res["compared"] += 1
                        same_n = abs(float(x["ct_n"] or 0) - mine["ct_n"]) < 0.5
                        same_m = (x["ct_match"] or "") == mine["ct_match"] or (
                            (x["ct_match"] or "").startswith("cosmic") and mine["ct_match"].startswith("cosmic"))
                        same_i = abs(float(x["ct_iou"] or 0) - mine["ct_iou"]) < 1e-6
                        res["same_size"] += same_n
                        res["same_match"] += same_m
                        res["same_match_label_exact"] += (x["ct_match"] or "") == mine["ct_match"]
                        res["same_iou_1e-6"] += same_i
                        res["iou_within_0.01"] += abs(float(x["ct_iou"] or 0) - mine["ct_iou"]) < 0.01
                        if not (same_n and same_m and same_i):
                            details.append("%s nu%d: matteo n=%s unl=%s match=%s iou=%.4f | ours n=%d unl=%d match=%s iou=%.4f" % (
                                rse, r["nu_index"], x["ct_n"], x["ct_n_unlabeled"], x["ct_match"],
                                float(x["ct_iou"] or 0), mine["ct_n"], mine["ct_n_unlabeled"], mine["ct_match"], mine["ct_iou"]))
            # V5: Matteo's own iou_matrix/spine_match on T_overlap (level 3 objects)
            if spine is not None:
                reco3, truth3 = level_rows(f, 3)
                bee_of, nu_of = {}, {}
                for t in f.Get("T_truth_track"):
                    bee_of[t.trackid] = t.bee_trackid
                    nu_of[t.trackid] = t.nu_idx
                recs = []
                for o in f.Get("T_overlap"):
                    rk = "cand%d" % o.nu_index if o.in_pf else "pr%d" % o.cluster_id
                    tk = None
                    if o.trackid >= 0:
                        tk = ("nu%d" % (nu_of[o.trackid] + 1)) if nu_of[o.trackid] >= 0 else "cosmic%d" % bee_of[o.trackid]
                    recs.append(dict(reco=rk, truth=tk, n=o.n_points, q=o.q))
                p = pd.DataFrame(recs)
                lab = p[p.truth.notna()]
                pairs = lab.groupby(["reco", "truth"]).agg(n=("n", "sum"), q=("q", "sum")).reset_index()
                rsz = p.groupby("reco").agg(n=("n", "sum"), q=("q", "sum"))
                tsz = lab.groupby("truth").agg(n=("n", "sum"), q=("q", "sum"))
                M = spine.iou_matrix(pairs, rsz, tsz, "points")
                r2t, t2r = spine.spine_match(M)
                for r in reco3.values():
                    if r["nu_index"] < 0:
                        continue
                    lab_ = "cand%d" % r["nu_index"]
                    if lab_ not in r2t.index:
                        continue
                    best = truth3[r["match_obj"][0]] if r["match_obj"] else None
                    py_t = r2t.truth.get(lab_)
                    py_i = float(r2t.iou.get(lab_))
                    ok = ((py_t is None or (isinstance(py_t, float) and math.isnan(py_t))) and best is None) or (
                        best is not None and py_t == truth_label(best) and abs(py_i - r["match_iou_n"][0]) < 1e-6)   # T_match stores float32
                    res["v5_candidates"] += 1
                    res["v5_same"] += ok
                    if not ok:
                        details.append("V5 %s %s: python %s %.6f | T_match %s" % (rse, lab_, py_t, py_i, best and truth_label(best)))
    print("\n".join(details))
    return dict(res)


def cafcmp(new_dir, old_dir):
    """recTreeWireCell of the merged CAF: every branch of the old file identical in the new one;
    a branch only in the new file must be empty (its ..length 0) -- the data check (V2)."""
    fo = ROOT.TFile.Open(glob.glob(os.path.join(old_dir, "merged", "*.root"))[0])
    fn = ROOT.TFile.Open(glob.glob(os.path.join(new_dir, "merged", "*.root"))[0])
    to, tn = fo.Get("recTreeWireCell"), fn.Get("recTreeWireCell")
    bo = [b.GetName() for b in to.GetListOfBranches()]
    bn = [b.GetName() for b in tn.GetListOfBranches()]
    only_new = [b for b in bn if b not in bo]
    res = dict(entries=(to.GetEntries(), tn.GetEntries()), branches=(len(bo), len(bn)),
               missing=[b for b in bo if b not in bn][:5], only_new=len(only_new), values=0, diffs=collections.Counter(),
               nonempty_new=collections.Counter())
    lens = [b for b in only_new if b.endswith("..length")]
    for i in range(min(to.GetEntries(), tn.GetEntries())):
        to.GetEntry(i)
        tn.GetEntry(i)
        for b in bo:
            if b not in bn:
                continue
            x, y = getattr(to, b), getattr(tn, b)
            if hasattr(x, "__len__") and not isinstance(x, str):
                x, y = list(x), list(y)
            res["values"] += 1
            if not same(x, y):
                res["diffs"][b] += 1
        for b in lens:
            if getattr(tn, b) != 0:
                res["nonempty_new"][b] += 1
    res["diffs"] = dict(res["diffs"])
    res["nonempty_new"] = dict(res["nonempty_new"])
    return res


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "v1":
        out = v1(sys.argv[2], sys.argv[3])
    elif mode == "tar":
        out = tarcmp(sys.argv[2], sys.argv[3])
    elif mode == "v3":
        out = v3(sys.argv[2])
    elif mode == "caf":
        out = cafcmp(sys.argv[2], sys.argv[3])
    elif mode == "v45":
        out = v45(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else None)
    else:
        sys.exit(__doc__)
    print(json.dumps(out, default=str))
