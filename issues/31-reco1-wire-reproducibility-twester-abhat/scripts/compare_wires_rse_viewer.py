#!/usr/bin/env python3
"""Bokeh server: compare recob::Wire waveforms of the same RSE (run, subrun,
event) between two of the runs Thomas / Avinay run1 / Avinay run2 (A and B are
chosen with two drop-downs; default A = Thomas, B = Avinay1).

Derived from wcp-porting-validation/sbnd/standalone-sample/w-gap/
compare_wires_viewer.py, but reads the art files with uproot + wirebytes.py
(no ROOT dictionaries, so it runs on the Aurora UAN) and navigates by RSE:

  * "< prev" / "next >" buttons step through the paired event list;
  * an RSE text box ("1/16/6", "1 16 6" or "1:16:6") jumps to that event;
  * a drop-down lists every RSE with the 3-way class of the current product
    (all_same, A1=A2!=T, T=A2!=A1, T=A1!=A2, all_differ);
  * "A run" / "B run" drop-downs pick which two runs the panels compare.
  * product: dnnsp from reco1 (what reco2 consumes), or dnnsp/gauss/wiener
    from detsim (where WCT sim+SP actually runs).

Panels: A, B and A-B (channel on X, tick on Y; bipolar colormap; every
pan/zoom re-renders with sign-preserving max-|v| pooling); tap a channel for
the 1D waveforms A, B and A-B; table of the largest |A-B| in the selected
APA/plane (click a row to inspect that channel).

The event list comes from rse-manifest-3way.tsv (compare_wires_3way.py;
runs Thomas, Avinay1, Avinay2) or, if that is missing, rse-manifest.tsv
(compare_wires_hash.py; runs T, A), both looked up next to this scripts/
folder; with --thomas/--abhat the two-run pairing is rebuilt from the run
directories instead.

Launched by serve-viewer.sh.  Standalone data-layer smoke test:
    python compare_wires_rse_viewer.py [--manifest F] [--rse 1/16/6] [--product dnnsp_reco1] [--run-a Thomas --run-b Avinay2]
"""
import argparse
import csv
import os
import sys

import numpy as np
import uproot

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wirebytes import decode_rse, dense_wires  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
_M3 = os.path.join(os.path.dirname(HERE), "rse-manifest-3way.tsv")
_M2 = os.path.join(os.path.dirname(HERE), "rse-manifest.tsv")
DEFAULT_MANIFEST = _M3 if os.path.exists(_M3) else _M2

PRODUCTS = {
    # key: (label, stage, tag, branch); the file column is f"{run}_{stage}"
    "dnnsp_reco1": ("dnnsp (reco1)", "reco1", "dnnsp", "recob::Wires_simtpc2d_dnnsp_DetSim.obj"),
    "dnnsp_detsim": ("dnnsp (detsim)", "detsim", "dnnsp", "recob::Wires_simtpc2d_dnnsp_DetSim.obj"),
    "gauss_detsim": ("gauss (detsim)", "detsim", "gauss", "recob::Wires_simtpc2d_gauss_DetSim.obj"),
    "wiener_detsim": ("wiener (detsim)", "detsim", "wiener", "recob::Wires_simtpc2d_wiener_DetSim.obj"),
}
# display names of the run prefixes used in the manifests
RUN_LABEL = {"Thomas": "Thomas", "Avinay1": "Avinay run1", "Avinay2": "Avinay run2",
             "T": "Thomas", "A": "Avinay run1"}


def run_names(rows):
    """Run prefixes present in the manifest (columns '<run>_reco1'), manifest order."""
    return [k[:-len("_reco1")] for k in rows[0].keys() if k.endswith("_reco1")]
MAX_IMG_W = 800
MAX_IMG_H = 600
NTOP = 5

# SBND channel layout: per APA u(1984) + v(1984) + w(1670) = 5638 channels.
NCH_U, NCH_V, NCH_W = 1984, 1984, 1670
NCH_APA = NCH_U + NCH_V + NCH_W


def region_channels(apa, plane):
    if apa == "all":
        return 0, 2 * NCH_APA
    base = int(apa) * NCH_APA
    lo, hi = {"all": (0, NCH_APA), "u": (0, NCH_U), "v": (NCH_U, NCH_U + NCH_V),
              "w": (NCH_U + NCH_V, NCH_APA)}[plane]
    return base + lo, base + hi


