source /nashome/y/yuhw/.bashrc >/dev/null 2>&1; source /exp/sbnd/app/users/yuhw/wcp-porting-img/sbnd/setup-local-opt.sh >/dev/null 2>&1; setup sam_web_client >/dev/null 2>&1; export SAM_EXPERIMENT=sbnd
W=/exp/sbnd/data/users/yuhw/production-prep/r8-prep; mkdir -p $W/meta; cd $W/meta
split -l 400 -d -a 3 $W/beam-off-cand-files.txt part-
for c in part-*; do [ -s $c.json ] || samweb get-metadata --json $(cat $c) > $c.json; done
echo META_DONE
