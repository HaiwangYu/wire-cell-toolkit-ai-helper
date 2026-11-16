#!/usr/bin/env python3
"""bee-compare.py <new runs dir> <old runs dir>   (issue 47 task B: Bee output identical after the MABC refactor)
For every unit present in both: mabc-pr.zip compared member by member (names, order, bytes).  Prints one line per
unit and a total; exit 1 if anything differs."""
import glob
import os
import sys
import zipfile

NEW, OLD = sys.argv[1:3]
bad = n = members = 0
for d in sorted(glob.glob(os.path.join(NEW, "*--*"))):
    o = os.path.join(OLD, os.path.basename(d), "mabc-pr.zip")
    z = os.path.join(d, "mabc-pr.zip")
    if not (os.path.exists(o) and os.path.exists(z)):
        print(os.path.basename(d), "missing"); bad += 1; continue
    a, b = zipfile.ZipFile(z), zipfile.ZipFile(o)
    na, nb = a.namelist(), b.namelist()
    diff = [x for x in sorted(set(na) | set(nb)) if x not in na or x not in nb or a.read(x) != b.read(x)]
    n += 1; members += len(na)
    print(os.path.basename(d), len(na), "members", "IDENTICAL" if (na == nb and not diff) else f"DIFFER {len(diff)} {diff[:3]}")
    bad += bool(diff or na != nb)
print(f"units {n}, members {members}, units differing {bad}")
sys.exit(1 if bad else 0)
