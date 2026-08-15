import sys, zipfile, re, os
# merge_bee.py <out.zip> <evt0.zip> <evt1.zip> ...  -> renumber index dir 0->k
out = sys.argv[1]; ins = sys.argv[2:]
pat = re.compile(r'^([^/]+)/(\d+)/(\d+)-(.*)$')
with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as zo:
    for k, fn in enumerate(ins):
        if not os.path.exists(fn):
            print("  MISSING", fn); continue
        with zipfile.ZipFile(fn) as zi:
            for n in zi.namelist():
                m = pat.match(n)
                if not m:
                    continue  # skip anything not matching prefix/idx/idx-set
                prefix, _d1, _d2, rest = m.groups()
                newname = "%s/%d/%d-%s" % (prefix, k, k, rest)
                zo.writestr(newname, zi.read(n))
        print("  +evt%d <- %s" % (k, os.path.basename(os.path.dirname(fn))))
print("wrote", out)
