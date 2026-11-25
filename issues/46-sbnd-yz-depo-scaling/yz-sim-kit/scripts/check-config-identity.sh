#!/bin/bash
# Compile the Wire-Cell configuration of three detsim fcls exactly as lar would
# (same params/structs, same WIRECELL_PATH) and compare the JSON:
#   stock: sbndcode's standard_detsim_sbnd.fcl
#   off:   the kit's detsim_sbnd_yz_off.fcl   -> must be IDENTICAL to stock
#   on:    the kit's detsim_sbnd_yz_on.fcl    -> only DepoTransformYZ + YZMap differ
# Usage (inside the kit env, see setup-yz-env.sh): check-config-identity.sh <outdir>
set -o pipefail
OUT=${1:?usage: check-config-identity.sh <outdir>}
[[ -n "$YZ_KIT" ]] || { echo "source setup-yz-env.sh first" >&2; exit 2; }
WCSONNET=${WCSONNET:-$YZ_WCT_LIB/../bin/wcsonnet}
mkdir -p "$OUT" && cd "$OUT" || exit 1

declare -A FCL=([stock]=standard_detsim_sbnd.fcl [off]=detsim_sbnd_yz_off.fcl [on]=detsim_sbnd_yz_on.fcl)
for m in stock off on; do
    lar -c "${FCL[$m]}" --debug-config "fcl_$m.fcl" > "fcl_$m.log" 2>&1 || { echo "lar --debug-config ${FCL[$m]} failed" >&2; exit 1; }
    mapfile -t ARGS < <(python3 "$YZ_KIT/scripts/fcl_wcls_args.py" "fcl_$m.fcl")
    printf '%s\n' "${ARGS[@]}" > "wcsonnet_args_$m.txt"
    "$WCSONNET" "${ARGS[@]}" -o "cfg_$m.raw.json" > "wcsonnet_$m.log" 2>&1 || { echo "wcsonnet $m failed, see $OUT/wcsonnet_$m.log" >&2; exit 1; }
    # Pretty, key-sorted copy for diffing.
    python3 -c 'import json,sys; json.dump(json.load(open(sys.argv[1])), open(sys.argv[2],"w"), indent=1, sort_keys=True)' "cfg_$m.raw.json" "cfg_$m.json"
done

echo "== stock vs off (expect no difference)"
if cmp -s cfg_stock.json cfg_off.json; then
    echo "IDENTICAL: $(wc -c < cfg_off.json) bytes, sha256 $(sha256sum < cfg_off.json | cut -c1-16)"
else
    echo "DIFFERENT"; diff cfg_stock.json cfg_off.json | head -50; exit 1
fi
echo "== stock vs on (expect DepoTransform -> DepoTransformYZ + YZMap)"
diff cfg_stock.json cfg_on.json > diff_stock_on.txt
python3 - <<'EOF'
import json
a = json.load(open("cfg_stock.json")); b = json.load(open("cfg_on.json"))
key = lambda c: (c["type"], c.get("name", ""))
A = {key(c): c for c in a}; B = {key(c): c for c in b}
print("components only in stock:", sorted(set(A) - set(B)))
print("components only in on:   ", sorted(set(B) - set(A)))
for k in sorted(set(A) & set(B)):
    if A[k] != B[k]:
        print("changed:", k)
# The DepoTransformYZ data must equal the DepoTransform data + yzmap keys.
for ka in [k for k in A if k[0] == "DepoTransform"]:
    kb = ("DepoTransformYZ", ka[1].replace("depotransform-", "depotransformyz-"))
    da, db = dict(A[ka]["data"]), dict(B[kb]["data"])
    extra = {k: db.pop(k) for k in ("yzmap", "yzmap_key")}
    print(f"{ka[1]} -> {kb[1]}: data equal apart from yzmap keys: {da == db}; {extra}")
EOF
