#!/usr/bin/env python3
"""make-report.py <outdir-with-jsons> > report.md  — per-species tables from size-breakdown.py output"""
import json, sys, os
W = sys.argv[1]
S = [('mccv', 'MC BNB CV', 13216), ('nuecc', 'MC nueCC', 8877), ('beamon', 'beam-on', 10000), ('beamoff', 'beam-off', 10000)]
def MB(b): return b / 1e6
def kB(b): return b / 1e3
data = {k: json.load(open(f'{W}/{k}.json')) for k, _, _ in S}

print('## A. Where the bytes are, per sample (run/ directory)\n')
print('| sample | events | total | `bee/` | `tracking-pr/` | `logs/` | other | **per event** (bee + root) |')
print('|---|---|---|---|---|---|---|---|')
for k, name, n in S:
    d = data[k]['dirs']; tot = sum(d.values()); bee = d.get('bee', 0); tp = d.get('tracking-pr', 0); lg = d.get('logs', 0); oth = tot - bee - tp - lg
    print(f'| {name} | {n:,} | **{MB(tot)/1e3:.1f} GB** | {MB(bee)/1e3:.1f} GB ({100*bee/tot:.0f} %) | {MB(tp)/1e3:.2f} GB ({100*tp/tot:.0f} %) | {MB(lg)/1e3:.2f} GB ({100*lg/tot:.0f} %) | {MB(oth):.0f} MB | **{kB(bee+tp)/n:,.0f} kB** (bee {kB(bee)/n:,.0f}, root {kB(tp)/n:,.0f}) |')

print('\n## B. Bee zip — per JSON layer, summed over every event (compressed = on disk; ratio = uncompressed/compressed)\n')
for k, name, n in S:
    b = data[k]['bee']; L = b['layers']; tot = b['total_bytes']
    print(f'\n### {name} — {b["nzips"]:,} zips, {MB(tot)/1e3:.1f} GB, {kB(tot)/b["nzips"]:,.0f} kB/event\n')
    print('| layer | in N events | compressed total | per event (all) | per event (when present) | share | uncompressed total | ratio |')
    print('|---|---|---|---|---|---|---|---|')
    for lay, v in sorted(L.items(), key=lambda kv: -kv[1]['compressed']):
        c, u, cnt = v['compressed'], v['uncompressed'], v['n']
        print(f'| `{lay}` | {cnt:,} | {MB(c):,.0f} MB | {kB(c)/b["nzips"]:,.1f} kB | {kB(c)/max(cnt,1):,.1f} kB | {100*c/tot:.1f} % | {MB(u):,.0f} MB | {u/max(c,1):.1f}× |')

print('\n## C. `tracking-pr.root` — per TTree, candidate vs non-candidate files (zip = compressed on disk, tot = uncompressed)\n')
for k, name, n in S:
    r = data[k]['root']
    for cls, label in (('cand', 'candidate (has T_kine)'), ('noncand', 'non-candidate')):
        rr = r[cls]; nf = rr['nfiles']
        if nf == 0: continue
        print(f'\n### {name} — {label}: {nf:,} files, {MB(rr["total_bytes"]):,.0f} MB, {kB(rr["total_bytes"])/nf:,.1f} kB/file\n')
        print('| tree | zip total | per file | share of files\' bytes | uncompressed | ratio |')
        print('|---|---|---|---|---|---|')
        for t, v in sorted(rr['trees'].items(), key=lambda kv: -kv[1]['zip']):
            print(f'| `{t}` | {MB(v["zip"]):,.1f} MB | {kB(v["zip"])/nf:,.1f} kB | {100*v["zip"]/max(rr["total_bytes"],1):.1f} % | {MB(v["tot"]):,.1f} MB | {v["tot"]/max(v["zip"],1):.1f}× |')
        s = sum(v['zip'] for v in rr['trees'].values())
        print(f'\nTrees account for {100*s/max(rr["total_bytes"],1):.0f} % of the file bytes; the rest is ROOT file structure/keys (~{kB(rr["total_bytes"]-s)/nf:.1f} kB/file).')
