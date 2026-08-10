#!/usr/bin/env python3
"""Browse a WCT Magnify file: 2D channel-vs-tick per SP stage + a 1D overlay of
ALL stages for one channel (Bokeh server).

A Magnify file holds TH2F named  h<plane><stage><apa>  (x = ABSOLUTE channel
number, y = tick), e.g. `hw_tight_lf1`.  Stages written by the SBND sim+SP dump:

    orig raw tight_lf loose_lf decon_charge break_roi_1st break_roi_2nd
    shrink_roi extend_roi cleanup_roi gauss wiener        (+ dnnsp if enabled)

Layout
  top    : file path + Load
  left   : 2D image (channel on X, tick on Y) for the selected stage/plane/APA.
           Colour scale is symmetric (+/-|max|), defaulting to 60% of the
           stage's largest |value|, and is editable.
           Re-rendered server-side on zoom with sign-preserving max-|v| pooling
           so single-tick spikes never vanish.  Click it to pick a channel.
  right  : 1D waveforms of that channel for EVERY stage.  Click a legend entry
           to hide/show a curve.  "normalize" rescales all curves to a common
           range (stages differ ~50x: orig/raw are ADC ~1e3, decon/ROI ~1e4-1e5).

Launched by serve-magnify-viewer.sh.  Needs the sbndcode/ROOT environment.
"""

import os
import numpy as np
import ROOT

# Pipeline order for the legend; anything unknown is appended alphabetically.
STAGE_ORDER = ["orig", "raw", "tight_lf", "loose_lf", "decon_charge",
               "break_roi_1st", "break_roi_2nd", "shrink_roi", "extend_roi",
               "cleanup_roi", "gauss", "wiener", "dnnsp"]
PLANES = ["u", "v", "w"]
MAX_IMG_W = 900     # rendered resolution budget, tick axis
MAX_IMG_H = 700     # channel axis
DEFAULT_FILE = os.environ.get("MAGNIFY_FILE", "")


# ---------------------------------------------------------------------------
# data layer
# ---------------------------------------------------------------------------
class MagFile:
    """Lazy reader for one Magnify ROOT file."""

    def __init__(self, path):
        self.path = path
        self.f = ROOT.TFile.Open(path)
        if not self.f or self.f.IsZombie():
            raise IOError("cannot open %s" % path)
        self.index = {}                      # (plane, stage, apa) -> hist name
        for k in self.f.GetListOfKeys():
            n = k.GetName()
            if not n.startswith("h"):
                continue
            body = n[1:]
            if len(body) < 4 or body[0] not in PLANES or body[1] != "_":
                continue
            plane, rest = body[0], body[2:]
            if not rest[-1].isdigit():
                continue
            self.index[(plane, rest[:-1], int(rest[-1]))] = n
        self._cache = {}                     # (plane, stage, apa) -> (arr, ch0, t0)

    # -- introspection ------------------------------------------------------
    def stages(self, plane=None, apa=None):
        got = {s for (p, s, a) in self.index
               if (plane is None or p == plane) and (apa is None or a == apa)}
        known = [s for s in STAGE_ORDER if s in got]
        return known + sorted(got - set(known))

    def planes(self, apa=None):
        return [p for p in PLANES
                if any(k[0] == p and (apa is None or k[2] == apa) for k in self.index)]

    def apas(self):
        return sorted({a for (_, _, a) in self.index})

    def default_stage(self, plane, apa):
        """dnnsp if present, else gauss, else the first available."""
        av = self.stages(plane, apa)
        for want in ("dnnsp", "gauss"):
            if want in av:
                return want
        return av[0] if av else ""

    # -- payload ------------------------------------------------------------
    def array(self, plane, stage, apa):
        """(arr[tick, channel], first_channel, first_tick) or None."""
        key = (plane, stage, apa)
        if key in self._cache:
            return self._cache[key]
        name = self.index.get(key)
        if not name:
            return None
        h = self.f.Get(name)
        if not h:
            return None
        nx, ny = h.GetNbinsX(), h.GetNbinsY()
        dtype = np.float64 if h.ClassName().endswith("D") else np.float32
        # NB: modern cppyy returns a LowLevelView with no SetSize();
        # np.frombuffer(..., count=n) reads it directly.
        # ROOT flat bin = binx + (nx+2)*biny  ->  [y][x], strip under/overflow
        a = np.frombuffer(h.GetArray(), dtype=dtype, count=(nx + 2) * (ny + 2))
        arr = np.array(a.reshape(ny + 2, nx + 2)[1:ny + 1, 1:nx + 1], dtype=np.float32)
        ch0 = int(round(h.GetXaxis().GetXmin() + 0.5))
        t0 = int(round(h.GetYaxis().GetXmin() + 0.5))
        if len(self._cache) > 14:            # keep memory bounded
            self._cache.clear()
        self._cache[key] = (arr, ch0, t0)
        return self._cache[key]

    def waveform(self, plane, stage, apa, channel):
        """1D (ticks, values) for one channel; cheap ProjectionY, no full read."""
        name = self.index.get((plane, stage, apa))
        if not name:
            return None
        h = self.f.Get(name)
        if not h:
            return None
        bx = h.GetXaxis().FindBin(float(channel))
        if bx < 1 or bx > h.GetNbinsX():
            return None
        p = h.ProjectionY("_py_%s_%d" % (name, channel), bx, bx)
        ny = p.GetNbinsX()
        dtype = np.float64 if p.ClassName().endswith("D") else np.float32
        vals = np.array(np.frombuffer(p.GetArray(), dtype=dtype,
                                      count=ny + 2)[1:ny + 1], dtype=np.float32)
        t0 = int(round(p.GetXaxis().GetXmin() + 0.5))
        p.Delete()
        return np.arange(t0, t0 + ny), vals


