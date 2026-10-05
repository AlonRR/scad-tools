#!/usr/bin/env sh
# SPDX-FileCopyrightText: 2026 Alon A. Rabinowitz
# SPDX-License-Identifier: MPL-2.0

# Render previews, cross-sections and thin slices of an OpenSCAD model.
#
#   scad-preview.sh MODEL.scad [OUTDIR] [SLICE_Z ...]
#
# Produces in OUTDIR (default: ./preview):
#   iso.png       three-quarter view
#   top.png       orthographic, looking down -Z
#   bottom.png    orthographic, looking up +Z
#   sec-xz.png    cross-section on the X-Z plane
#   sec-yz.png    cross-section on the Y-Z plane
#   slice-Z.png   thin wafer at each SLICE_Z given, looking straight down
#
# Sections and slices import the EXPORTED STL, not the .scad. That is the point: it checks the file you would actually slice, so a bug in the export path cannot hide behind a correct-looking render of the source.
#
# --camera is the gimbal form:  tx,ty,tz, rx,ry,rz, dist
set -eu

SCAD=${1:?usage: scad-preview.sh MODEL.scad [OUTDIR] [SLICE_Z ...]}
OUT=${2:-preview}
shift 2 2>/dev/null || shift 1
mkdir -p "$OUT"

CS=Tomorrow
STL="$OUT/_model.stl"
TMP="$OUT/_tmp.scad"

# Resolve the binaries. openscad is on PATH, but only for processes started AFTER it was added -- an older shell will not see it, so fall back to the install path rather than dying with a bare 127.
OPENSCAD=${OPENSCAD:-}
if [ -z "$OPENSCAD" ]; then
    if command -v openscad >/dev/null 2>&1; then OPENSCAD=openscad
    else OPENSCAD="/c/Program Files/OpenSCAD/openscad.exe"; fi
fi
[ -x "$OPENSCAD" ] || command -v "$OPENSCAD" >/dev/null 2>&1 || {
    echo "openscad not found; set OPENSCAD=/path/to/openscad" >&2; exit 1; }

# Optional: PrusaSlicer reports the bounding box, which is only used to pick a camera distance. Absent, fall back to a sane default.
PSLICER=${PSLICER:-/c/Program Files/Prusa3D/PrusaSlicer/prusa-slicer-console.exe}

# Absolute path for import(), which is resolved relative to the generated .scad rather than the working directory.
#
# MUST be a Windows path. OpenSCAD is a native binary and cannot open a Git Bash path like /c/Users/... -- it fails the import, renders an empty scene, and still exits 0, so you get a plausible blank PNG instead of an error. `pwd -W` gives C:/Users/...; plain `pwd` does not.
abspath() (
    cd "$(dirname "$1")" || exit 1
    d=$(pwd -W 2>/dev/null) || d=$(pwd)
    printf '%s/%s\n' "$d" "$(basename "$1")"
)

echo "==> exporting STL"
"$OPENSCAD" -o "$STL" "$SCAD" 2>&1 | grep -Ei 'ECHO|WARNING|ERROR|Assert' || true
[ -s "$STL" ] || { echo "STL export produced nothing -- check the asserts above" >&2; exit 1; }
STL_ABS=$(abspath "$STL")

# Bounding box, only used to pick a camera distance. PrusaSlicer reports it; without it, fall back to a default rather than failing.
INFO=$("$PSLICER" --info "$STL" 2>/dev/null || true)
SIZE=$(printf '%s\n' "$INFO" | awk -F= '/size_[xyz]/ {gsub(/ /,"",$2); print $2+0}' | sort -g | tail -1)
MIDZ=$(printf '%s\n' "$INFO" | awk -F= '/size_z/ {gsub(/ /,"",$2); printf "%.2f", ($2+0)/2}')
[ -n "${SIZE:-}" ] && [ "$SIZE" != "0" ] || SIZE=30
[ -n "${MIDZ:-}" ] || MIDZ=0
DIST=$(awk -v s="$SIZE" 'BEGIN { printf "%.1f", s * 2.2 }')
# A cross-section is a thin profile, not the whole silhouette, so the distance that frames the model leaves it a speck. Sections get their own, tighter one.
SECDIST=$(awk -v s="$SIZE" 'BEGIN { printf "%.1f", s * 0.9 }')
echo "    largest dimension $SIZE mm -> camera $DIST (model) / $SECDIST (sections)"

# Never swallow OpenSCAD's stderr here. A failed import is only a WARNING and still exits 0, so silence turns a broken render into a blank PNG that looks like a legitimate result.
render() {
    _out=$("$OPENSCAD" -o "$1" --imgsize="$2" --camera="$3" ${4:-} \
           --colorscheme=$CS "$5" 2>&1) || true
    case "$_out" in
        *"Can't open import"*|*"WARNING: Can't"*|*ERROR*)
            printf '%s\n' "$_out" | grep -Ei "can't open|error" >&2
            echo "render failed: $1" >&2
            exit 1 ;;
    esac
}

echo "==> whole-model views"
render "$OUT/iso.png"    1300,900 "0,0,$MIDZ,55,0,25,$DIST" ""                 "$SCAD"
render "$OUT/top.png"    1200,900 "0,0,$MIDZ,0,0,0,$DIST"   --projection=ortho "$SCAD"
render "$OUT/bottom.png" 1200,900 "0,0,$MIDZ,180,0,0,$DIST" --projection=ortho "$SCAD"

echo "==> cross-sections"
cat > "$TMP" <<EOF
intersection() {
    import("$STL_ABS");
    translate([-500, 0, -500]) cube([1000, 500, 1000]);
}
EOF
render "$OUT/sec-xz.png" 1200,650 "0,0,$MIDZ,90,0,0,$SECDIST" --projection=ortho "$TMP"

cat > "$TMP" <<EOF
intersection() {
    import("$STL_ABS");
    translate([0, -500, -500]) cube([500, 1000, 1000]);
}
EOF
render "$OUT/sec-yz.png" 1200,650 "0,0,$MIDZ,90,0,90,$SECDIST" --projection=ortho "$TMP"

for Z in "$@"; do
    echo "==> slice at z=$Z"
    cat > "$TMP" <<EOF
intersection() {
    import("$STL_ABS");
    translate([-500, -500, $Z]) cube([1000, 1000, 0.05]);
}
EOF
    render "$OUT/slice-$Z.png" 1000,650 "0,0,$Z,0,0,0,$DIST" --projection=ortho "$TMP"
done

rm -f "$TMP"
echo "==> done: $OUT"
ls -1 "$OUT"/*.png