# ---------------------------------------------------------------------------
# event list
# ---------------------------------------------------------------------------
def parse_rse(text):
    """'1/16/6', '1 16 6', '1:16:6', '1,16,6' -> (1, 16, 6)."""
    for sep in "/:,":
        text = text.replace(sep, " ")
    parts = text.split()
    if len(parts) != 3:
        raise ValueError(f"need run subrun event, got {text!r}")
    return tuple(int(p) for p in parts)


def load_manifest(path):
    """rows of rse-manifest.tsv (dicts) sorted by (run, subrun, event)."""
    with open(path) as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    for r in rows:
        for k in ("entry", "run", "subrun", "event"):
            r[k] = int(r[k])
    rows.sort(key=lambda r: (r["run"], r["subrun"], r["event"]))
    return rows


def build_from_dirs(tdir, adir):
    """Rebuild the event list from two run directories (no verdicts); runs T and A."""
    from compare_wires_hash import pairs
    rows = []
    for uuid, t_det, a_det, t_rec, a_rec in pairs(tdir, adir):
        t = uproot.open(t_rec)["Events"]
        for i in range(t.num_entries):
            run, subrun, event = decode_rse(t["EventAuxiliary"].basket(i).data)
            rows.append(dict(uuid=uuid, entry=i, run=run, subrun=subrun, event=event,
                             T_reco1=t_rec, T_detsim=t_det, A_reco1=a_rec, A_detsim=a_det))
    rows.sort(key=lambda r: (r["run"], r["subrun"], r["event"]))
    return rows


def rse_label(r):
    return f"{r['run']}/{r['subrun']}/{r['event']}"


def verdict(r, product, run_a, run_b):
    """'identical' / 'DIFFERENT' for the (run_a, run_b) pair from the manifest, '?' if absent."""
    tag = PRODUCTS[product][2]
    if run_a == run_b:
        return "identical"
    cands = [f"{run_a}-{run_b}_{tag}_same", f"{run_b}-{run_a}_{tag}_same"]      # 3-way manifest
    if {run_a, run_b} == {"T", "A"}:                                           # 2-run manifest
        cands += [{"dnnsp_reco1": "dnnsp_reco1_same", "dnnsp_detsim": "dnnsp_detsim_same",
                   "gauss_detsim": "gauss_same", "wiener_detsim": "wiener_same"}[product]]
    for c in cands:
        v = r.get(c)
        if v not in (None, ""):
            return "identical" if int(v) else "DIFFERENT"
    return "?"


def three_way(r, product):
    """3-way class of the product's tag (3-way manifest), else the 2-run verdict."""
    tag = PRODUCTS[product][2]
    v = r.get(f"{tag}_class")
    if v not in (None, ""):
        return v
    return verdict(r, product, "T", "A")


# ---------------------------------------------------------------------------
# data layer
# ---------------------------------------------------------------------------
class Trees:
    """Open uproot trees, cached by path; dense arrays cached per (path, entry, branch)."""

    def __init__(self):
        self._trees = {}
        self._cache = {}

    def tree(self, path):
        if path not in self._trees:
            self._trees[path] = uproot.open(path)["Events"]
        return self._trees[path]

    def dense(self, path, entry, branch):
        key = (path, entry, branch)
        if key not in self._cache:
            t = self.tree(path)
            self._cache = {key: dense_wires(t[branch].basket(entry).data)}
        return self._cache[key]

    def rse(self, path, entry):
        return decode_rse(self.tree(path)["EventAuxiliary"].basket(entry).data)


def aligned(a, b):
    nch = max(a.shape[0], b.shape[0])
    nt = max(a.shape[1], b.shape[1])
    if a.shape != (nch, nt):
        tmp = np.zeros((nch, nt), dtype=a.dtype); tmp[: a.shape[0], : a.shape[1]] = a; a = tmp
    if b.shape != (nch, nt):
        tmp = np.zeros((nch, nt), dtype=b.dtype); tmp[: b.shape[0], : b.shape[1]] = b; b = tmp
    return a, b


