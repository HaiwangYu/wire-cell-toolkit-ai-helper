#!/usr/bin/env python3
"""Print the wcsonnet arguments that a lar job's WireCellToolkit module uses.

Reads the post-processed fcl written by `lar -c <fcl> --debug-config <out.fcl>`
and turns physics.producers.<label>.wcls_main into wcsonnet arguments:
params -> -V key=value (strings), structs -> -C key=value (code), and the
first configs entry as the file.  This mirrors larwirecell's WCLS tool
(add_var for params, add_code for structs).

Usage: fcl_wcls_args.py <debug-config.fcl> [label=simtpc2d]
Output: one argument per line (NUL-free), ready for `mapfile -t`.
"""
import re
import sys

path = sys.argv[1]
label = sys.argv[2] if len(sys.argv) > 2 else "simtpc2d"
lines = open(path).read().splitlines()

# Find "<label>: {" under producers, then wcls_main's params / structs / configs.
start = next(i for i, l in enumerate(lines) if l.strip() == f"{label}: {{")
depth, block = 0, []
for l in lines[start:]:
    depth += l.count("{") - l.count("}")
    depth += l.count("[") - l.count("]")
    block.append(l)
    if depth == 0:
        break


def table(name):
    i = next(i for i, l in enumerate(block) if l.strip() == f"{name}: {{")
    out = {}
    for l in block[i + 1:]:
        s = l.strip()
        if s == "}":
            return out
        m = re.match(r'^([A-Za-z0-9_]+):\s*(.*)$', s)
        if not m:
            raise SystemExit(f"cannot parse line in {name}: {l!r}")
        out[m.group(1)] = m.group(2)
    raise SystemExit(f"unterminated table {name}")


def unquote(v):
    if len(v) >= 2 and v[0] == '"' and v[-1] == '"':
        return v[1:-1]
    return v


i = next(i for i, l in enumerate(block) if l.strip() == "configs: [")
config = unquote(block[i + 1].strip().rstrip(","))
args = []
for k, v in sorted(table("params").items()):
    args += ["-V", f"{k}={unquote(v)}"]
for k, v in sorted(table("structs").items()):
    args += ["-C", f"{k}={unquote(v)}"]
args.append(config)
print("\n".join(args))
