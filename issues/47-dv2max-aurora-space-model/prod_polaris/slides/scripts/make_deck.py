"""Beamer deck: nueCC-48 + NCpi0-19 vertexing, Xin round 2 vs `original` vs `aurora_space`, against Xin's round-2 hand scan.

usage: make_deck.py <prod_polaris dir> <porting tables dir> <bee cache dir> <out dir>
Writes <out>/figures/evt-<run>-<event>.png and <out>/deck.tex.  Optional <prod_polaris>/tables/xin-r2-scores.csv
(sample,run,subrun,event,nu_index,nue_score,numu_score,numu_cc_flag,nu_x,nu_y,nu_z,...) fills Xin r2's scores.
"""
import csv, json, math, os, re, sys
from collections import Counter
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

P, T, CACHE, OUT = sys.argv[1:5]
os.makedirs(f"{OUT}/figures", exist_ok=True)
SETS = {"orig": "89cdea53-c227-476c-8f67-0ae765f804b4", "aur": "431dc57f-997d-4cff-88e1-4e33fd743ab8"}
BEE = "https://www.phy.bnl.gov/twister/bee/set/%s/event/%d/"
# Sheet RSE typos, checked against the runNo/subRunNo/eventNo of Xin's round-2 Bee event of that row:
SHEET_FIX = {(18255, 234538): (18255, 234638), (18355, 40074): (18355, 400474)}
HALF = 40.0  # cm, half-width of the zoom window
M = {"xin": ("Xin r2", "tab:purple", "s"), "orig": ("original", "tab:blue", "o"), "aur": ("aurora", "tab:red", "^")}
f = float


def dist(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b))) if (a and b) else float("nan")


def load_json(uuid, idx, layer):
    p = f"{CACHE}/{uuid[:8]}-{idx}-{layer}.json"
    return json.load(open(p)) if os.path.exists(p) else None


def mc_vertex(uuid, idx):
    d = load_json(uuid, idx, "mc")
    if not d: return None, 0
    starts = [tuple(round(v, 2) for v in n["data"]["start"]) for n in d if isinstance(n, dict) and "data" in n]
    if not starts: return None, 0
    return Counter(starts).most_common(1)[0][0], len(set(starts))


# --- inputs ------------------------------------------------------------------------------------------------
sheet = {}
for tab, samp in (("nuecc", "nuecc48"), ("ncpi0", "ncpi0")):
    R = list(csv.reader(open(f"{P}/tables/handscan-xin-r2-{tab}.csv")))
    i = [k for k, r in enumerate(R) if r and r[0].lower().startswith("round 2")][0]
    for r in R[i + 1:]:
        if r and re.match(r"\d+-\d+", r[0]):
            run, evt = (int(x) for x in r[0].split("-"))
            run, evt = SHEET_FIX.get((run, evt), (run, evt))
            m = re.search(r"/set/([0-9a-f-]+)/event/(\d+)", r[1])
            sheet[(run, evt)] = dict(uuid=m.group(1), idx=int(m.group(2)), link=r[1].strip(), verdict=r[2].strip(),
                                     note=" ".join(x.strip() for x in r[3:5] if x.strip()))
E = {(int(r["run"]), int(r["event"])): r for r in csv.DictReader(open(f"{T}/data-orig-vs-aur-event.csv"))}
C = {(int(r["run"]), int(r["event"])): r for r in csv.DictReader(open(f"{T}/data-orig-vs-aur-cand.csv")) if r["selected_A"] == "1"}
HS = {(int(r["run"]), int(r["event"])): r for r in csv.DictReader(open(f"{P}/tables/handscan-vs-arms.csv"))}
XS = {}
XV0 = {}  # exact Xin r2 main vertex (Bee q == 15000 marker), from production-prep_wcgpu1's table
if os.path.exists(f"{P}/tables/xin-r2-prod0811.csv"):
    for r in csv.DictReader(open(f"{P}/tables/xin-r2-prod0811.csv")):
        XV0[(int(r["run"]), int(r["event"]))] = (float(r["nu_x"]), float(r["nu_y"]), float(r["nu_z"]))
xs_path = f"{P}/tables/xin-r2-scores.csv"
if os.path.exists(xs_path):
    for r in csv.DictReader(open(xs_path)):
        XS[(int(r["run"]), int(r["event"]))] = r