def maxpool2d_signed(arr, max_h, max_w):
    h, w = arr.shape
    fy = max(1, int(np.ceil(h / max_h)))
    fx = max(1, int(np.ceil(w / max_w)))
    if fy == 1 and fx == 1:
        return arr, 1, 1
    ph = (-h) % fy
    pw = (-w) % fx
    if ph or pw:
        arr = np.pad(arr, ((0, ph), (0, pw)), constant_values=0)
    H, W = arr.shape
    blk = arr.reshape(H // fy, fy, W // fx, fx)
    bmax = blk.max(axis=(1, 3))
    bmin = blk.min(axis=(1, 3))
    return np.where(bmax > -bmin, bmax, bmin), fy, fx


def top_diffs(diff, n=NTOP):
    flat = np.argpartition(np.abs(diff).ravel(), -n)[-n:]
    out = [(float(abs(diff.ravel()[i])), int(i // diff.shape[1]), int(i % diff.shape[1])) for i in flat]
    return sorted(out, reverse=True)


def bipolar_palette(n=256):
    try:
        import matplotlib
        from matplotlib.colors import to_hex
        cmap = matplotlib.colormaps["RdBu_r"]
        return [to_hex(cmap(i / (n - 1))) for i in range(n)]
    except Exception:
        out = []
        for i in range(n):
            t = i / (n - 1)
            if t < 0.5:
                s = t * 2; r, g, b = int(255 * s), int(255 * s), 255
            else:
                s = (t - 0.5) * 2; r, g, b = 255, int(255 * (1 - s)), int(255 * (1 - s))
            out.append(f"#{r:02x}{g:02x}{b:02x}")
        return out


def parse_args(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default=DEFAULT_MANIFEST)
    ap.add_argument("--thomas", help="rebuild the event list from this run dir (with --abhat)")
    ap.add_argument("--abhat")
    ap.add_argument("--rse", default=None, help="start at this RSE, e.g. 1/16/6")
    ap.add_argument("--product", default="dnnsp_reco1", choices=list(PRODUCTS))
    ap.add_argument("--run-a", default=None, help="run prefix for A (default: first run in the manifest)")
    ap.add_argument("--run-b", default=None, help="run prefix for B (default: second run)")
    return ap.parse_args(argv)


def pick_runs(args, rows):
    names = run_names(rows)
    a = args.run_a or names[0]
    b = args.run_b or (names[1] if len(names) > 1 else names[0])
    for x in (a, b):
        if x not in names:
            sys.exit(f"run {x!r} not in manifest; have {names}")
    return names, a, b


def event_rows(args):
    if args.thomas and args.abhat:
        return build_from_dirs(args.thomas, args.abhat)
    if not os.path.exists(args.manifest):
        sys.exit(f"no manifest {args.manifest}; run compare_wires_hash.py or pass --thomas/--abhat")
    return load_manifest(args.manifest)


# ---------------------------------------------------------------------------
# Bokeh app
# ---------------------------------------------------------------------------
def run_app():
    from bokeh.io import curdoc
    from bokeh.layouts import column, row
    from bokeh.models import (Button, ColorBar, ColumnDataSource, DataTable, Div,
                              LinearColorMapper, NumberFormatter, Range1d, Select,
                              TableColumn, TextInput)
    from bokeh.events import Tap
    from bokeh.plotting import figure

    args = parse_args(sys.argv[1:])
    rows = event_rows(args)
    names, run_a0, run_b0 = pick_runs(args, rows)
    trees = Trees()
    state = {"idx": 0, "product": args.product, "a": None, "b": None, "diff": None, "ch": -1,
             "run_a": run_a0, "run_b": run_b0}
    if args.rse:
        want = parse_rse(args.rse)
        for k, r in enumerate(rows):
            if (r["run"], r["subrun"], r["event"]) == want:
                state["idx"] = k

    # -- widgets ------------------------------------------------------------
    def opt_label(r):
        return f"{rse_label(r)}  [{three_way(r, state['product'])}]  {r['uuid'][:4]} e{r['entry']}"

    sel_rse = Select(title="RSE (run/subrun/event) [3-way class of product]",
                     value=str(state["idx"]),
                     options=[(str(k), opt_label(r)) for k, r in enumerate(rows)], width=380)
    run_opts = [(n, RUN_LABEL.get(n, n)) for n in names]
    sel_run_a = Select(title="A run", value=state["run_a"], options=run_opts, width=130)
    sel_run_b = Select(title="B run", value=state["run_b"], options=run_opts, width=130)
    in_rse = TextInput(title="go to RSE (run/subrun/event)", value=rse_label(rows[state["idx"]]), width=180)
    bt_go = Button(label="Go", button_type="primary", width=60)
    bt_prev = Button(label="< prev", width=80)
    bt_next = Button(label="next >", width=80)
    sel_prod = Select(title="product", value=state["product"],
                      options=[(k, v[0]) for k, v in PRODUCTS.items()], width=150)
    sel_apa = Select(title="APA", value="all", options=["all", "0", "1"], width=80)
    sel_plane = Select(title="plane", value="all", options=["all", "u", "v", "w"], width=80)
    in_cmin_ab = TextInput(title="A/B cmap min", value="-100", placeholder="auto", width=100)
    in_cmax_ab = TextInput(title="A/B cmap max", value="100", placeholder="auto", width=100)
    in_cmin_d = TextInput(title="diff cmap min", value="-20", placeholder="auto", width=100)
    in_cmax_d = TextInput(title="diff cmap max", value="20", placeholder="auto", width=100)
    sel_dmode = Select(title="diff mode", value="abs",
                       options=[("abs", "A-B"), ("rel", "(A-B)/max(|A|,|B|)")], width=150)
    in_deps = TextInput(title="rel eps", value="1", width=80)
    info = Div(text="loading ...", width=1400)
    topdiv = Div(text="", width=420)
    top_src = ColumnDataSource(data=dict(v=[], c=[], t=[]))
    top_table = DataTable(
        source=top_src, width=420, height=200, index_position=None,
        columns=[TableColumn(field="v", title="|A-B|", formatter=NumberFormatter(format="0.000")),
                 TableColumn(field="c", title="channel"),
                 TableColumn(field="t", title="tick")])

    # -- three linked 2D panels ---------------------------------------------
    PAL = bipolar_palette()
    PANEL_W, PANEL_H = 620, 540
    figs, img_srcs, mappers = {}, {}, {}

    def make_panel(key, title, shared=None):
        kw = dict(width=PANEL_W, height=PANEL_H, x_axis_label="channel", y_axis_label="time tick",
                  tools="pan,box_zoom,wheel_zoom,reset,save", active_scroll="wheel_zoom", title=title)
        if shared is not None:
            kw["x_range"], kw["y_range"] = shared.x_range, shared.y_range
        else:
            kw["x_range"], kw["y_range"] = Range1d(0, 1), Range1d(0, 1)
        fig = figure(**kw)
        mapper = LinearColorMapper(palette=PAL, low=-1, high=1)
        src = ColumnDataSource(data=dict(image=[np.zeros((2, 2), dtype=np.float32)],
                                         x=[0], y=[0], dw=[1], dh=[1]))
        fig.image(image="image", x="x", y="y", dw="dw", dh="dh", color_mapper=mapper, source=src)
        fig.add_layout(ColorBar(color_mapper=mapper, width=10), "right")
        figs[key], img_srcs[key], mappers[key] = fig, src, mapper
        return fig

    fig_a = make_panel("a", "A")
    fig_b = make_panel("b", "B", shared=fig_a)
    fig_d = make_panel("d", "A - B", shared=fig_a)

    # -- 1D panels ----------------------------------------------------------
    cap1d = Div(text="channel waveform (tap a 2D panel or a table row)", width=700)
    fig1d = figure(width=700, height=300, x_axis_label="time tick", y_axis_label="signal",
                   tools="pan,box_zoom,wheel_zoom,reset,save")
    src_a = ColumnDataSource(data=dict(x=[], y=[]))
    src_b = ColumnDataSource(data=dict(x=[], y=[]))
    fig1d.line("x", "y", source=src_a, color="#2ca02c", legend_label="A", line_width=1.2)
    fig1d.scatter("x", "y", source=src_b, color="#d62728", legend_label="B", size=3, marker="circle")
    fig1d.legend.click_policy = "hide"
    figdf = figure(title="A - B", width=700, height=260, x_axis_label="time tick", y_axis_label="A - B",
                   x_range=fig1d.x_range, tools="pan,box_zoom,wheel_zoom,reset,save")
    src_d = ColumnDataSource(data=dict(x=[], y=[]))
    figdf.line("x", "y", source=src_d, color="#d62728", line_width=1.2)

    # -- rendering ----------------------------------------------------------
    render_pending = {"on": False}

    def view_window():
        nch, nt = state["diff"].shape
        xr, yr = fig_a.x_range, fig_a.y_range
        c0 = int(max(0, np.floor(xr.start if xr.start is not None else 0)))
        c1 = int(min(nch, np.ceil(xr.end if xr.end is not None else nch)))
        t0 = int(max(0, np.floor(yr.start if yr.start is not None else 0)))
        t1 = int(min(nt, np.ceil(yr.end if yr.end is not None else nt)))
        return c0, c1, t0, t1

    def parse_or(w, default):
        s = w.value.strip()
        if not s:
            return default
        try:
            return float(s)
        except ValueError:
            return default

    def render_view():
        render_pending["on"] = False
        if state["diff"] is None:
            return
        c0, c1, t0, t1 = view_window()
        if c1 - c0 < 2 or t1 - t0 < 2:
            return
        suba = state["a"][c0:c1, t0:t1]
        subb = state["b"][c0:c1, t0:t1]
        if sel_dmode.value == "rel":
            eps = max(parse_or(in_deps, 1.0), 1e-9)
            subd = (suba - subb) / (np.maximum(np.abs(suba), np.abs(subb)) + eps)
            fig_d.title.text = "(A - B) / (max(|A|,|B|) + %.4g)" % eps
        else:
            subd = suba - subb
            fig_d.title.text = "A - B"
        imgs = {}
        for key, arr in (("a", suba), ("b", subb), ("d", subd)):
            img, _, _ = maxpool2d_signed(arr, MAX_IMG_W, MAX_IMG_H)
            imgs[key] = img.T.astype(np.float32)
        ab_lo = min(float(imgs["a"].min()), float(imgs["b"].min()))
        ab_hi = max(float(imgs["a"].max()), float(imgs["b"].max()))
        vlo, vhi = parse_or(in_cmin_ab, 0.9 * ab_lo), parse_or(in_cmax_ab, 0.9 * ab_hi)
        if vhi <= vlo:
            vhi = vlo + 1e-9
        mappers["a"].low, mappers["a"].high = vlo, vhi
        mappers["b"].low, mappers["b"].high = vlo, vhi
        dlo = parse_or(in_cmin_d, 0.9 * float(imgs["d"].min()))
        dhi = parse_or(in_cmax_d, 0.9 * float(imgs["d"].max()))
        if dhi <= dlo:
            dhi = dlo + 1e-9
        mappers["d"].low, mappers["d"].high = dlo, dhi
        for key in ("a", "b", "d"):
            img_srcs[key].data = dict(image=[imgs[key]], x=[c0], y=[t0], dw=[c1 - c0], dh=[t1 - t0])

    def schedule_render(attr, old, new):
        if render_pending["on"]:
            return
        render_pending["on"] = True
        curdoc().add_timeout_callback(render_view, 150)

    for rng in (fig_a.x_range, fig_a.y_range):
        rng.on_change("start", schedule_render)
        rng.on_change("end", schedule_render)

    def update_1d_caption():
        ch = state["ch"]
        a, b = state["a"], state["b"]
        if a is None or ch < 0 or ch >= a.shape[0]:
            return
        nt = a.shape[1]
        xr = fig1d.x_range
        t0 = 0 if xr.start is None else int(max(0, np.floor(xr.start)))
        t1 = nt if xr.end is None else int(min(nt, np.ceil(xr.end)))
        if t1 <= t0:
            return
        d = a[ch] - b[ch]
        k = int(np.argmax(np.abs(d)))
        qa, qb = float(a[ch, t0:t1].sum()), float(b[ch, t0:t1].sum())
        cap1d.text = (f"<b>channel {ch}</b>: max|A-B| = {abs(d[k]):.4g} @ tick {k}, "
                      f"{int((d != 0).sum())} samples differ &nbsp; Q[{t0},{t1}) A={qa:.5g} B={qb:.5g} "
                      f"A-B={qa - qb:.4g}")

    charge_pending = {"on": False}

    def charge_recalc():
        charge_pending["on"] = False
        update_1d_caption()

    def on_1d_zoom(attr, old, new):
        if charge_pending["on"]:
            return
        charge_pending["on"] = True
        curdoc().add_timeout_callback(charge_recalc, 250)

    fig1d.x_range.on_change("start", on_1d_zoom)
    fig1d.x_range.on_change("end", on_1d_zoom)

    def show_channel(ch):
        a, b = state["a"], state["b"]
        if a is None or ch < 0 or ch >= a.shape[0]:
            return
        state["ch"] = ch
        x = np.arange(a.shape[1])
        src_a.data = dict(x=x, y=a[ch])
        src_b.data = dict(x=x, y=b[ch])
        src_d.data = dict(x=x, y=a[ch] - b[ch])
        update_1d_caption()

    def on_tap(event):
        show_channel(int(round(event.x)))

    for f in (fig_a, fig_b, fig_d):
        f.on_event(Tap, on_tap)

    def update_top_table():
        if state["diff"] is None:
            return []
        lo, hi = region_channels(sel_apa.value, sel_plane.value)
        hi = min(hi, state["diff"].shape[0])
        sub = state["diff"][lo:hi]
        tops = [(v, c + lo, t) for v, c, t in top_diffs(sub)]
        region = f"APA {sel_apa.value} / plane {sel_plane.value}"
        ndiff = int((sub != 0).sum())
        topdiv.text = (f"<b>largest |A-B|</b> ({region}; {ndiff} samples differ) "
                       f"&mdash; click a row to inspect")
        top_src.selected.indices = []
        top_src.data = dict(v=[v for v, c, t in tops], c=[c for v, c, t in tops], t=[t for v, c, t in tops])
        r = rows[state["idx"]]
        print(f"[RSE {rse_label(r)} {state['product']} A={state['run_a']} B={state['run_b']} {region}] {ndiff} samples differ; largest |A-B|: "
              + ", ".join(f"{v:.5g}@(ch {c}, tick {t})" for v, c, t in tops), flush=True)
        return tops

    def apply_region():
        if state["diff"] is None:
            return
        lo, hi = region_channels(sel_apa.value, sel_plane.value)
        nch, nt = state["diff"].shape
        hi = min(hi, nch)
        fig_a.x_range.start, fig_a.x_range.end = lo, hi
        fig_a.y_range.start, fig_a.y_range.end = 0, nt
        fig_a.x_range.reset_start, fig_a.x_range.reset_end = lo, hi
        fig_a.y_range.reset_start, fig_a.y_range.reset_end = 0, nt

    def on_region(attr, old, new):
        apply_region()
        update_top_table()

    def on_top_select(attr, old, new):
        if not new:
            return
        chans = top_src.data["c"]
        if 0 <= new[0] < len(chans):
            show_channel(int(chans[new[0]]))

    top_src.selected.on_change("indices", on_top_select)
    sel_apa.on_change("value", on_region)
    sel_plane.on_change("value", on_region)
    for w in (in_cmin_ab, in_cmax_ab, in_cmin_d, in_cmax_d, in_deps):
        w.on_change("value", schedule_render)
    sel_dmode.on_change("value", schedule_render)

    # -- event loading ------------------------------------------------------
    def load_event():
        r = rows[state["idx"]]
        label, stage, tag, branch = PRODUCTS[state["product"]]
        col_a, col_b = f"{state['run_a']}_{stage}", f"{state['run_b']}_{stage}"
        la, lb = RUN_LABEL.get(state["run_a"], state["run_a"]), RUN_LABEL.get(state["run_b"], state["run_b"])
        try:
            a = trees.dense(r[col_a], r["entry"], branch)
            b = trees.dense(r[col_b], r["entry"], branch)
            rse_a = trees.rse(r[col_a], r["entry"])
            rse_b = trees.rse(r[col_b], r["entry"])
        except Exception as e:
            info.text = f"<b>error:</b> {e}"
            return
        a, b = aligned(a, b)
        state["a"], state["b"], state["diff"] = a, b, a - b
        apply_region()
        render_view()
        tops = update_top_table()
        same = "byte-identical" if not np.any(state["diff"]) else "DIFFERENT"
        v = verdict(r, state["product"], state["run_a"], state["run_b"])
        nch, nt = a.shape
        info.text = (f"<b>RSE {rse_label(r)}</b> (event {state['idx'] + 1}/{len(rows)}; g4 {r['uuid']}, "
                     f"entry {r['entry']}; A reads {rse_a[0]}/{rse_a[1]}/{rse_a[2]}, "
                     f"B reads {rse_b[0]}/{rse_b[1]}/{rse_b[2]}) &nbsp; product <b>{label}</b>, "
                     f"A = <b>{la}</b>, B = <b>{lb}</b>: <b>{same}</b> now, manifest says {v}; "
                     f"3-way class {three_way(r, state['product'])}; "
                     f"sum A={a.sum():.6g} B={b.sum():.6g}; shape {nch} ch x {nt} ticks<br>"
                     f"A: {r[col_a]}<br>B: {r[col_b]}")
        fig_a.title.text = f"A: {la} {label}"
        fig_b.title.text = f"B: {lb} {label}"
        fig_d.title.text = "A - B"
        in_rse.value = rse_label(r)
        sel_rse.value = str(state["idx"])
        if tops:
            show_channel(tops[0][1])

    def step(dn):
        state["idx"] = int(np.clip(state["idx"] + dn, 0, len(rows) - 1))
        load_event()

    def go():
        try:
            want = parse_rse(in_rse.value)
        except ValueError as e:
            info.text = f"<b>error:</b> {e}"
            return
        for k, r in enumerate(rows):
            if (r["run"], r["subrun"], r["event"]) == want:
                state["idx"] = k
                load_event()
                return
        info.text = f"<b>error:</b> RSE {want[0]}/{want[1]}/{want[2]} is not in the event list"

    def on_sel_rse(attr, old, new):
        if int(new) != state["idx"]:
            state["idx"] = int(new)
            load_event()

    def on_product(attr, old, new):
        state["product"] = new
        sel_rse.options = [(str(k), opt_label(r)) for k, r in enumerate(rows)]
        load_event()

    def on_run(attr, old, new):
        state["run_a"], state["run_b"] = sel_run_a.value, sel_run_b.value
        load_event()

    bt_go.on_click(go)
    bt_prev.on_click(lambda: step(-1))
    bt_next.on_click(lambda: step(+1))
    sel_rse.on_change("value", on_sel_rse)
    sel_prod.on_change("value", on_product)
    sel_run_a.on_change("value", on_run)
    sel_run_b.on_change("value", on_run)

    controls = column(
        row(bt_prev, bt_next, in_rse, bt_go, sel_rse, sel_run_a, sel_run_b, sel_prod, sel_apa, sel_plane),
        row(in_cmin_ab, in_cmax_ab, in_cmin_d, in_cmax_d, sel_dmode, in_deps),
        info)
    layout = column(controls, row(fig_a, fig_b, fig_d),
                    row(column(cap1d, fig1d, figdf), column(topdiv, top_table)))
    curdoc().add_root(layout)
    curdoc().title = "recob::Wire Thomas / Avinay1 / Avinay2 by RSE"
    load_event()


# ---------------------------------------------------------------------------
def main_cli():
    """Data-layer smoke test: load one RSE and print the largest diffs."""
    args = parse_args(sys.argv[1:])
    rows = event_rows(args)
    print(f"{len(rows)} events; first {rse_label(rows[0])} last {rse_label(rows[-1])}")
    idx = 0
    if args.rse:
        want = parse_rse(args.rse)
        idx = [k for k, r in enumerate(rows) if (r["run"], r["subrun"], r["event"]) == want][0]
    r = rows[idx]
    names, run_a, run_b = pick_runs(args, rows)
    label, stage, tag, branch = PRODUCTS[args.product]
    col_a, col_b = f"{run_a}_{stage}", f"{run_b}_{stage}"
    trees = Trees()
    a, b = aligned(trees.dense(r[col_a], r["entry"], branch), trees.dense(r[col_b], r["entry"], branch))
    print(f"RSE {rse_label(r)} {label} A={run_a} B={run_b}: shape {a.shape}; A sum {a.sum():.6g} B sum {b.sum():.6g}; "
          f"{int((a != b).sum())} samples differ; manifest verdict {verdict(r, args.product, run_a, run_b)}; "
          f"3-way {three_way(r, args.product)}")
    for v, c, t in top_diffs(a - b):
        print(f"  |A-B| {v:.5g} @ channel {c} tick {t}")


if __name__.startswith("bokeh_app"):
    run_app()
elif __name__ == "__main__":
    main_cli()
