#!/usr/bin/env python3
"""Pair the two runs event by event and compare their recob::Wire products.

For every subrun the pairing is derived from the art provenance JSONs
(Avinay's detsim JSON names Thomas's g4 file as its parent), so no external
mapping table is needed.  For every event it records

  * the RSE (run, subrun, event) decoded from EventAuxiliary in all four
    files (Thomas/Avinay x reco1/detsim) -- they must agree;
  * SHA-256 of the decompressed basket bytes (one basket = one event) of
    reco1 simtpc2d:dnnsp and detsim simtpc2d:dnnsp/gauss/wiener, Thomas vs
    Avinay -> byte-identical or not;
  * the decoded waveform difference (max |A-B|, number of differing samples,
    charge sums) for dnnsp (reco1) and gauss/wiener (detsim);
  * the pass-through check reco1 dnnsp == detsim dnnsp within each run.

Usage:
  compare_wires_hash.py [--thomas DIR] [--abhat DIR] [--out manifest.tsv]
Runs on the Aurora UAN with uproot only (no ROOT dictionaries): the wire
payload is decoded by wirebytes.py.
"""
import argparse, glob, hashlib, json, os, sys, time
import numpy as np
import uproot
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wirebytes import decode_rse, dense_wires

T_DEF = "/lus/flare/projects/neutrinoGPU/twester/scratch/sbnd_gen2_full"
A_DEF = "/lus/flare/projects/neutrinoGPU/abhat/sbnd/thomas-g4-parsl-reproduction-20260921"
SUB = "000000/000000"
DNNSP = "recob::Wires_simtpc2d_dnnsp_DetSim.obj"
GAUSS = "recob::Wires_simtpc2d_gauss_DetSim.obj"
WIENER = "recob::Wires_simtpc2d_wiener_DetSim.obj"


def pairs(tdir, adir):
    """[(uuid, T_detsim, A_detsim, T_reco1, A_reco1)] from Avinay's detsim JSONs."""
    out = []
    for js in sorted(glob.glob(f"{adir}/detsim/{SUB}/detsim-*.root.json")):
        meta = json.load(open(js))
        g4 = meta["parents"][0]["file_name"]                # g4-gen-<uuid>.root
        uuid = g4[len("g4-gen-"):-len(".root")]
        a_det = js[:-len(".json")]
        a_rec = f"{adir}/reco1/{SUB}/reco1-{os.path.basename(a_det)}"
        t_det = f"{tdir}/detsim/{SUB}/detsim-{g4}"
        t_rec = f"{tdir}/reco1/{SUB}/reco1-detsim-{g4}"
        # cross-check the reco1 parentage on both sides
        for rec, det in ((a_rec, a_det), (t_rec, t_det)):
            p = json.load(open(rec + ".json"))["parents"][0]["file_name"]
            assert p == os.path.basename(det), (rec, p)
        out.append((uuid, t_det, a_det, t_rec, a_rec))
    return out


def sha(b):
    return hashlib.sha256(bytes(b)).hexdigest()