def tex(s):
    s = str(s)
    for a, b in (("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"), ("$", r"\$"), ("#", r"\#"), ("_", r"\_"),
                 ("{", r"\{"), ("}", r"\}"), ("~", r"\textasciitilde{}"), ("^", r"\textasciicircum{}"), ("<", r"$<$"), (">", r"$>$")):
        s = s.replace(a, b)
    return s


def pred(nue, numu, generic):
    if generic is not None and not generic: return "no $\\nu$"
    t = []
    if nue is not None and nue > 7: t.append("$\\nu_e$")
    if numu is not None and numu > 0.9: t.append("$\\nu_\\mu$CC")
    return "+".join(t) if t else "other"


def flavor(samp, note):
    base = "$\\nu_e$CC" if samp == "nuecc48" else "NC$\\pi^0$"
    n = note.lower()
    hint = ""
    if samp == "nuecc48" and ("ncpi0" in n.replace(" ", "") or "nc pi0" in n): hint = " (scan note: NC$\\pi^0$?)"
    if samp == "ncpi0" and ("electron" in n and "mis" not in n): hint = ""
    return base + hint


# --- per event ---------------------------------------------------------------------------------------------
events = []
for key in sorted(E, key=lambda k: (0 if E[k]["sample"] == "nuecc48" else 1, int(E[k]["orig_bee"]))):
    e, c, s, h = E[key], C.get(key), sheet.get(key), HS.get(key)
    run, evt = key
    v = {"orig": (f(c["orig_x"]), f(c["orig_y"]), f(c["orig_z"])) if c else None,
         "aur": (f(c["aur_x"]), f(c["aur_y"]), f(c["aur_z"])) if c else None}
    xv, nst = mc_vertex(s["uuid"], s["idx"]) if s else (None, 0)
    if key in XV0: xv = XV0[key]
    v["xin"] = xv
    ref, refsrc = None, "none"
    if h and h["ref_x"]:
        ref = (f(h["ref_x"]), f(h["ref_y"]), f(h["ref_z"]))
        refsrc = "scanner point" if h["ref_source"].startswith("scanner") else "Xin r2 vertex (scan Good/OK)"
        if "(?)" in h["ref_source"]: refsrc += " ?"
    d = {k: dist(v[k], ref) for k in v}
    mism = ref is not None and min(d["orig"], d["aur"]) > 10
    x = XS.get(key)
    sc = {"orig": (f(e["orig_nue_score"]), f(e["orig_numu_score"]), e["orig_generic"] == "1"),
          "aur": (f(e["aur_nue_score"]), f(e["aur_numu_score"]), e["aur_generic"] == "1"),
          "xin": ((f(x["nue_score"]), f(x["numu_score"]), int(f(x["numu_cc_flag"])) >= 0) if x else (None, None, None))}
    events.append(dict(key=key, samp=e["sample"], e=e, s=s, v=v, ref=ref, refsrc=refsrc, d=d, mism=mism, sc=sc,
                       nstart=nst, changed=e["changed"] == "1"))

# --- figures -----------------------------------------------------------------------------------------------
def tf_points(which, ev):
    if which == "xin":
        if not ev["s"]: return None
        dj = load_json(ev["s"]["uuid"], ev["s"]["idx"], "track_fit-global")
    else:
        dj = load_json(SETS[which], int(ev["e"][f"{which}_bee"]), "track_fit-global")
    if not dj or "x" not in dj: return None
    return dj["x"], dj["z"]


