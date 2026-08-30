#!/usr/bin/env python3
"""Generate sbnd/pr-operating-point.jsonnet: the SBND PR operating point as a
wrapper around clus_maker.pr(), so the 1-step chain reconstructs with the same
knobs as Xin's 2-step wct-pr-perevt.jsonnet.

  gen-pr-operating-point.py <compiled_dir> <clus.jsonnet> <out.jsonnet>

WHY GENERATED, NOT HAND-WRITTEN (issue 17): wct-pr-perevt.jsonnet passes 351
named args to clus_maker.pr(); our 1-step passed 7.  Hand-copying them is what
let the two drift apart in the first place, so this reads the values mechanically
and can be re-run whenever the owner flips more knobs.

VALUES come from the COMPILED Xin config, not from parsing jsonnet source: the
call site contains expressions ("pr_y_top - 17", "[t * wc.us for t in ...]")
that are already resolved to plain numbers after compilation.  Internal units
are preserved because clus.jsonnet forwards these values unscaled (its own
"5 * wc.cm" occurrences are signature DEFAULTS, replaced when a value is passed).

NAMES come from clus.jsonnet's pr() signature: identity where the component key
and the pr() argument agree (most), else a unique suffix match for the prefixed
ones (cathode_rejoin_angle -> protect_cathode_rejoin_angle).

The name heuristic is allowed to be imperfect BECAUSE the acceptance test is
exact: compile-both.sh must report 0 differences.  A mis-mapped name means the
knob never takes effect and the gate stays non-zero -- loud, not silent.
"""
import json, sys, os, re, subprocess

compiled, clus_path, out_path = sys.argv[1], sys.argv[2], sys.argv[3]

def idx(p):
    d = {}
    for c in json.load(open(p)):
        if isinstance(c, dict) and 'type' in c:
            d[(c['type'], c.get('name', ''))] = c.get('data', {})
    return d

ours = idx(os.path.join(compiled, 'onestep.json'))
xin  = idx(os.path.join(compiled, 'xin-both.json'))

# pr() argument names
sig = subprocess.run(
    ["awk", "NR>=2966 && NR<=3620", clus_path], capture_output=True, text=True).stdout
# ALL names on a line, not just the first: the signature packs several per line
# (e.g. "main_vertex_require_descriptor=false, main_vertex_candidate_flag=false,"),
# and an anchored ^ regex silently drops every one but the first.
pr_args = sorted(set(re.findall(r'(?:^|[,(\s])([a-z_0-9]+)\s*=', sig, re.M)))

# Components whose knobs are configured THROUGH pr().  clus_all_apa's own two
# (save_bundle_main_provenance, bee_flash_pred_min) are handled by the caller,
# not here -- they belong to a different clus maker function.
PR_COMPONENTS = ['TaggerCheckNeutrino', 'ClusteringProtectBundle', 'CreateSteinerGraph',
                 'ClusteringUnmergeBundle', 'TaggerCheckTGM', 'TaggerCheckSTM',
                 'TaggerCheckFC', 'UbooneTaggerOutputVisitor']

# A few component keys are DERIVED inside clus_pr() from an upstream pr()
# argument rather than being settable directly, e.g.
#   fv_tolerance=(if stm_consistent_fv then sbnd_pr_fv_margins else [])
#   exempt_demoted_main_pairs=tgm_exempt_demoted_main
#   nu_per_bundle_demoted_acts=evaluate_demoted_mains
# Map them to that upstream argument; the value becomes the boolean that selects
# the non-default branch.  `fiducial` is a component REFERENCE that clus_pr()
# constructs itself (BoxFiducial:sbnd_pr_fv) -- not a knob, so it is skipped and
# is expected to match once the fiducial config agrees.
# Keyed by (component type, data key): the SAME key is driven by DIFFERENT
# arguments on different components -- fv_tolerance comes from
# stm_consistent_fv on TaggerCheckSTM but neutrino_consistent_fv on
# TaggerCheckNeutrino -- so a global map silently mis-assigns it.
DERIVED = {
    ('TaggerCheckSTM',      'fv_tolerance'):               'stm_consistent_fv',
    ('TaggerCheckNeutrino', 'fv_tolerance'):               'neutrino_consistent_fv',
    ('TaggerCheckNeutrino', 'fiducial'):                   'neutrino_consistent_fv',
    ('TaggerCheckTGM',      'exempt_demoted_main_pairs'):  'tgm_exempt_demoted_main',
    ('TaggerCheckNeutrino', 'nu_per_bundle_demoted_acts'): 'evaluate_demoted_mains',
}

