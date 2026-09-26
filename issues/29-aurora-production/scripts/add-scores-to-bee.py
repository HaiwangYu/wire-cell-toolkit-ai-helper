#!/usr/bin/env python3
"""Put the BDT scores into the Bee "mc" summary text of Xin's standalone PR-job zips.
usage: add-scores-to-bee.py <scores.json> <in dir of bee_<E>.zip> <out dir>

Xin's PR job (sbnd_xin/wct-pr-perevt.jsonnet) dumps the Bee particle-flow layer with
bee_pf.visitor = TaggerCheckNeutrino:pr, i.e. BEFORE UbooneNumuBDTScorer / UbooneNueBDTScorer run,
so MultiAlgBlobClustering::pf_summary_node prints "numu 0.000 nue 0.000".  The scores exist in his
tracking-pr.root (T_tagger.numu_score / nue_score, written by UbooneTaggerOutputVisitor after the
scorers).  This rewrites the summary node's text with those values in the toolkit's own format
("reco nu  %.1f MeV   numu %.3f   nue %.3f", pf_summary_node) -- nothing else in the zip changes.
Events without a candidate (no T_tagger entry) keep their marker text."""
import sys, json, zipfile, re, os, glob
scores = json.load(open(sys.argv[1])); IN, OUT = sys.argv[2], sys.argv[3]; os.makedirs(OUT, exist_ok=True)
pat = re.compile(r'^([^/]+)/(\d+)/(\d+)-(.*)$'); n = nrep = 0
def fix(nodes, s):
    c = 0
    for node in nodes:
        t = node.get('text', '')
        if t.startswith('reco nu') and 'numu' in t and s.get('numu_score') is not None:
            node['text'] = 'reco nu  %.1f MeV   numu %.3f   nue %.3f' % (s['kine_reco_Enu'], s['numu_score'], s['nue_score']); c += 1
        c += fix(node.get('children', []), s)
    return c
for z in sorted(glob.glob(IN + '/bee_*.zip')):
    e = os.path.basename(z)[4:-4]; zi = zipfile.ZipFile(z); zo = zipfile.ZipFile(os.path.join(OUT, os.path.basename(z)), 'w', zipfile.ZIP_DEFLATED); n += 1
    for info in zi.infolist():
        data = zi.read(info.filename); m = pat.match(info.filename)
        if m and m.group(4) == 'mc.json' and e in scores:
            j = json.loads(data); c = fix(j, scores[e])
            if c: nrep += 1; data = json.dumps(j, separators=(',', ':')).encode()
        zo.writestr(info, data)
    zo.close()
print('patched', nrep, 'of', n, 'zips ->', OUT)