def maxpool2d_signed(arr, max_h, max_w):
    """Block downsample keeping the largest |value| so spikes of either sign
    survive.  Returns (img, fy, fx)."""
    h, w = arr.shape
    fy = max(1, int(np.ceil(h / max_h)))
    fx = max(1, int(np.ceil(w / max_w)))
    if fy == 1 and fx == 1:
        return arr, 1, 1
    ph, pw = (-h) % fy, (-w) % fx
    if ph or pw:
        arr = np.pad(arr, ((0, ph), (0, pw)), constant_values=0)
    H, W = arr.shape
    blk = arr.reshape(H // fy, fy, W // fx, fx)
    bmax = blk.max(axis=(1, 3))
    bmin = blk.min(axis=(1, 3))
    return np.where(bmax > -bmin, bmax, bmin), fy, fx


# ---------------------------------------------------------------------------
# bokeh app
# ---------------------------------------------------------------------------
def main():
    from bokeh.io import curdoc
    from bokeh.events import Tap
    from bokeh.layouts import column, row
    from bokeh.models import (Button, CheckboxGroup, ColorBar, ColumnDataSource,
                              Div, LinearColorMapper, Select, TextInput)
    from bokeh.palettes import Category20_20, RdBu11
    from bokeh.plotting import figure

    state = {"mag": None, "channel": None}

    # ---- widgets ----
    in_file = TextInput(value=DEFAULT_FILE, width=760,
                        title="Magnify ROOT file")
    bt_load = Button(label="Load", button_type="primary", width=90)
    sel_stage = Select(title="2D stage", options=[], value="", width=150)
    sel_plane = Select(title="plane", options=[], value="", width=90)
    sel_apa = Select(title="APA", options=[], value="", width=80)
    in_cabs = TextInput(value="", title="color |max| (symmetric)", width=170)
    cb_norm = CheckboxGroup(labels=["normalize 1D"], active=[], width=140)
    status = Div(text="<i>enter a file and press Load</i>", width=900)

    img_src = ColumnDataSource(dict(image=[np.zeros((1, 1), dtype=np.float32)],
                                    x=[0], y=[0], dw=[1], dh=[1]))
    mapper = LinearColorMapper(palette=list(reversed(RdBu11)), low=-1, high=1)

    fig2d = figure(width=760, height=680, title="2D (click a channel)",
                   x_axis_label="channel", y_axis_label="tick",
                   tools="pan,box_zoom,wheel_zoom,reset,save",
                   active_scroll="wheel_zoom")
    fig2d.image(image="image", x="x", y="y", dw="dw", dh="dh",
                color_mapper=mapper, source=img_src)
    fig2d.add_layout(ColorBar(color_mapper=mapper, width=10), "right")

    fig1d = figure(width=820, height=680, title="1D — click legend to hide/show",
                   x_axis_label="tick", y_axis_label="value",
                   tools="pan,box_zoom,wheel_zoom,reset,save",
                   active_scroll="wheel_zoom")
    lines = {}          # stage -> (renderer, source)

    # ---- colour limits (default: 60% of the full-histogram min/max) ----
    def default_climit():
        """Symmetric limit: 60% of the stage's largest |value|, so the
        blue-white-red palette stays centred on zero."""
        mag = state["mag"]
        got = (mag.array(sel_plane.value, sel_stage.value, int(sel_apa.value))
               if mag and sel_stage.value and sel_apa.value else None)
        if got is None:
            return 1.0
        arr = got[0]
        lim = 0.6 * max(abs(float(arr.min())), abs(float(arr.max())))
        return lim if lim > 0 else 1.0

    def set_climit_boxes():
        in_cabs.value = "%.4g" % default_climit()

    def apply_climits():
        try:
            lim = abs(float(in_cabs.value))
        except ValueError:
            lim = default_climit()
        if lim <= 0:
            lim = default_climit()
        mapper.low, mapper.high = -lim, lim

    # ---- 2D rendering (zoom-aware, server side) ----
    def render2d():
        mag = state["mag"]
        if not mag or not sel_stage.value:
            return
        got = mag.array(sel_plane.value, sel_stage.value, int(sel_apa.value))
        if got is None:
            status.text = "<b>no histogram</b> for that stage/plane/APA"
            return
        arr, ch0, t0 = got   # arr[tick, channel]; x = channel, y = tick
        nt, nch = arr.shape
        # visible window; bokeh auto-ranges report None *or* NaN before the
        # first renderer exists, so fall back to the full extent for both.
        def _rng(v, fallback):
            try:
                v = float(v)
            except (TypeError, ValueError):
                return fallback
            return fallback if not np.isfinite(v) else v
        x0 = _rng(fig2d.x_range.start, ch0)          # x = channel
        x1 = _rng(fig2d.x_range.end, ch0 + nch)
        y0 = _rng(fig2d.y_range.start, t0)           # y = tick
        y1 = _rng(fig2d.y_range.end, t0 + nt)
        i0 = max(0, int(np.floor(y0 - t0)));   i1 = min(nt, int(np.ceil(y1 - t0)))
        j0 = max(0, int(np.floor(x0 - ch0)));  j1 = min(nch, int(np.ceil(x1 - ch0)))
        if i1 <= i0 or j1 <= j0:
            return
        sub = arr[i0:i1, j0:j1]                      # rows = tick, cols = channel
        img, fy, fx = maxpool2d_signed(sub, MAX_IMG_H, MAX_IMG_W)
        apply_climits()
        img_src.data = dict(image=[img], x=[ch0 + j0], y=[t0 + i0],
                            dw=[(j1 - j0)], dh=[(i1 - i0)])
        fig2d.title.text = ("2D  h%s_%s%s   channels %d..%d, ticks %d..%d "
                            "(pooled %dx%d)" %
                            (sel_plane.value, sel_stage.value, sel_apa.value,
                             ch0 + j0, ch0 + j1 - 1, t0 + i0, t0 + i1 - 1, fy, fx))

    _pending = {"t": None}

    def schedule_render():
        # debounce the range callbacks
        if _pending["t"] is not None:
            try:
                curdoc().remove_timeout_callback(_pending["t"])
            except Exception:
                pass
        _pending["t"] = curdoc().add_timeout_callback(render2d, 150)

    fig2d.x_range.on_change("start", lambda a, o, n: schedule_render())
    fig2d.x_range.on_change("end", lambda a, o, n: schedule_render())
    fig2d.y_range.on_change("start", lambda a, o, n: schedule_render())
    fig2d.y_range.on_change("end", lambda a, o, n: schedule_render())

    # ---- 1D overlay ----
    def render1d():
        mag = state["mag"]
        ch = state["channel"]
        if not mag or ch is None:
            return
        plane, apa = sel_plane.value, int(sel_apa.value)
        stages = mag.stages(plane, apa)
        norm = 0 in cb_norm.active
        # build/refresh one line per stage
        for i, st in enumerate(stages):
            got = mag.waveform(plane, st, apa, ch)
            if got is None:
                continue
            t, v = got
            y = v.astype(np.float64)
            if norm:
                lo, hi = float(y.min()), float(y.max())
                y = (y - lo) / (hi - lo) if hi > lo else y * 0.0
            if st not in lines:
                src = ColumnDataSource(dict(x=t, y=y))
                r = fig1d.line("x", "y", source=src, legend_label=st,
                               line_width=1.4,
                               color=Category20_20[i % len(Category20_20)])
                lines[st] = (r, src)
            else:
                lines[st][1].data = dict(x=t, y=y)
        fig1d.legend.click_policy = "hide"
        fig1d.legend.label_text_font_size = "8pt"
        fig1d.yaxis.axis_label = "normalized" if norm else "value"
        fig1d.title.text = ("1D  %s-plane APA%s channel %d  — click legend to "
                            "hide/show" % (plane, apa, ch))

    def on_tap(event):
        if state["mag"] is None:
            return
        state["channel"] = int(round(event.x))   # x axis = channel
        render1d()

    fig2d.on_event(Tap, on_tap)

    # ---- loading / selector wiring ----
    def repopulate(keep=True):
        mag = state["mag"]
        apas = [str(a) for a in mag.apas()]
        sel_apa.options = apas
        if not keep or sel_apa.value not in apas:
            sel_apa.value = apas[-1] if apas else ""       # APA1 by default
        apa = int(sel_apa.value)
        planes = mag.planes(apa)
        sel_plane.options = planes
        if not keep or sel_plane.value not in planes:
            sel_plane.value = "w" if "w" in planes else (planes[0] if planes else "")
        stages = mag.stages(sel_plane.value, apa)
        sel_stage.options = stages
        if not keep or sel_stage.value not in stages:
            sel_stage.value = mag.default_stage(sel_plane.value, apa)

    def reset_ranges():
        """Set the 2D ranges to the full extent of the current histogram.
        DataRange1d rejects None, so always assign numbers."""
        mag = state["mag"]
        if not mag or not sel_stage.value:
            return
        got = mag.array(sel_plane.value, sel_stage.value, int(sel_apa.value))
        if got is None:
            return
        arr, ch0, t0 = got                      # arr[tick, channel]
        nt, nch = arr.shape
        fig2d.x_range.start, fig2d.x_range.end = ch0, ch0 + nch   # channel
        fig2d.y_range.start, fig2d.y_range.end = t0, t0 + nt       # tick

    def do_load():
        path = in_file.value.strip()
        try:
            state["mag"] = MagFile(path)
        except Exception as exc:
            status.text = "<b style='color:crimson'>load failed:</b> %s" % exc
            return
        mag = state["mag"]
        for st in list(lines):                 # stage set may change
            fig1d.renderers.remove(lines[st][0])
            del lines[st]
        if fig1d.legend:
            fig1d.legend.items = []
        state["channel"] = None
        repopulate(keep=False)
        status.text = ("loaded <b>%s</b> — %d histograms, stages: %s" %
                       (os.path.basename(path), len(mag.index),
                        ", ".join(mag.stages())))
        reset_ranges()
        set_climit_boxes()
        render2d()

    bt_load.on_click(do_load)

    def on_geom(attr, old, new):
        if state["mag"] is None:
            return
        repopulate(keep=True)
        reset_ranges()
        set_climit_boxes()
        render2d()
        render1d()

    sel_apa.on_change("value", on_geom)
    sel_plane.on_change("value", on_geom)
    def on_stage(attr, old_, new_):
        set_climit_boxes()      # 60% default for the newly selected stage
        render2d()
    sel_stage.on_change("value", on_stage)
    in_cabs.on_change("value", lambda a, o, n: apply_climits())
    cb_norm.on_change("active", lambda a, o, n: render1d())

    curdoc().add_root(column(
        row(in_file, column(Div(text="<br>"), bt_load)),
        row(sel_stage, sel_plane, sel_apa, in_cabs, cb_norm),
        status,
        row(fig2d, fig1d)))
    curdoc().title = "Magnify viewer"

    if DEFAULT_FILE:
        do_load()


# Import-only mode (for headless testing of the data layer):
#   MAGNIFY_NO_SERVE=1 python3 -c "import magnify_viewer"
if os.environ.get("MAGNIFY_NO_SERVE") != "1":
    main()
