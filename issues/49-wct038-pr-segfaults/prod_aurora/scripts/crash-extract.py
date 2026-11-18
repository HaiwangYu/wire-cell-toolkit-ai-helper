"""#49 helper: from a step-2 wct.log.gz that ended in a segfault, report the tensor-set ident being processed,
the crashing thread's frames, and the 'aliased onto existing edge' lines of that ident; optionally cut a one-event
step-1 tar (members clustering_tensor[set]_<ident>_*) from the unit's qlpctree.tar.gz.
usage: crash-extract.py <wct.log.gz> [<qlpctree.tar.gz> <out.tar.gz>]"""
import sys, gzip, re, tarfile

log = gzip.open(sys.argv[1], "rt", errors="replace").read().split("\n")
crash = next((i for i, l in enumerate(log) if "*** Break ***" in l), None)
idents = [(i, int(m.group(1))) for i, l in enumerate(log[:crash])
          for m in [re.search(r"loading tensor set ident=(\d+)", l)] if m]
i0, ident = idents[-1] if idents else (0, None)
print(f"crash line {crash}; ident {ident} (tensor set #{len(idents)} of this run)")
print("last log lines:", *[l[:200] for l in log[max(i0, crash - 3):crash]], sep="\n  ")
print(f"'aliased onto existing edge' lines in ident {ident}: {sum('aliased onto existing edge' in l for l in log[i0:crash])}")
# the crashing thread: the one with '<signal handler called>'
for j in range(crash, len(log)):
    if "<signal handler called>" in log[j]:
        k = j + 1; out = []
        while k < len(log) and log[k].startswith("#") and len(out) < 8:
            out.append(re.sub(r"\(this=[^)]*\)", "", re.sub(r" at /\S+/include/", " at include/", log[k]))[:200]); k += 1
        print("frames after the signal handler:", *out, sep="\n  ")
        break
if len(sys.argv) > 3 and ident is not None:
    # idents repeat inside one tar when a unit spans several reco1 files: take the occurrence that crashed
    occ = sum(1 for _, x in idents if x == ident)
    pat = re.compile(rf"^clustering_tensor(set)?_{ident}_"); head = f"clustering_tensorset_{ident}_metadata.json"
    with tarfile.open(sys.argv[2]) as src, tarfile.open(sys.argv[3], "w:gz") as dst:
        n = seen = 0
        for m in src.getmembers():
            if m.name == head: seen += 1
            if pat.match(m.name) and seen == occ:
                dst.addfile(m, src.extractfile(m) if m.isfile() else None); n += 1
    print(f"wrote {sys.argv[3]}: {n} members of ident {ident}, occurrence {occ} of {seen} in the tar")
