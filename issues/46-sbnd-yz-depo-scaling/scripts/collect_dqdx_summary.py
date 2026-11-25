#!/usr/bin/env python3
"""Collect the issue-46 dQ/dx numbers of one analysis directory into dqdx_summary.json:
truth-sp/truth_sp_summary.json, fit*/fit_summary.json, and the reco cost of
wcreco-*/step{1,2}/time.txt and reco1-*/reco1.time (/usr/bin/time -v).

Usage: collect_dqdx_summary.py <analysis-dir> [--note "..."]
"""
import argparse
import json
import os
import re

ap = argparse.ArgumentParser()
ap.add_argument("adir")
ap.add_argument("--note", default="")
a = ap.parse_args()


def timev(fn):
    if not os.path.exists(fn):
        return None
    t = open(fn).read()

    def g(pat):
        m = re.search(pat, t)
        return m.group(1) if m else None
    wall = g(r"Elapsed \(wall clock\) time \(h:mm:ss or m:ss\): (\S+)")
    sec = None
    if wall:
        parts = [float(x) for x in wall.split(":")]
        sec = sum(p * 60 ** i for i, p in enumerate(reversed(parts)))
    u, s = float(g(r"User time \(seconds\): (\S+)") or 0), float(g(r"System time \(seconds\): (\S+)") or 0)
    return dict(wall=wall, wall_s=sec, cpu_s=u + s, user_s=u, sys_s=s,
                maxrss_MB=int(g(r"Maximum resident set size \(kbytes\): (\d+)") or 0) / 1024.0,
                exit_status=g(r"Exit status: (\d+)"))


S = dict(analysis_dir=os.path.abspath(a.adir), note=a.note)
import glob  # noqa: E402
p = f"{a.adir}/truth-sp/truth_sp_summary.json"
if os.path.exists(p):
    S["truth_sp"] = json.load(open(p))
for p in sorted(glob.glob(f"{a.adir}/fit*/fit_summary.json")):
    S[os.path.basename(os.path.dirname(p)).replace("-", "_")] = json.load(open(p))
cost = {}
for d in sorted(glob.glob(f"{a.adir}/wcreco-*")):
    if not os.path.isdir(d):
        continue
    for st in ("step1", "step2", "step2-prodgate"):
        c = timev(f"{d}/{st}/time.txt")
        if c:
            cost[f"{os.path.basename(d)} {st}"] = c
for m in ("off", "on"):
    c = timev(f"{a.adir}/reco1-{m}/reco1.time")
    if c:
        cost[f"{m} reco1 (larsoft standard_reco1_sbnd.fcl)"] = c
if cost:
    S["reco_cost"] = cost
json.dump(S, open(f"{a.adir}/dqdx_summary.json", "w"), indent=1)
print(f"wrote {a.adir}/dqdx_summary.json ({', '.join(k for k in S if k not in ('analysis_dir', 'note'))})")
