#!/bin/bash
# keep the Kerberos ticket alive for the campaign (FNAL: 26 h lifetime, renewable 7 days). Log each renewal.
while :; do kinit -R 2>&1 | sed "s/^/$(/bin/date '+%F %T') /"; echo "$(/bin/date '+%F %T') renewed; $(klist 2>/dev/null | grep -A1 krbtgt | tail -1 | sed 's/^ *//')"; sleep 3600; done
