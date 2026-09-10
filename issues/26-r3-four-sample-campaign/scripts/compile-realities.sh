#!/bin/bash
W=$1; cd /exp/sbnd/app/users/yuhw/wcp-porting-img/sbnd; export WIRECELL_PATH=/exp/sbnd/app/users/yuhw/wire-cell-toolkit/cfg:/exp/sbnd/app/users/yuhw/wire-cell-data:$WIRECELL_PATH
PIPE="switch_scope,unmerge_bundle,unmerge_assoc,steiner,fiducialutils,tagger_check_tgm,tagger_check_stm,tagger_check_fc,protect_bundle,steiner_refresh,tagger_check_neutrino,numu_bdt_scorer,nue_bdt_scorer,tracking_visitor,tagger_output"
PIPE_TLA="pipeline_names=[$(echo "$PIPE" | sed "s/[^,]\+/'&'/g")]"
for R in sim data; do
  if [ $R = sim ]; then TAG=simtpc2d; else TAG=sptpc2d; fi
  wcsonnet --ext-str reality=$R --ext-str enable_tracking_root=true --ext-str enable_nugraph_h5=false --ext-str pr_operating_point=sync \
    --ext-code "recobwire_tags=[\"$TAG:dnnsp\", \"$TAG:dnnsp\"]" --ext-code 'trace_tags=["gauss", "wiener"]' --ext-code "summary_tags=[\"\", \"$TAG:wienersummary\"]" \
    --ext-code "input_mask_tags=[\"$TAG:badmasks\"]" --ext-code 'output_mask_tags=["bad"]' --ext-str opflash0_input_label=opflashtpc0: --ext-str opflash1_input_label=opflashtpc1: \
    wcls-img-clus-matching-xin.jsonnet > $W/ours-$R.json || echo "ours $R FAILED"
  wcsonnet --tla-str reality=$R pgrapher/experiment/sbnd/wct-clus-matching-perevt.jsonnet > $W/xin1-$R.json || echo "xin1 $R FAILED"
  wcsonnet --tla-str reality=$R --tla-code "$PIPE_TLA" pgrapher/experiment/sbnd/wct-pr-perevt.jsonnet > $W/xin2-$R.json || echo "xin2 $R FAILED"
done
python3 - $W <<'PY'
import json,sys
W=sys.argv[1]
def flat(o,p='',out=None):
    out={} if out is None else out
    if isinstance(o,dict):
        for k,v in o.items(): flat(v,p+'/'+str(k),out)
    elif isinstance(o,list):
        for i,v in enumerate(o): flat(v,p+'['+str(i)+']',out)
    else: out[p]=o
    return out
def bynode(cfg):
    d={}
    for c in cfg:
        if not isinstance(c,dict) or 'type' not in c: continue
        d[c['type']+':'+str(c.get('name',''))]=c.get('data',{})
    return d
for arm in ['ours','xin1','xin2']:
    a=bynode(json.load(open(f'{W}/{arm}-sim.json'))); b=bynode(json.load(open(f'{W}/{arm}-data.json')))
    diffs=[]
    for k in sorted(set(a)|set(b)):
        if k not in a: diffs.append((k,'<only data>','')); continue
        if k not in b: diffs.append((k,'<only sim>','')); continue
        fa,fb=flat(a[k]),flat(b[k])
        for kk in sorted(set(fa)|set(fb)):
            if fa.get(kk)!=fb.get(kk): diffs.append((k+kk,fa.get(kk,'<absent>'),fb.get(kk,'<absent>')))
    print(f'### {arm}: {len(diffs)} sim-vs-data differences')
    for k,x,y in diffs: print('  %-90s sim=%s  data=%s'%(k[:90],str(x)[:50],str(y)[:50]))
PY