for ev in events:
    run, evt = ev["key"]
    ctr = ev["ref"] if (ev["ref"] and not ev["mism"]) else (ev["v"]["aur"] or ev["v"]["orig"])
    fig, axs = plt.subplots(1, 3, figsize=(12, 4.5), sharex=True, sharey=True)
    for ax, k in zip(axs, ("xin", "orig", "aur")):
        name, col, mk = M[k]
        pts = tf_points(k, ev)
        if pts:
            ax.scatter(pts[1], pts[0], s=2, c="0.45", lw=0, label="traj-fit points")
        offp = []
        for k2 in ("xin", "orig", "aur"):
            vv = ev["v"][k2]
            if not vv: continue
            n2, c2, m2 = M[k2]
            big = k2 == k
            zz, xx = vv[2], vv[0]
            dz, dx = zz - ctr[2], xx - ctr[0]
            far = max(abs(dz), abs(dx)) > HALF
            if far:  # off-panel: put the marker on the edge, with an arrow and the distance
                sc_ = (HALF * 0.9) / max(abs(dz), abs(dx))
                ez, ex = ctr[2] + dz * sc_, ctr[0] + dx * sc_
                ax.annotate("", xy=(ctr[2] + dz * sc_ * 1.08, ctr[0] + dx * sc_ * 1.08), xytext=(ez, ex),
                            arrowprops=dict(arrowstyle="->", color=c2, lw=1.5))
                offp.append(f"{n2} ({math.hypot(dz, dx):.0f} cm in xz)")
                zz, xx = ez, ex
            ax.scatter([zz], [xx], s=140 if big else 45, marker=m2, facecolors=c2 if big else "none",
                       edgecolors=c2, lw=1.5, alpha=1.0 if big else 0.6, zorder=5, label=f"{n2} vertex")
        if ev["ref"]:
            ax.scatter([ev["ref"][2]], [ev["ref"][0]], s=220, marker="*", facecolors="none", edgecolors="k", lw=1.3,
                       zorder=6, label="hand-scan vertex")
        if offp:
            ax.text(0.02, 0.98, "off panel (arrow): " + ", ".join(offp), transform=ax.transAxes, fontsize=7, va="top",
                    bbox=dict(fc="white", ec="0.7", alpha=0.85, pad=2), zorder=8)
        ax.set_xlim(ctr[2] - HALF, ctr[2] + HALF); ax.set_ylim(ctr[0] - HALF, ctr[0] + HALF)
        ax.set_aspect("equal"); ax.grid(alpha=0.25)
        dd = ev["d"][k]
        ttl = f"{name}" + ("" if math.isnan(dd) or ev["mism"] else f"  (d = {dd:.2f} cm)")
        ax.set_title(ttl, color=col, fontsize=11)
        ax.set_xlabel("z [cm]")
        if not pts: ax.text(0.5, 0.5, "no traj-fit layer", transform=ax.transAxes, ha="center", color="0.5")
    axs[0].set_ylabel("x [cm]")
    h, l = axs[2].get_legend_handles_labels()
    uniq = dict(zip(l, h))
    fig.legend(uniq.values(), uniq.keys(), loc="lower center", ncol=5, fontsize=8, frameon=False)
    fig.subplots_adjust(left=0.06, right=0.99, top=0.91, bottom=0.17, wspace=0.08)
    fig.savefig(f"{OUT}/figures/evt-{run}-{evt}.png", dpi=110)
    plt.close(fig)

