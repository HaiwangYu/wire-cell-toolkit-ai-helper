"""Fetch the Bee layers the deck needs (track_fit-global, mc) for the three methods, per event, into a cache dir.
usage: fetch_bee.py <prod_polaris dir> <porting tables dir> <cache dir>"""
import csv, json, os, re, sys, urllib.request
P, T, CACHE = sys.argv[1:4]
os.makedirs(CACHE, exist_ok=True)
SETS = {"orig": "89cdea53-c227-476c-8f67-0ae765f804b4", "aur": "431dc57f-997d-4cff-88e1-4e33fd743ab8"}
SHEET_FIX = {(18255, 234538): (18255, 234638), (18355, 40074): (18355, 400474)}
def get(uuid, idx, layer):
    f = f"{CACHE}/{uuid[:8]}-{idx}-{layer}.json"
    if not os.path.exists(f):
        u = f"https://www.phy.bnl.gov/twister/bee/set/{uuid}/event/{idx}/{layer}/"
        txt = urllib.request.urlopen(u, timeout=60).read().decode()
        if not txt.lstrip().startswith(("{", "[")): txt = "null"
        open(f, "w").write(txt)
    return f
jobs = []
for r in csv.DictReader(open(f"{T}/data-orig-vs-aur-event.csv")):
    for arm in ("orig", "aur"):
        jobs.append((SETS[arm], int(r[f"{arm}_bee"])))
for tab in ("nuecc", "ncpi0"):
    R = list(csv.reader(open(f"{P}/tables/handscan-xin-r2-{tab}.csv")))
    i = [k for k, r in enumerate(R) if r and r[0].lower().startswith("round 2")][0]
    for r in R[i + 1:]:
        if r and re.match(r"\d+-\d+", r[0]):
            m = re.search(r"/set/([0-9a-f-]+)/event/(\d+)", r[1]); jobs.append((m.group(1), int(m.group(2))))
n = 0
for uuid, idx in jobs:
    for layer in ("track_fit-global", "mc", "vertices-global"):
        get(uuid, idx, layer); n += 1
print("fetched/cached", n, "layers for", len(jobs), "events-x-sets")
