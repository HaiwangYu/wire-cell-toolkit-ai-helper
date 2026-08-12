#!/usr/bin/env python3
"""Build the two 6-column comparison lists for compare_wires_viewer.

One row per campaign event:  A = PRODUCTION, B = OUR validation re-run, both
tagged dnnsp -- so the viewer's A-B panel shows production minus ours, i.e. the
charge the four fixes changed.

The event indices differ per side on purpose: production files hold a whole run
segment (our event sits at some entry N), while each validation output holds a
single event at entry 0.  That is exactly why the viewer needed independent
event A/B.

    python3 campaign-cmplists.py       -> <campaign>/cmp-mc-list.txt
                                          <campaign>/cmp-data-list.txt
"""
import glob, os
import ROOT

C = ("/exp/sbnd/data/users/yuhw/wire-cell-toolkit-ai-helper/issues/"
     "10-prolong-dashed-track-w/data/validation-20260812")
PROD = {
    "mc": ("/pnfs/sbn/data_add/sbn_nd/poms_production/mc/MCP2025C_FallProduction/"
           "v10_14_02/prodgenie_corsika_proton_rockbox0p1_sbnd/CV/reco1/a5/"
           "gen_g4_detsim_reco1-a5f42e7e-aae1-243a-11b2-fad9417d6ce0.root"),
    "data": ("/pnfs/sbn/data_add/sbn_nd/poms_production/data/MCP2025C/v10_14_02/"
             "Fall25-Run1_BNB_Dev_bnblight/reco1/bnblight/fe/"
             "data_filtered_decoded_reco1-fe6033f3-07a0-4971-cea5-16ce59269fba.root"),
}
TAG = "dnnsp"


def rse_index(path):
    """(run, subrun, event) -> entry, for a production file."""
    f = ROOT.TFile.Open(path)
    t = f.Get("Events")
    out = {}
    for i in range(t.GetEntries()):
        t.GetEntry(i)
        a = t.EventAuxiliary
        out[(a.run(), a.subRun(), a.event())] = i
    f.Close()
    return out


def main():
    for leg, prod in PROD.items():
        idx = rse_index(prod)
        rows, missing = [], []
        for spp in sorted(glob.glob(os.path.join(C, leg, "*", "sp.root"))):
            lbl = os.path.basename(os.path.dirname(spp))
            rse = tuple(int(x) for x in lbl.split("-"))
            if rse not in idx:
                missing.append(lbl)
                continue
            rows.append((prod, spp, idx[rse], 0, TAG, TAG, lbl))
        out = os.path.join(C, f"cmp-{leg}-list.txt")
        with open(out, "w") as fh:
            fh.write(f"# issue #10 campaign, {leg} leg: PRODUCTION (A) vs OUR re-run (B).\n")
            fh.write("# columns: fileA fileB eventA eventB tagA tagB   # label\n")
            fh.write("# A = production reco1 (pre-fix); B = validation re-run with all\n")
            fh.write("# four fixes.  The A-B panel is therefore production minus ours:\n")
            fh.write("# negative where the fixes recovered charge.\n")
            for r in rows:
                fh.write("%s %s %d %d %s %s  # %s\n" % r)
        print(f"{out}: {len(rows)} rows"
              + (f"  (MISSING from production: {missing})" if missing else ""))


main()
