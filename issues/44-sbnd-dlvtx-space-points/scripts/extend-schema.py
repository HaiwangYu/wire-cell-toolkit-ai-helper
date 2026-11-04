#!/usr/bin/env python3
"""Append the branches of a reference schema that the current schema lacks (ai-helper issue 44).
    extend-schema.py <current schema> <reference schema> <out>
Every existing branch keeps its position; a name present in both must have the same type/count."""
import json, sys, hashlib
old, ref = json.load(open(sys.argv[1])), json.load(open(sys.argv[2]))
on = {b['name']: b for b in old['branches']}
bad = [b['name'] for b in ref['branches'] if b['name'] in on and on[b['name']] != b]
if bad: sys.exit('type/count conflicts: %s' % bad[:5])
add = [b for b in ref['branches'] if b['name'] not in on]
new = dict(old)
new['branches'] = old['branches'] + add
new['trees'] = sorted(set(old['trees']) | set(ref['trees']))
new['references'] = old['references'] + ref['references']
s = json.dumps(new, indent=1)
open(sys.argv[3], 'w').write(s)
print('%s: %d + %d = %d branches, md5 %s' % (sys.argv[3], len(old['branches']), len(add), len(new['branches']), hashlib.md5(s.encode()).hexdigest()))
for b in add: print('  +', b['name'], b['type'], b['count'])