def diffstats(da, db):
    d = da - db
    return float(np.abs(d).max()), int((d != 0).sum()), float(da.sum()), float(db.sum())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--thomas", default=T_DEF)
    ap.add_argument("--abhat", default=A_DEF)
    ap.add_argument("--out", default="rse-manifest.tsv")
    ap.add_argument("--no-decode", action="store_true", help="hashes only")
    a = ap.parse_args()
    cols = ["uuid", "entry", "run", "subrun", "event",
            "dnnsp_reco1_same", "dnnsp_detsim_same", "gauss_same", "wiener_same",
            "dnnsp_maxabs", "dnnsp_ndiff", "dnnsp_sumT", "dnnsp_sumA",
            "gauss_maxabs", "gauss_ndiff", "wiener_maxabs", "wiener_ndiff",
            "passthrough_T", "passthrough_A",
            "T_reco1", "A_reco1", "T_detsim", "A_detsim"]
    rows = []
    t0 = time.time()
    for uuid, t_det, a_det, t_rec, a_rec in pairs(a.thomas, a.abhat):
        trees = {k: uproot.open(p)["Events"] for k, p in
                 (("td", t_det), ("ad", a_det), ("tr", t_rec), ("ar", a_rec))}
        n = {k: t.num_entries for k, t in trees.items()}
        assert len(set(n.values())) == 1, (uuid, n)
        for i in range(n["tr"]):
            rse = {k: decode_rse(t["EventAuxiliary"].basket(i).data) for k, t in trees.items()}
            assert len(set(rse.values())) == 1, (uuid, i, rse)
            run, subrun, event = rse["tr"]
            bts = {("tr", DNNSP): None, ("ar", DNNSP): None}
            for k in ("td", "ad"):
                for br in (DNNSP, GAUSS, WIENER):
                    bts[(k, br)] = None
            for (k, br) in list(bts):
                bts[(k, br)] = bytes(trees[k][br].basket(i).data)
            h = {key: sha(v) for key, v in bts.items()}
            same = {
                "dnnsp_reco1_same": int(h[("tr", DNNSP)] == h[("ar", DNNSP)]),
                "dnnsp_detsim_same": int(h[("td", DNNSP)] == h[("ad", DNNSP)]),
                "gauss_same": int(h[("td", GAUSS)] == h[("ad", GAUSS)]),
                "wiener_same": int(h[("td", WIENER)] == h[("ad", WIENER)]),
                "passthrough_T": int(h[("tr", DNNSP)] == h[("td", DNNSP)]),
                "passthrough_A": int(h[("ar", DNNSP)] == h[("ad", DNNSP)]),
            }
            st = dict(dnnsp_maxabs=0.0, dnnsp_ndiff=0, dnnsp_sumT=float("nan"), dnnsp_sumA=float("nan"),
                      gauss_maxabs=0.0, gauss_ndiff=0, wiener_maxabs=0.0, wiener_ndiff=0)
            if not a.no_decode:
                da, db = dense_wires(bts[("tr", DNNSP)]), dense_wires(bts[("ar", DNNSP)])
                st["dnnsp_maxabs"], st["dnnsp_ndiff"], st["dnnsp_sumT"], st["dnnsp_sumA"] = diffstats(da, db)
                for tag, br in (("gauss", GAUSS), ("wiener", WIENER)):
                    if same[f"{tag}_same"]:
                        continue
                    da, db = dense_wires(bts[("td", br)]), dense_wires(bts[("ad", br)])
                    st[f"{tag}_maxabs"], st[f"{tag}_ndiff"], _, _ = diffstats(da, db)
            row = dict(uuid=uuid, entry=i, run=run, subrun=subrun, event=event, **same, **st,
                       T_reco1=t_rec, A_reco1=a_rec, T_detsim=t_det, A_detsim=a_det)
            rows.append(row)
            flag = "SAME" if same["dnnsp_reco1_same"] else f"DIFF max|A-B|={st['dnnsp_maxabs']:.4g} n={st['dnnsp_ndiff']}"
            print(f"{uuid} entry {i} RSE {run}/{subrun}/{event}: dnnsp {flag}; "
                  f"gauss {'same' if same['gauss_same'] else 'DIFF'} wiener {'same' if same['wiener_same'] else 'DIFF'}; "
                  f"passthrough T={same['passthrough_T']} A={same['passthrough_A']}  [{time.time()-t0:.0f}s]", flush=True)
    with open(a.out, "w") as f:
        f.write("\t".join(cols) + "\n")
        for r in rows:
            f.write("\t".join(str(r[c]) for c in cols) + "\n")
    N = len(rows)
    def cnt(c): return sum(r[c] for r in rows)
    print(f"\n{N} events in {len(set(r['uuid'] for r in rows))} subruns; RSE agree in all four files for every event")
    for c in ("dnnsp_reco1_same", "dnnsp_detsim_same", "gauss_same", "wiener_same", "passthrough_T", "passthrough_A"):
        print(f"  {c:18s} {cnt(c)}/{N}")
    bad = [r for r in rows if not r["dnnsp_reco1_same"]]
    if bad:
        print("  differing dnnsp events (run/subrun/event: max|A-B|, n samples differing, sumT, sumA):")
        for r in bad:
            print(f"    {r['run']}/{r['subrun']}/{r['event']}: {r['dnnsp_maxabs']:.5g} {r['dnnsp_ndiff']} {r['dnnsp_sumT']:.7g} {r['dnnsp_sumA']:.7g}")
    print(f"manifest: {a.out}")


if __name__ == "__main__":
    main()
