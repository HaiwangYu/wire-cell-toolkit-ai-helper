#!/bin/bash
# After the main harness finishes: re-run every rc!=0 / audit!=ok row into run-retry/, then merge into run/ and write summary-merged.csv
P=/exp/sbnd/data/users/yuhw/production-prep/r3-mc-cv-2026-09-09
H=/exp/sbnd/data/users/yuhw/wcp-porting-img/sbnd/img-clus-matching-eval/prabhjot-100file-Aug5-debug-25evt/chain/scripts/run-harness.sh
SL7=/exp/sbnd/app/users/yuhw/claude-utilities/in-gpvm-sl7.sh
until grep -q MCCV_DONE $P/harness.log; do sleep 60; done
echo "main harness done $(/bin/date)"; grep "harness done" $P/harness.log
python3 - $P <<'PY'
import csv,sys
P=sys.argv[1]
bad=[(x['run'],x['subrun'],x['event']) for x in csv.DictReader(open(P+'/run/summary.csv')) if x['rc']!='0' or x['audit']!='ok' or x.get('rse_check')!='ok']
badset=set(bad); n=0
with open(P+'/lists/retry.manifest','w') as fh:
    for l in open(P+'/lists/mc.manifest'):
        f,k,r,s,e=l.rstrip('\n').split('\t')
        if (r,s,e) in badset: fh.write(l); n+=1
print('retry manifest rows',n,'of',len(bad),'bad rows')
PY
$SL7 bash -c "$H $P/lists/retry.manifest $P/run-retry 20 1 wcls-img-clus-matching-xin.fcl" > $P/harness-retry.log 2>&1
echo "RETRY_RC=$?"; grep "harness done" $P/harness-retry.log
# merge: copy deliverables, then summary rows (retry row replaces the failed one)
cp -n $P/run-retry/bee/*.zip $P/run/bee/ 2>/dev/null; cp -n $P/run-retry/tracking-pr/*.root $P/run/tracking-pr/ 2>/dev/null
python3 - $P <<'PY'
import csv,sys
P=sys.argv[1]
main=list(csv.DictReader(open(P+'/run/summary.csv'))); retry={(x['run'],x['subrun'],x['event']):x for x in csv.DictReader(open(P+'/run-retry/summary.csv'))}
out=[]; rep=0
for x in main:
    k=(x['run'],x['subrun'],x['event'])
    if k in retry and (x['rc']!='0' or x['audit']!='ok'): x=dict(retry[k]); x['task']='retry:'+x['task']; rep+=1
    out.append(x)
w=csv.DictWriter(open(P+'/run/summary-merged.csv','w'),fieldnames=list(main[0].keys())); w.writeheader(); w.writerows(out)
ok=[x for x in out if x['rc']=='0' and x['audit']=='ok' and x.get('rse_check')=='ok']
print('merged rows',len(out),'replaced',rep,'ok',len(ok),'still bad',len(out)-len(ok))
for x in out:
    if not (x['rc']=='0' and x['audit']=='ok'): print('  STILL BAD',x['run'],x['subrun'],x['event'],'rc',x['rc'],'audit',x['audit'])
PY
echo "RETRY_DONE $(/bin/date)"
