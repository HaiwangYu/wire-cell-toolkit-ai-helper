#!/bin/bash
# Full open FixedDev BNB data run: 1,817 pairs / 89,946 events, 2-step + CAF merge, keep-minimal.
#   nohup ./launch.sh > launch.out 2>&1 &      (rerun the same command to resume)
# 60 % of sbndbuild03 (site/fnal-sbndbuild03-60pct.sh): 38 pairs at night and on weekends, 19 Mon-Fri 08-20.
# Kerberos: the campaign cache renewed hourly by production-prep/r6-dlvtx-r26-samples/krb-renew.sh.
W=/exp/sbnd/data/users/yuhw/production-prep/opendata-fixeddev-prep
A=/exp/sbnd/app/users/yuhw/sbnd-wirecell-production/aurora
export KRB5CCNAME=FILE:/tmp/krb5cc_53514_r6campaign
export WC_KEEP=minimal
exec $A/bin/run-pairs.sh $A/site/fnal-sbndbuild03-60pct.sh $W/pairs.tsv $W/run
