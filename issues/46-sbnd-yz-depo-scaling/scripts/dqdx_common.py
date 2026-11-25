"""Shared pieces for the issue-46 dQ/dx scripts: SBND wire geometry, the
simulation's space-charge displacement, the YZ map, drift/tick conversion.

Not a script. Imported by dqdx_truth_sp.py, dqdx_fit.py, plot_dqdx.py.
"""
import bz2
import json
import math

import numpy as np

WIRES = "/exp/sbnd/app/users/yuhw/wire-cell-data/sbnd-wires-geometry-v0206.json.bz2"
YZMAP = "/exp/sbnd/app/users/yuhw/wire-cell-data/sbnd/sbnd-yzmap-run2-gen2-bnblight-v1.json.bz2"
SCEMAP = ("/cvmfs/sbnd.opensciencegrid.org/products/sbnd/sbnd_data/v01_43_00/SCEoffsets/"
          "SCEoffsets_SBND_E500_dualmap_CV_voxelTH3.root")
PL, TPC = ["U", "V", "Y"], ["East", "West"]
NCH_TPC = 5638
# sbndcode v10_14_02_03 detsim (wcsimsp_sbnd.fcl, detectorclocks_sbnd.fcl, params.jsonnet)
DRIFT_SPEED = 0.1563     # cm/us
TICK = 0.5               # us
TICK0_TIME = -205.0      # us: TPC readout start w.r.t. trigger (= G4 time 0)
NTICKS = 3427
X_COLL = 202.05          # cm: |x| of the collection plane; tick 0 time is for charge at this plane
FRAME_SCALE = 0.02       # recob::Wire = SP electrons * 0.02 (spsaver / dnnsaver frame_scale)
ACTIVE = dict(x=(-200.0, 200.0), y=(-200.0, 200.0), z=(0.0, 500.0))


def tpc_plane(ch):
    ch = np.asarray(ch)
    tpc, local = np.divmod(ch, NCH_TPC)
    plane = np.where(local < 1984, 0, np.where(local < 3968, 1, 2))
    return tpc, plane


class Geometry:
    """Per (tpc, plane): wire index (ordered along the pitch direction) -> channel,
    and (y, z) -> fractional wire index."""

    def __init__(self, fn=WIRES):
        s = json.load(bz2.open(fn, "rt"))["Store"]
        pts = np.array([[q["Point"][k] for k in "xyz"] for q in s["points"]]) / 10.0  # mm -> cm
        W = [w["Wire"] for w in s["wires"]]
        self.planes = {}
        for face in s["faces"]:
            face = face["Face"]
            tpc = face["ident"]
            for ip, pidx in enumerate(face["planes"]):
                pl = s["planes"][pidx]["Plane"]
                ws = [W[i] for i in pl["wires"]]
                tail = pts[[w["tail"] for w in ws]]
                head = pts[[w["head"] for w in ws]]
                cen = 0.5 * (tail + head)[:, 1:]
                dd = (head - tail)[:, 1:]
                il = np.argmax(np.linalg.norm(dd, axis=1))      # longest wire: best direction
                d = dd[il] / np.linalg.norm(dd[il])
                ph = np.array([-d[1], d[0]])
                if np.dot(cen[-1] - cen[0], ph) < 0:
                    ph = -ph
                pitch = np.dot(cen[-1] - cen[0], ph) / (len(ws) - 1)
                coord = (cen - cen[0]) @ ph / pitch
                if np.abs(coord - np.arange(len(ws))).max() > 0.05:
                    raise RuntimeError(f"non-uniform pitch tpc {tpc} plane {ip}: "
                                       f"{np.abs(coord - np.arange(len(ws))).max()}")
                self.planes[(tpc, ip)] = dict(
                    c0=cen[0], ph=ph, pitch=pitch, wdir=d, x=tail[0, 0],
                    chans=np.array([w["channel"] for w in ws]))

    def wire_coord(self, tpc, plane, y, z):
        p = self.planes[(tpc, plane)]
        return ((np.stack([y, z], -1) - p["c0"]) @ p["ph"]) / p["pitch"]

    def channel(self, tpc, plane, iw):
        ch = self.planes[(tpc, plane)]["chans"]
        iw = np.asarray(iw)
        ok = (iw >= 0) & (iw < len(ch))
        return np.where(ok, ch[np.clip(iw, 0, len(ch) - 1)], -1)