def pr_arg_for(knob):
    """component data key -> pr() argument name."""
    if knob in pr_args:
        return knob
    cands = [a for a in pr_args if a.endswith('_' + knob)]
    if len(cands) == 1:
        return cands[0]
    return None   # ambiguous or absent: reported, and the gate will catch it

wanted, unmapped, ambiguous = {}, [], []
for (ty, nm), xdata in sorted(xin.items()):
    if ty not in PR_COMPONENTS:
        continue
    odata = ours.get((ty, nm), {})
    for k in sorted(xdata):
        # Baseline is the BARE 1-step: pr() called with structural arguments
        # only, no operating point.  Diffing against that (rather than against
        # whatever the 1-step currently sets) is what makes the generated file
        # self-contained without dragging in component wiring -- keys like
        # detector_volumes/grouping/pcarray_name are identical in both and drop
        # out, while a knob the 1-step used to set BY HAND (iso_endpoint) is
        # correctly included instead of being silently skipped as "already
        # agrees".
        if k in odata and odata[k] == xdata[k]:
            continue
        if (ty, k) in DERIVED:
            a = DERIVED[(ty, k)]
            # non-empty / true selects the branch that yields Xin's value
            v = bool(xdata[k]) if not isinstance(xdata[k], (list, dict)) else len(xdata[k]) > 0
            if a in wanted and wanted[a][0] != v:
                ambiguous.append("%s:%s.%s (derived, conflicts on '%s')" % (ty, nm, k, a))
            else:
                wanted[a] = (v, "%s:%s" % (ty, nm), k + " (derived)")
            continue
        a = pr_arg_for(k)
        if a is None:
            (ambiguous if [x for x in pr_args if x.endswith('_' + k)] else unmapped).append(
                "%s:%s.%s" % (ty, nm, k))
            continue
        # A pr() arg feeding two components must not get two different values.
        if a in wanted and wanted[a][0] != xdata[k]:
            ambiguous.append("%s:%s.%s (conflicting values for pr arg '%s')" % (ty, nm, k, a))
            continue
        wanted[a] = (xdata[k], "%s:%s" % (ty, nm), k)

src = subprocess.run(["git", "-C", os.path.dirname(clus_path), "rev-parse", "--short", "HEAD"],
                     capture_output=True, text=True).stdout.strip()

lines = [
 "// GENERATED by scripts/gen-pr-operating-point.py -- DO NOT EDIT BY HAND.",
 "//",
 "// The SBND pattern-recognition operating point, as a wrapper around",
 "// clus_maker.pr().  Source of truth: the 351 TLA defaults of",
 "// cfg/pgrapher/experiment/sbnd/wct-pr-perevt.jsonnet (toolkit %s), which is" % (src or "?"),
 "// where the owner records each 'SBND PRODUCTION ON <date>' flip.  The 1-step",
 "// chain calls clus_maker.pr() directly and so never saw those values; see",
 "// ai-helper issue 17.  Regenerate after the owner flips more knobs:",
 "//",
 "//   scripts/compile-both.sh <dir> ; scripts/gen-pr-operating-point.py <dir> \\",
 "//       <clus.jsonnet> sbnd/pr-operating-point.jsonnet",
 "//",
 "// Acceptance test is exact, not by inspection: compile-both.sh must report 0",
 "// differences on the PR components.",
 "//",
 "// %d knobs synchronised." % len(wanted),
 "",
 "function(clus_maker, anodes, dump=false, bee_sink=null, pipeline_names=[],",
 "         particle_dataset=null, extra_uses=[], beam_window=null, tensor_outname='')",
 "  clus_maker.pr(",
 "    anodes, dump=dump, bee_sink=bee_sink, pipeline_names=pipeline_names,",
 "    particle_dataset=particle_dataset, extra_uses=extra_uses,",
 "    beam_window=beam_window, tensor_outname=tensor_outname,",
 "",
 "    // ---- generated operating point ----",
]
for a in sorted(wanted):
    v, comp, key = wanted[a]
    note = "" if a == key else "  // %s.%s" % (comp, key)
    lines.append("    %s=%s,%s" % (a, json.dumps(v), note))
lines[-1] = lines[-1].replace(",  //", ")  //", 1) if lines[-1].rstrip().endswith(",") is False else lines[-1]
# close the call cleanly
lines.append("  )")
open(out_path, 'w').write("\n".join(lines) + "\n")

print("  synchronised knobs : %d" % len(wanted))
print("  unmapped (no pr arg): %d %s" % (len(unmapped), unmapped[:8]))
print("  ambiguous          : %d %s" % (len(ambiguous), ambiguous[:8]))
print("  wrote %s" % out_path)
