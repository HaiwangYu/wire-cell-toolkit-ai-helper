#!/bin/bash
# r8: the r7 samples (MC CV, MC nueCC, beam-off) through the updated chain (2-step + truth match
# #41 + CAF merge #39 + the dl-vtx dump), ai-helper #42.  Resume: rerun this script.
#   validation/<sample>  ~100 events, WC_KEEP=validation (Bee + tracking-pr.root + merged CAF + qlpctree)
#   semiprod/<sample>    all events, WC_KEEP=semiprod   (tracking-pr.root + merged CAF + qlpctree)
# One budget for all six pools, set by bin/load-governor.sh from the other users' load
# (< 20 % CPU and memory -> 60 %, else 30 %), control dir control/.
O=/exp/sbnd/data/users/yuhw/production-prep/r8-r26-truth-caf
A=/exp/sbnd/app/users/yuhw/sbnd-wirecell-production/aurora
export KRB5CCNAME=FILE:/tmp/krb5cc_53514_r8campaign
export WC_CONTROL_DIR=$O/control
klist -s || { echo "no valid Kerberos ticket in $KRB5CCNAME: run  KRB5CCNAME=$KRB5CCNAME ~/utilities/fnal-auth.sh start"; exit 1; }
# the governor and the hourly ticket renewal (one each)
ps -u "$USER" -o args= | grep -q '[l]oad-governor.sh '"$O/control" || { rm -f $O/control/STOP; nohup $A/bin/load-governor.sh $O/control > /dev/null 2>&1 & }
ps -u "$USER" -o args= | grep -q '[k]rb-renew-r8' || nohup bash -c 'exec -a krb-renew-r8 bash -c "while :; do kinit -R 2>&1 | sed \"s/^/\$(/bin/date +%F_%T) /\"; echo \"\$(/bin/date +%F_%T) \$(klist 2>/dev/null | grep -A1 krbtgt | tail -1)\"; sleep 3600; done"' >> $O/control/krb-renew.log 2>&1 &
sleep 5
for s in mc-cv mc-nuecc beam-off; do
  WC_KEEP=validation nohup $A/bin/run-pairs.sh $A/site/fnal-sbndbuild03-governed.sh $O/lists/validation-$s.tsv $O/validation/$s > $O/validation-$s.out 2>&1 &
done
sleep 120   # the validation pairs take the first slots
for s in mc-cv mc-nuecc beam-off; do
  WC_KEEP=semiprod nohup $A/bin/run-pairs.sh $A/site/fnal-sbndbuild03-governed.sh $O/lists/semiprod-$s.tsv $O/semiprod/$s > $O/semiprod-$s.out 2>&1 &
done
echo "launched $(date)"