class SCE:
    """larsim IonAndScint + SpaceChargeSBND (Voxelized_TH3, TrueFwd): the position
    the simulation gives a deposit at true position (x, y, z)."""

    def __init__(self, fn=SCEMAP):
        import uproot
        from scipy.interpolate import RegularGridInterpolator as RGI
        f = uproot.open(fn)
        self.h = {}
        for side in "EW":
            for k in "XYZ":
                h = f[f"TrueFwd_Displacement_{k}_{side}"]
                c = [ax.centers() for ax in h.axes]
                self.h[side + k] = (RGI(c, h.values(), bounds_error=False, fill_value=None), c)

    def __call__(self, x, y, z):
        x, y, z = (np.asarray(v, float) for v in (x, y, z))
        xx = np.clip(x, -199.999, 199.999)
        yy = np.clip(y, -199.999, 199.999)
        zz = np.clip(z, 0.001, 499.999)
        out = np.stack([x, y, z], -1).copy()
        # corr = -1 on BOTH sides: SpaceChargeSBND's is2DdriftSimHack is in effect in the
        # G4 job (x_sce = x + Hx in East and West); checked against ionandscint vs
        # ionandscint:priorSCE deposits of an East and a West muon (|diff| < 3e-5 cm).
        for side, m, corr in (("E", xx < 0, -1.0), ("W", xx >= 0, -1.0)):
            if not m.any():
                continue
            res = []
            for k in "XYZ":
                g, c = self.h[side + k]
                p = np.stack([np.clip(v[m], c[i][0], c[i][-1]) for i, v in enumerate((xx, yy, zz))], -1)
                res.append(g(p))
            out[m, 0] = x[m] - corr * res[0]
            out[m, 1] = y[m] + res[1]
            out[m, 2] = z[m] + res[2]
        return out


class YZMap:
    KEYS = ["AnodePlane:apa0", "AnodePlane:apa1"]

    def __init__(self, fn=YZMAP):
        m = json.load(bz2.open(fn, "rt"))
        self.g = {(t, p): np.array(m[k][str(p)], float) for t, k in enumerate(self.KEYS) for p in range(3)}

    def __call__(self, tpc, plane, y, z):
        g = self.g[(tpc, plane)]
        iz = np.clip(np.floor(np.asarray(z) / 5.0).astype(int), 0, 99)
        iy = np.clip(np.floor((np.asarray(y) + 200.0) / 5.0).astype(int), 0, 79)
        return g[iz, iy]


def tick_of(t_ns, x_sce):
    """Nominal SP tick of charge deposited at G4 time t_ns at drift position x_sce."""
    drift_us = (X_COLL - np.abs(x_sce)) / DRIFT_SPEED
    return (np.asarray(t_ns) / 1000.0 + drift_us - TICK0_TIME) / TICK


def robust_stats(v):
    v = np.asarray(v, float)
    v = v[np.isfinite(v)]
    if len(v) == 0:
        return dict(n=0)
    q16, q50, q84, q5, q95 = np.percentile(v, [16, 50, 84, 5, 95])
    return dict(n=int(len(v)), median=float(q50), mean=float(v.mean()), rms=float(v.std()),
                half68=float(0.5 * (q84 - q16)), p16=float(q16), p84=float(q84), p5=float(q5), p95=float(q95),
                median_err=float(1.2533 * 0.5 * (q84 - q16) / math.sqrt(len(v))))
