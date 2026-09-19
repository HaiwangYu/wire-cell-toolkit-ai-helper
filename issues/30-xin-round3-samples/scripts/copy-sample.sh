#!/bin/bash
# copy-sample.sh <mc-cv|mc-nuecc> : copy the listed /pnfs reco1 files into <sample>/reco1/, then verify sizes
X=/exp/sbnd/data/users/yuhw/production-prep/xin-round3-samples; S=$1
cat $X/$S/lists/reco1-files.lst | xargs -P 3 -I{} sh -c 'f={}; b=$(basename $f); [ -s '$X/$S'/reco1/$b ] || cp $f '$X/$S'/reco1/$b.tmp && mv '$X/$S'/reco1/$b.tmp '$X/$S'/reco1/$b 2>/dev/null; true'
n=0; bad=0; while read f; do b=$(basename $f); [ "$(stat -c %s $f)" = "$(stat -c %s $X/$S/reco1/$b 2>/dev/null)" ] && n=$((n+1)) || { bad=$((bad+1)); echo "SIZE MISMATCH/MISSING $b"; }; done < $X/$S/lists/reco1-files.lst
echo "COPY_DONE $S ok=$n bad=$bad $(du -sh $X/$S/reco1 | cut -f1) $(/bin/date)"
