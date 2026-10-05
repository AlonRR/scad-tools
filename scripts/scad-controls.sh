#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Alon A. Rabinowitz
# SPDX-License-Identifier: MPL-2.0

# Run every control in a model README's "Guards" block and say whether each one fired its guard.
#
#   scripts/scad-controls.sh models/usbc-panel-plate [PART]
#
# A control is a line in the README between "## Guards" and "defaults":
#
#   -D sel_gap=0.5                -> no material between a leg's two ports       (blocks)
#
# It is rendered to a real STL with those -D values - an .echo export skips every assert, so it would
# pass vacuously - and judged by OpenSCAD's own exit code: "blocks" wants a non-zero exit, "warns" wants
# exit 0 with a WARNING echoed. The message that fired is printed beside it: an assert can fire for the
# wrong reason, so read it, not just the verdict. PART is the draw_part rendered (default fplug, a small
# one). Finally the defaults are rendered once and must be silent.
#
# Use OpenSCAD 2021.01 (the one on PATH here): the nightly prints a failed assert and exits 0, so on it
# every control reads as a pass that did not block.
set -u
DIR=${1:?usage: scad-controls.sh MODEL_DIR [PART]}
PART=${2:-fplug}
N=${OPENSCAD:-openscad}
cd "$DIR" || exit 2
MODEL=$(basename "$PWD").scad                 # models/<name>/<name>.scad
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
bad=0
while IFS= read -r line; do
    args=${line%%->*}; want=${line##*(}; want=${want%)}
    eval "set -- $args"
    out=$("$N" -o "$TMP/ctl.stl" -D "draw_part=\"$PART\"" "$@" "$MODEL" 2>&1); rc=$?
    msg=$(printf '%s\n' "$out" | grep -o 'Assertion.*failed: "[^"]*"\|WARNING: [^"]*' | grep -v 'draw_part is' | head -1 | sed 's/.*failed: //' | cut -c1-110)
    ok=BAD
    { [ "$want" = blocks ] && [ $rc -ne 0 ]; } && ok=ok
    { [ "$want" = warns ] && [ $rc -eq 0 ] && [ -n "$msg" ]; } && ok=ok
    [ $ok = BAD ] && bad=$((bad + 1))
    printf '%-4s %-40s rc=%s  %s\n' "$ok" "$args" "$rc" "$msg"
done < <(sed -n '/^## Guards/,/^defaults/p' README.md | grep '^-D')
out=$("$N" -o "$TMP/ctl.stl" -D "draw_part=\"$PART\"" "$MODEL" 2>&1); rc=$?
nw=$(printf '%s\n' "$out" | grep -c '^ECHO: "WARNING' || true)
# OpenSCAD's OWN warnings too - above all "x was assigned on line N": a second assignment of a name silently
# replaces the first everywhere, and nothing else reports it (25 Sep 2026: a new gasket_t quietly made the
# port gasket's grooves 0.8 deep instead of 1.4).
ns=$(printf '%s\n' "$out" | grep '^WARNING:' || true)
echo "defaults: rc=$rc, $nw model warnings, $(printf '%s' "$ns" | grep -c . || true) OpenSCAD warnings"
[ -n "$ns" ] && printf '  %s\n' "$ns"
{ [ $rc -ne 0 ] || [ "$nw" -ne 0 ] || [ -n "$ns" ]; } && bad=$((bad + 1))
echo "$bad unexpected"
exit $(( bad > 0 ))
