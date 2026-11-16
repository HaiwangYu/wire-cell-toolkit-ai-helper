#!/usr/bin/env python3
"""Issue 48 P2 / R2: how many kept step-1 tars still exist (stat only, read-only).
   count-scratch-tars.py <out.tsv> <name=list.txt> ...   (one path per line; size from stat)"""
import os, sys
from concurrent.futures import ThreadPoolExecutor
out = sys.argv[1]
def st(p):
    try: return p, os.stat(p).st_size
    except OSError: return p, -1
rows = []
with ThreadPoolExecutor(16) as ex:
    for arg in sys.argv[2:]:
        name, lst = arg.split('=', 1)
        paths = [l.split()[0] for l in open(lst) if l.strip()]
        res = list(ex.map(st, paths))
        n_ok = sum(1 for _, s in res if s > 0); n_zero = sum(1 for _, s in res if s == 0)
        gb = sum(s for _, s in res if s > 0) / 1e9
        rows.append((name, len(paths), n_ok, n_zero, len(paths) - n_ok - n_zero, round(gb, 1)))
        with open(out + '.' + name + '.missing', 'w') as f:
            f.writelines(p + '\n' for p, s in res if s <= 0)
        print(*rows[-1], sep='\t', flush=True)
with open(out, 'w') as f:
    f.write('list\tlisted\tpresent\tzero_size\tmissing\tGB\n')
    for r in rows: f.write('\t'.join(map(str, r)) + '\n')
