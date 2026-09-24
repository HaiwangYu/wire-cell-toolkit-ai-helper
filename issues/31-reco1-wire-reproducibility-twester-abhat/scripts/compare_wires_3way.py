#!/usr/bin/env python3
"""Three-run recob::Wire comparison: Thomas vs Avinay run1 vs Avinay run2.

Pairs the runs event by event through the art provenance JSONs (each Avinay
detsim names Thomas's g4 file as parent), then for every event and every
wire tag (dnnsp, gauss, wiener, all read from the detsim files where WCT
sim+SP runs) records, for each of the three run pairs:

  same      SHA-256 of the decompressed per-event basket equal
  maxabs    largest |A-B| of the decoded dense waveforms
  ndiff     number of samples that differ
  nchan     number of channels with any differing sample
  nroi      channels whose ROI (offset, length) list differs  -> edge flips
  nval      channels with identical ROI structure but different values
            -> rounding differences inside ROIs

and a 3-way class per tag: all_same, A1=A2!=T, T=A2!=A1, T=A1!=A2, all_differ.
Also the per-run non-zero dnnsp sample count and, for run2, the reco1
pass-through check (reco1 dnnsp == detsim dnnsp).

Usage: compare_wires_3way.py [--out rse-manifest-3way.tsv]
Runs on the Aurora UAN with uproot (venv-wire-viewer); ~45 min for 88 events.
"""
import argparse, glob, hashlib, itertools, json, os, sys, time
import numpy as np
import uproot
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wirebytes import decode_rse, decode_wires

RUNS = [  # name, directory, has g4 (reference)
    ("Thomas", "/lus/flare/projects/neutrinoGPU/twester/scratch/sbnd_gen2_full"),
    ("Avinay1", "/lus/flare/projects/neutrinoGPU/abhat/sbnd/thomas-g4-parsl-reproduction-20260921"),
    ("Avinay2", "/lus/flare/projects/neutrinoGPU/abhat/sbnd/thomas-g4-parsl-rerun-20260924"),
]
PAIRS = [("Thomas", "Avinay1"), ("Thomas", "Avinay2"), ("Avinay1", "Avinay2")]
SUB = "000000/000000"
TAGS = {"dnnsp": "recob::Wires_simtpc2d_dnnsp_DetSim.obj",
        "gauss": "recob::Wires_simtpc2d_gauss_DetSim.obj",
        "wiener": "recob::Wires_simtpc2d_wiener_DetSim.obj"}


def pairs():
    """{uuid: {run: (detsim, reco1)}} from the Avinay detsim JSONs."""
    out = {}
    for name, d in RUNS[1:]:
        for js in sorted(glob.glob(f"{d}/detsim/{SUB}/detsim-*.root.json")):
            g4 = json.load(open(js))["parents"][0]["file_name"]
            uuid = g4[len("g4-gen-"):-len(".root")]
            det = js[:-len(".json")]
            rec = f"{d}/reco1/{SUB}/reco1-{os.path.basename(det)}"
            assert json.load(open(rec + ".json"))["parents"][0]["file_name"] == os.path.basename(det)
            out.setdefault(uuid, {})[name] = (det, rec)
            t = RUNS[0][1]
            out[uuid]["Thomas"] = (f"{t}/detsim/{SUB}/detsim-{g4}", f"{t}/reco1/{SUB}/reco1-detsim-{g4}")
    for uuid, m in out.items():
        assert len(m) == 3, (uuid, m.keys())
    return out


class Decoded:
    def __init__(self, raw):
        self.sha = hashlib.sha256(raw).hexdigest()
        self.ch, self.vw, self.nominal, self.rois = decode_wires(raw)
        self.struct = [tuple((o, v.size) for o, v in r) for r in self.rois]
        self.nz = sum(v.size for r in self.rois for _, v in r)

    def dense(self):
        arr = np.zeros((int(self.ch.max()) + 1, self.nominal), dtype=np.float32)
        for c, r in zip(self.ch, self.rois):
            for off, vals in r:
                arr[c, off:off + vals.size] = vals
        return arr


def compare(a, b):
    if a.sha == b.sha:
        return dict(same=1, maxabs=0.0, ndiff=0, nchan=0, nroi=0, nval=0)
    da, db = a.dense(), b.dense()
    d = da - db
    chans = np.unique(np.nonzero(d)[0])
    nroi = sum(1 for c in chans if a.struct[c] != b.struct[c])
    return dict(same=0, maxabs=float(np.abs(d).max()), ndiff=int((d != 0).sum()),
                nchan=int(len(chans)), nroi=nroi, nval=int(len(chans)) - nroi)


