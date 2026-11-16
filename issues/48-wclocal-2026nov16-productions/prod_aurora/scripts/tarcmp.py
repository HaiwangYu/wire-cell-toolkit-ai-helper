#!/usr/bin/env python3
"""ai-helper #48 P2: compare two qlpctree.tar.gz by datapath (the #41 V1b method, val41.tar_members):
array content per datapath + metadata per datapath; set metadata may differ only in input_file.
  tarcmp.py <new.tar.gz> <old.tar.gz>   -> one JSON line"""
import json, sys, tarfile, collections
def members(path):
    raw = {}
    with tarfile.open(path) as t:
        for m in t.getmembers():
            if m.isfile():
                raw[m.name] = t.extractfile(m).read()
    out = {}
    for n, b in raw.items():
        if not n.endswith("_metadata.json"):
            continue
        md = json.loads(b)
        arr = raw.get(n[:-len("_metadata.json")] + "_array.npy", b"")
        dp = md.get("datapath", n)
        if dp in out:
            dp = dp + "#" + n
        out[dp] = ({k: v for k, v in md.items() if k != "arrays"}, arr)
    return out, len(raw)
a, na = members(sys.argv[1]); b, nb = members(sys.argv[2])
chg_arr = sorted(k for k in a if k in b and a[k][1] != b[k][1])
md_keys = collections.Counter()
for k in a:
    if k in b and a[k][0] != b[k][0]:
        x, y = a[k][0], b[k][0]
        for kk in set(x) | set(y):
            if x.get(kk) != y.get(kk):
                md_keys[kk] += 1
res = dict(files_new=na, files_old=nb, datapaths_new=len(a), datapaths_old=len(b),
           only_new=sorted(k for k in a if k not in b)[:10], n_only_new=sum(k not in b for k in a),
           n_only_old=sum(k not in a for k in b), changed_arrays=len(chg_arr), changed_arrays_first=chg_arr[:10],
           metadata_keys_changed=dict(md_keys))
res["identical"] = (res["n_only_new"] == 0 and res["n_only_old"] == 0 and not chg_arr
                    and set(md_keys) <= {"input_file"})
print(json.dumps(res))