# --- summary numbers -----------------------------------------------------------------------------------------
def stats(evs, k):
    ds = [ev["d"][k] for ev in evs]
    ds = [x for x in ds if not math.isnan(x)]
    if not ds: return None
    srt = sorted(ds); n = len(srt)
    med = srt[n // 2] if n % 2 else 0.5 * (srt[n // 2 - 1] + srt[n // 2])
    return n, sum(x < 1 for x in ds), sum(x < 2 for x in ds), sum(x < 3 for x in ds), med


usable = [ev for ev in events if ev["ref"] and not ev["mism"]]
perf_rows = []
for samp_name, sel in (("$\\nu_e$CC-48", "nuecc48"), ("NC$\\pi^0$-19", "ncpi0"), ("all", None)):
    for refname, rf in (("scan Good/OK", "Xin"), ("scan Not good", "scanner"), ("all", None)):
        evs = [ev for ev in usable if (sel is None or ev["samp"] == sel) and (rf is None or ev["refsrc"].startswith(rf))]
        if not evs: continue
        row = [samp_name, refname]
        for k in ("xin", "orig", "aur"):
            st = stats(evs, k)
            row.append("--" if not st else f"{st[1]}/{st[2]}/{st[3]} of {st[0]}, {st[4]:.2f}")
        perf_rows.append(row)


def pred_counts(sel, k):
    evs = [ev for ev in events if ev["samp"] == sel]
    if k == "xin" and not XS: return None
    cnt = Counter(pred(*ev["sc"][k]) for ev in evs if ev["sc"][k][0] is not None)
    return len(evs), cnt


# --- deck ----------------------------------------------------------------------------------------------------
GH = "https://github.com/HaiwangYu/wire-cell-toolkit-ai-helper"
L = []
w = L.append
w(r"""\documentclass[aspectratio=169,10pt]{beamer}
\usetheme{default}\usecolortheme{default}
\setbeamertemplate{navigation symbols}{}
\setbeamertemplate{footline}[frame number]
\usepackage{booktabs}\usepackage{graphicx}\usepackage{hyperref}\usepackage{array}
\hypersetup{colorlinks=true,urlcolor=blue!60!black,linkcolor=black}
\title{SBND DL vertexing on data: Xin round 2 vs \texttt{original} vs \texttt{aurora\_space}}
\subtitle{nueCC-48 + NC$\pi^0$-19, against Xin's round-2 hand scan}
\author{Haiwang Yu (prepared with Claude Code)}
\date{2026-11-16}
\begin{document}
\frame{\titlepage}
""")
w(r"""\begin{frame}{Setup: the three methods}
\small
\begin{tabular}{>{\raggedright\arraybackslash}p{0.13\linewidth}>{\raggedright\arraybackslash}p{0.82\linewidth}}
\toprule
\textbf{Xin r2} & Xin's \emph{prod0811} delivery (2026-08-11) behind the round-2 hand-scan Bee sets (\texttt{9e2a1a1e} nueCC, \texttt{13900b8c} NC$\pi^0$).
His 2-step chain: stage A = \texttt{cb0805} Q/L hubs (toolkit \texttt{a1ea3789}); stage B = \texttt{run\_pr\_chain\_batch.sh \ldots{} data} at toolkit \texttt{b38127a0}
(apply-pointcloud, ``pr/64 round 4''), compiled defaults. uboone SCN DL vertex, \emph{single} chain (no dual chain, no \texttt{vertex\_method}).
Main vertex: Bee neutrino-vertex marker. Scores: \emph{not recoverable} (\texttt{tracking-pr.root} deleted 2026-08-13). \\
\midrule
\textbf{original} & WCT master \texttt{c6be329e} + PR\,\#547 (tree of \texttt{e426d988}); \texttt{vertex\_method=original}: uboone SCN net
(\texttt{t48k-m16-l5-lr5d-res0.5-CP24.pth}), re-rank top-5 (accept score $\ge 10$), dual chain \texttt{snap} (transfer $\le 2$\,cm), fit exclusion,
\texttt{improve\_vertex} and the snap/audit refinements. 2 network calls per candidate. \\
\midrule
\textbf{aurora} & Same build; \texttt{vertex\_method=dv2\_split\_move}, bundle \texttt{dv2max/sbnd/aurora\_space} (wire-cell-data \#8, \texttt{bundle.json} sha256 \texttt{51588842}):
DV2-MAX trained on aurora-r2 MC (478k events), input = trajectory-fit cloud + Bee space points of touching clusters; vertex = nearest graph vertex if
$<1.5$\,cm, else split at the nearest fit point, then moved onto the DV2-MAX point. No dual chain. 1 call per candidate. \\
\bottomrule
\end{tabular}

\medskip
Both of our arms: step 2 from the same step-1 tars (\#43 data slices, FrameShift applied), production data TLAs, one pinned core each.
\end{frame}
""")
w(r"""\begin{frame}{Links}
\small
\begin{itemize}
\item Tracking issue: \href{""" + GH + r"""/issues/47}{ai-helper \#47}; space-point plan \href{""" + GH + r"""/issues/44}{\#44};
DL dump \href{""" + GH + r"""/issues/35}{\#35}; PR\,\#543 review \href{""" + GH + r"""/issues/43}{\#43}; flat CAF \href{""" + GH + r"""/issues/39}{\#39}; truth match \href{""" + GH + r"""/issues/41}{\#41}
\item WCT PRs: \href{https://github.com/WireCell/wire-cell-toolkit/pull/543}{\#543} (DV2-MAX, merged),
\href{https://github.com/WireCell/wire-cell-toolkit/pull/544}{\#544} (flat CAF + truth match, merged),
\href{https://github.com/WireCell/wire-cell-toolkit/pull/547}{\#547} (\texttt{aurora\_space}, open);
wire-cell-data \href{https://github.com/WireCell/wire-cell-data/pull/8}{\#8} (bundle, merged)
\item Docs (issue-47 folder): \href{""" + GH + r"""/blob/main/issues/47-dv2max-aurora-space-model/porting_sbndbuild03/data-orig-vs-aur.md}{data original vs aurora},
\href{""" + GH + r"""/blob/main/issues/47-dv2max-aurora-space-model/prod_polaris/handscan-vertex.md}{hand-scan vertex method},
\href{""" + GH + r"""/blob/main/issues/47-dv2max-aurora-space-model/prod_polaris/data-events-handscan.md}{per-event table},
\href{""" + GH + r"""/blob/main/issues/47-dv2max-aurora-space-model/porting_sbndbuild03/results.md}{MC + hold-out validation}
\item Bee: \href{""" + BEE % (SETS["orig"], 0) + r"""}{original set}, \href{""" + BEE % (SETS["aur"], 0) + r"""}{aurora set};
Xin r2 \href{https://www.phy.bnl.gov/twister/bee/set/9e2a1a1e-b637-4be5-99b7-f49bf8c04c57/event/0/}{nueCC},
\href{https://www.phy.bnl.gov/twister/bee/set/13900b8c-e48c-4ebb-8daa-da19e2e989b6/event/0/}{NC$\pi^0$}
\end{itemize}
\end{frame}
""")
w(r"""\begin{frame}{Hand-scan reference (``true'' vertex in this deck)}
\small
\begin{itemize}
\item Xin's round-2 hand scan rates each event's round-2 vertex: Good / OK / Not OK / Not good.
\item \textbf{Good/OK}: reference = Xin r2's main vertex (the neutrino-vertex marker of his Bee set).
So Xin r2 is 0\,cm \emph{by construction} on these events.
\item \textbf{Not OK/Not good with ``(x, y, z)''}: reference = the scanner's point (eyeballed in Bee, $\sim$1\,cm).
\item Excluded from the vertex numbers: 3 ``Not good'' events without coordinates; 5 events where our selected candidate is a different interaction from
the scanned one (both our arms $>10$\,cm away and within 0.2\,cm of each other); 1 event not in the sheet (18259/1/116962).
\item Two sheet RSE typos corrected against Xin's Bee events (18255-234538$\to$234638, 18355-40074$\to$400474).
\item Flavor: from the hand-picked sample (nueCC-48 $\to\nu_e$CC, NC$\pi^0$-19 $\to$ NC$\pi^0$), with the scanner's note when it suggests otherwise.
\item Prediction from scores: $\nu_e$ = \texttt{nue\_score} $>7$; $\nu_\mu$CC = \texttt{numu\_score} $>0.9$; ``no $\nu$'' = fails the generic cut.
\end{itemize}
\end{frame}
""")
w(r"""\begin{frame}{Vertexing vs the hand scan (assumed true)}
\scriptsize
Entries: $<1$/$<2$/$<3$\,cm of $n$ events, median distance [cm].
\begin{center}
\begin{tabular}{llccc}
\toprule
sample & reference & Xin r2 & original & aurora \\
\midrule
""" + "\n".join(" & ".join(r) + r" \\" for r in perf_rows) + r"""
\bottomrule
\end{tabular}
\end{center}
\begin{itemize}
\item Where the scanners located the right vertex (Not good), \textbf{aurora} is within 1.5\,cm in 11 of 13 events; \textbf{original} is 5--50\,cm off in 7.
\item Where Xin r2 was judged Good/OK, aurora is at least as close to that vertex as original (the reference is biased towards Xin r2, and partly towards original).
\end{itemize}
\end{frame}
""")
LABS = [("$\\nu_e$", "$\\nu_e$"), ("$\\nu_\\mu$CC", "$\\nu_\\mu$CC"), ("$\\nu_e$+$\\nu_\\mu$CC", "both"), ("other", "other"), ("no $\\nu$", "no $\\nu$")]
prow = []
for sname, sel in (("nueCC-48 ($\\nu_e$CC)", "nuecc48"), ("NC$\\pi^0$-19 (NC)", "ncpi0")):
    for k in ("xin", "orig", "aur"):
        pc = pred_counts(sel, k)
        if not pc:
            prow.append([sname, M[k][0]] + [r"\multicolumn{%d}{c}{scores not recoverable}" % len(LABS)]); continue
        n, cnt = pc
        prow.append([sname, M[k][0]] + [str(cnt.get(lab, 0)) for lab, _ in LABS])
    prow.append(None)
w(r"""\begin{frame}{Predictions from the current scores}
\small
\begin{center}
\begin{tabular}{llccccc}
\toprule
sample (hand-scan flavor) & method & """ + " & ".join(h for _, h in LABS) + r""" \\
\midrule
""" + "\n".join((r"\midrule" if r is None else " & ".join(r) + r" \\") for r in prow[:-1]) + r"""
\bottomrule
\end{tabular}
\end{center}
\begin{itemize}
\item $\nu_e$: \texttt{nue\_score} $>7$; $\nu_\mu$CC: \texttt{numu\_score} $>0.9$; both: passes both; other: neither; no $\nu$: fails the generic cut.
\item nueCC-48 is hand-scanned $\nu_e$CC, so more $\nu_e$ is better. NC$\pi^0$-19 is NC, so $\nu_e$ or $\nu_\mu$CC there is wrong.
\item original $\to$ aurora: 9 events change; the per-event pages flag them.
\end{itemize}
\end{frame}
""")
for i, ev in enumerate(events):
    run, evt = ev["key"]; e = ev["e"]; s = ev["s"]
    sname = "nueCC-48" if ev["samp"] == "nuecc48" else "NC$\\pi^0$-19"
    title = f"{sname}: {run}/1/{evt}"
    flags = []
    if ev["changed"]: flags.append(r"\textcolor{red}{selection changes}")
    if ev["mism"]: flags.append(r"\textcolor{orange!80!black}{our candidate $\ne$ scanned interaction}")
    if not s: flags.append("not in the scan sheet")
    rows = []
    links = {"xin": s["link"] if s else None, "orig": BEE % (SETS["orig"], int(e["orig_bee"])), "aur": BEE % (SETS["aur"], int(e["aur_bee"]))}
    for k in ("xin", "orig", "aur"):
        name = M[k][0]; vv = ev["v"][k]; dd = ev["d"][k]
        nue, numu, gen = ev["sc"][k]
        vtx = "--" if not vv else f"({vv[0]:.1f}, {vv[1]:.1f}, {vv[2]:.1f})"
        dtx = "--" if (math.isnan(dd) or ev["mism"]) else ("\\textbf{%.2f}" % dd if dd < 1 else "%.2f" % dd)
        sct = "--" if nue is None else f"{nue:.2f} / {numu:.2f}"
        prd = "--" if nue is None else pred(nue, numu, gen)
        lk = r"\href{" + links[k] + "}{Bee}" if links[k] else "--"
        rows.append(f"{name} & {lk} & {vtx} & {dtx} & {sct} & {prd} \\\\")
    ref = "--" if not ev["ref"] else f"({ev['ref'][0]:.1f}, {ev['ref'][1]:.1f}, {ev['ref'][2]:.1f})"
    verdict = tex(s["verdict"]) if s else "--"
    note = tex(s["note"][:150]) if s and s["note"] else ""
    w(r"""\begin{frame}{""" + title + r"""}
\vspace{-6pt}
\centering\includegraphics[width=0.92\linewidth]{figures/evt-""" + f"{run}-{evt}" + r""".png}\\[-2pt]
\scriptsize\raggedright
\textbf{Hand scan:} vertex """ + ref + r""" [""" + tex(ev["refsrc"]) + r"""], Xin r2 verdict: """ + verdict + r""", flavor: """ + flavor(ev["samp"], s["note"] if s else "") + (r"""; """ + ", ".join(flags) if flags else "") + r"""\\
""" + (r"\textit{Scan note: " + note + r"}\\" if note else "") + r"""
\begin{tabular}{llcccc}
\toprule
method & & main vertex (x, y, z) cm & d to hand scan [cm] & $\nu_e$ / $\nu_\mu$ score & prediction \\
\midrule
""" + "\n".join(rows) + r"""
\bottomrule
\end{tabular}
\end{frame}
""")
w(r"\end{document}")
open(f"{OUT}/deck.tex", "w").write("\n".join(L))
print("events", len(events), "usable", len(usable), "figures", len(os.listdir(f"{OUT}/figures")))