def classify(s):  # s = {pair: same}
    ta1, ta2, a12 = s[("Thomas", "Avinay1")], s[("Thomas", "Avinay2")], s[("Avinay1", "Avinay2")]
    if ta1 and ta2:
        return "all_same"
    if a12 and not ta1:
        return "A1=A2!=T"
    if ta2 and not ta1:
        return "T=A2!=A1"
    if ta1 and not ta2:
        return "T=A1!=A2"
    return "all_differ"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="rse-manifest-3way.tsv")
    args = ap.parse_args()
    names = [n for n, _ in RUNS]
    pn = {p: f"{p[0]}-{p[1]}" for p in PAIRS}
    cols = ["uuid", "entry", "run", "subrun", "event"]
    for tag in TAGS:
        cols.append(f"{tag}_class")
    for p in PAIRS:
        for tag in TAGS:
            cols += [f"{pn[p]}_{tag}_{k}" for k in ("same", "maxabs", "ndiff", "nchan", "nroi", "nval")]
    for n in names:
        cols.append(f"{n}_dnnsp_nz")
    cols.append("Avinay2_passthrough")
    for n in names:
        cols += [f"{n}_reco1", f"{n}_detsim"]
    rows = []
    t0 = time.time()
    for uuid, m in sorted(pairs().items()):
        trees = {n: uproot.open(m[n][0])["Events"] for n in names}
        rec2 = uproot.open(m["Avinay2"][1])["Events"]
        nev = {n: t.num_entries for n, t in trees.items()}
        assert len(set(nev.values())) == 1 and rec2.num_entries == nev["Thomas"], (uuid, nev)
        for i in range(nev["Thomas"]):
            rse = {n: decode_rse(t["EventAuxiliary"].basket(i).data) for n, t in trees.items()}
            rse["Avinay2_reco1"] = decode_rse(rec2["EventAuxiliary"].basket(i).data)
            assert len(set(rse.values())) == 1, (uuid, i, rse)
            run, subrun, event = rse["Thomas"]
            row = dict(uuid=uuid, entry=i, run=run, subrun=subrun, event=event)
            dec = {(n, tag): Decoded(bytes(trees[n][br].basket(i).data)) for n in names for tag, br in TAGS.items()}
            for tag in TAGS:
                s = {}
                for p in PAIRS:
                    r = compare(dec[(p[0], tag)], dec[(p[1], tag)])
                    s[p] = r["same"]
                    for k, v in r.items():
                        row[f"{pn[p]}_{tag}_{k}"] = v
                row[f"{tag}_class"] = classify(s)
            for n in names:
                row[f"{n}_dnnsp_nz"] = dec[(n, "dnnsp")].nz
            row["Avinay2_passthrough"] = int(hashlib.sha256(bytes(rec2[TAGS["dnnsp"]].basket(i).data)).hexdigest()
                                            == dec[("Avinay2", "dnnsp")].sha)
            for n in names:
                row[f"{n}_reco1"], row[f"{n}_detsim"] = m[n][1], m[n][0]
            rows.append(row)
            print(f"{uuid} entry {i} RSE {run}/{subrun}/{event}: " +
                  " ".join(f"{tag}={row[f'{tag}_class']}" for tag in TAGS) +
                  f"  [{time.time()-t0:.0f}s]", flush=True)
        del trees, rec2
    with open(args.out, "w") as f:
        f.write("\t".join(cols) + "\n")
        for r in rows:
            f.write("\t".join(str(r[c]) for c in cols) + "\n")
    N = len(rows)
    print(f"\n{N} events in {len(set(r['uuid'] for r in rows))} subruns; RSE agree across all files")
    for tag in TAGS:
        print(f"  {tag}: " + ", ".join(f"{pn[p]} identical {sum(r[f'{pn[p]}_{tag}_same'] for r in rows)}/{N}" for p in PAIRS))
        cls = {}
        for r in rows:
            cls[r[f"{tag}_class"]] = cls.get(r[f"{tag}_class"], 0) + 1
        print(f"     3-way classes: {cls}")
        nroi = sum(r[f"{pn[p]}_{tag}_nroi"] for p in PAIRS for r in rows)
        nval = sum(r[f"{pn[p]}_{tag}_nval"] for p in PAIRS for r in rows)
        print(f"     differing channels over all pairs: ROI structure differs {nroi}, values-only {nval}")
    print(f"  Avinay2 reco1 pass-through: {sum(r['Avinay2_passthrough'] for r in rows)}/{N}")
    print(f"manifest: {args.out}")


if __name__ == "__main__":
    main()
