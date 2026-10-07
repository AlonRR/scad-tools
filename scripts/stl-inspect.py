#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Alon A. Rabinowitz
# SPDX-License-Identifier: MPL-2.0
# /// script
# requires-python = ">=3.11"
# ///
"""Measure someone else's model before remixing it: where its faces are, what its joints look like, and how
its author prints it. Works on a downloaded STL or 3MF; changes nothing.

  uv run stl-inspect.py bounds FILE.stl [FILE.stl ...]
        size, bounding box, volume and facets of each STL

  uv run stl-inspect.py sections FILE.stl [--axis z] --at 1.5 0.5 -0.5 ...
  uv run stl-inspect.py sections FILE.stl [--axis z] --from -12 --to 2 --step 1
        cut the STL across AXIS at each position and print every loop of every cut: solid or hole, its
        box, its area, and its corners. Axis z gives (x, y); axis y gives (x, z); axis x gives (y, z) - in
        the STL's own coordinates, never the SVG's flipped y. Two parts that join: cut each a little
        either side of the joint's plane and lay the loops side by side.

  uv run stl-inspect.py 3mf FILE.3mf
        the objects in a slicer project: name, plate, size, and whether the plate flips it over - which is
        how its author prints it, and so which of its faces is the bottom

Why each piece exists, learned on GekoPrime's LunchBox (Oct 2026):
- STLs from one project need not share a frame. Its body and lid were exported in place, assembled; its
  fan section was not, and stood turned 180 degrees against them. Only cutting both sides of the joint
  showed which face of the fan section met the body, and which way round.
- A part's print orientation is not its use orientation, and the STL is in neither for sure. The 3MF says
  how the author printed it.
- OpenSCAD's SVG export negates y. Read raw, every depth comes out mirrored; this script un-negates it.
- A failed import is only a WARNING: an empty cut is reported as a failure here, never as "no loops".

OPENSCAD names the binary; a build with the Manifold backend (the nightly) cuts an 8 MB mesh in seconds,
where the 2021.01 release takes minutes. JOBS sets how many cuts run at once.
"""
import argparse
import re
import sys
import tempfile
import uuid
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scadtools import describe, parallel, problems, render, stl_stats  # noqa: E402

# The cut's frame for each axis: a rotation (never a mirror, which would turn the solid inside out) that
# takes the cut plane to z = 0 and the two remaining axes, in order, to the picture's x and y.
FRAMES = {
    "z": ("[[1,0,0,0],[0,1,0,0],[0,0,1,0]]", "x", "y"),
    "y": ("[[1,0,0,0],[0,0,1,0],[0,-1,0,0]]", "x", "z"),
    "x": ("[[0,1,0,0],[0,0,1,0],[1,0,0,0]]", "y", "z"),
}


# ---------------------------------------------------------------- sections
def cut_svg(stl, axis, at, tmp):
    """One cut, as an SVG; returns (svg path or None, OpenSCAD's problems)."""
    matrix = FRAMES[axis][0]
    shift = {"x": f"[{-at},0,0]", "y": f"[0,{-at},0]", "z": f"[0,0,{-at}]"}[axis]
    src = Path(tmp) / f"cut-{uuid.uuid4().hex[:8]}.scad"
    src.write_text(f'projection(cut = true) multmatrix({matrix}) translate({shift}) import("{Path(stl).resolve().as_posix()}");\n',
                   encoding="utf-8")
    out = src.with_suffix(".svg")
    _, log = render(out, str(src), [])
    bad = problems(log)
    return (out if out.exists() and not bad else None), bad + ([] if out.exists() else ["no SVG written: the cut is empty"])


def loops_of(svg):
    """Every closed loop of an OpenSCAD SVG, in model coordinates (the SVG's y is the model's -y)."""
    text = Path(svg).read_text()
    found = []
    for d in re.findall(r'd="([^"]+)"', text):
        for sub in re.split(r"(?=M)", d):
            pts = [(float(a), -float(b)) for a, b in re.findall(r"(-?[\d.]+(?:e-?\d+)?),(-?[\d.]+(?:e-?\d+)?)", sub)]
            clean = []
            for p in pts:
                if not clean or (abs(clean[-1][0] - p[0]) > 1e-9 or abs(clean[-1][1] - p[1]) > 1e-9):
                    clean.append(p)
            if len(clean) > 2:
                found.append(clean)
    return found


def area(p):
    return abs(sum(p[i][0] * p[i - 1][1] - p[i - 1][0] * p[i][1] for i in range(len(p)))) / 2


def inside(pt, poly):
    x, y = pt
    hit = False
    for i in range(len(poly)):
        (x1, y1), (x2, y2) = poly[i - 1], poly[i]
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            hit = not hit
    return hit


def simplify(pts, tol):
    """Ramer-Douglas-Peucker on an open polyline: the fewest points that stay within tol of it."""
    if len(pts) < 3:
        return pts
    (x1, y1), (x2, y2) = pts[0], pts[-1]
    length = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
    def off(p):
        if length == 0:
            return ((p[0] - x1) ** 2 + (p[1] - y1) ** 2) ** 0.5
        return abs((y2 - y1) * p[0] - (x2 - x1) * p[1] + x2 * y1 - y2 * x1) / length
    i, d = max(((k, off(p)) for k, p in enumerate(pts[1:-1], 1)), key=lambda kd: kd[1])
    if d <= tol:
        return [pts[0], pts[-1]]
    return simplify(pts[:i + 1], tol)[:-1] + simplify(pts[i:], tol)


def corners(p, tol=0.05):
    """The loop's outline in the fewest points that stay within tol mm of it: a straight edge is its two
    ends, a rounded corner a few points along its arc - where it starts and ends always among them. A plain
    turn-angle filter loses rounded corners altogether, whose many short segments each turn only a little."""
    far = max(range(len(p)), key=lambda k: (p[k][0] - p[0][0]) ** 2 + (p[k][1] - p[0][1]) ** 2)
    ring = p + [p[0]]
    return (simplify(ring[:far + 1], tol)[:-1] + simplify(ring[far:], tol))[:-1]


def sections(stl, axis, positions, max_points=24):
    """max_points caps the corners listed per loop, 0 for all of them. A capped list ends in "...", and what
    it leaves out is easy to read as absent: a body's side blocks hid in the tail of its outline once."""
    u, v = FRAMES[axis][1], FRAMES[axis][2]
    with tempfile.TemporaryDirectory() as tmp:
        cuts = parallel(lambda at: cut_svg(stl, axis, at, tmp) + (at,), positions)
        failed = 0
        for svg, bad, at in cuts:
            if svg is None:
                failed += 1
                print(f"== {axis} = {at:g}: FAILED  {'; '.join(bad)[:200]}")
                continue
            loops = sorted(loops_of(svg), key=area, reverse=True)
            print(f"== {axis} = {at:g}: {len(loops)} loop(s), in ({u}, {v})")
            for i, p in enumerate(loops):
                depth = sum(inside(p[0], q) for j, q in enumerate(loops) if j != i and area(q) > area(p))
                kind = "solid" if depth % 2 == 0 else "hole "
                xs, ys = [q[0] for q in p], [q[1] for q in p]
                c = corners(p)
                shown = c if not max_points else c[:max_points]
                pts = " ".join(f"({x:.2f},{y:.2f})" for x, y in shown) + (f" ... {len(c) - len(shown)} more" if len(shown) < len(c) else "")
                print(f"   {kind} {u} {min(xs):8.2f} .. {max(xs):8.2f}   {v} {min(ys):8.2f} .. {max(ys):8.2f}   "
                      f"area {area(p):9.2f}   {pts}")
    return failed == 0


# ---------------------------------------------------------------- 3mf
def three_mf(path):
    """The objects of a slicer project and how they sit on its plates. The build items carry the transforms;
    the names and plates are in Metadata/model_settings.config for Bambu Studio and Orca, and the names in
    Metadata/Slic3r_PE_model.config for PrusaSlicer, which has one plate."""
    with zipfile.ZipFile(path) as z:
        model = z.read("3D/3dmodel.model").decode("utf-8", "replace")
        config = "".join(z.read(f).decode("utf-8", "replace") for f in
                         ("Metadata/model_settings.config", "Metadata/Slic3r_PE_model.config") if f in z.namelist())
    names, plates = {}, {}
    for oid, body in re.findall(r'<object id="(\d+)"[^>]*>(.*?)</object>', config, re.DOTALL):
        n = re.search(r'key="name" value="([^"]*)"', body)
        names[oid] = n.group(1) if n else "?"
    for plate in re.findall(r"<plate>(.*?)</plate>", config, re.DOTALL):
        pid = re.search(r'key="plater_id" value="(\d+)"', plate)
        for oid in re.findall(r'key="object_id" value="(\d+)"', plate):
            plates[oid] = pid.group(1) if pid else "?"
    for oid, attrs in re.findall(r'<object id="(\d+)"([^>]*)>', model):
        if oid not in names:
            n = re.search(r'name="([^"]*)"', attrs)
            names[oid] = n.group(1) if n else "?"
    meshes = dict(re.findall(r'<object id="(\d+)"[^>]*>\s*<mesh>\s*<vertices>(.*?)</vertices>', model, re.DOTALL))
    components = dict(re.findall(r'<object id="(\d+)"[^>]*>\s*<components>\s*<component objectid="(\d+)"', model, re.DOTALL))
    items = re.findall(r'<item objectid="(\d+)"(?:[^>]*?transform="([^"]+)")?', model)
    if not items:
        print("no build items")
        return False
    print(f"{'object':>6}  {'name':40} {'plate':>5}  {'size (x y z) of its mesh':28} up while printing")
    for oid, tf in items:
        verts = re.findall(r'x="([-\d.e]+)" y="([-\d.e]+)" z="([-\d.e]+)"', meshes.get(components.get(oid, oid), ""))
        size = "no mesh in this file"
        if verts:
            pts = [tuple(map(float, v)) for v in verts]
            size = " x ".join(f"{max(p[k] for p in pts) - min(p[k] for p in pts):.1f}" for k in range(3))
        t = [float(x) for x in tf.split()] if tf else [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0]
        # A 3MF transform is "m00 m01 m02 m10 m11 m12 m20 m21 m22 m30 m31 m32", applied to a row vector:
        # the plate's z is x*m02 + y*m12 + z*m22, so (m02, m12, m22) is the mesh direction that points up.
        up = (t[2], t[5], t[8])
        k = max(range(3), key=lambda i: abs(up[i]))
        axis = ("+" if up[k] > 0 else "-") + "xyz"[k]
        pose = {"+z": "as modelled", "-z": "turned over"}.get(axis, "on its side")
        if abs(abs(up[k]) - 1) > 1e-3:
            pose = "tilted"
        print(f"{oid:>6}  {names.get(oid, '?')[:40]:40} {plates.get(oid, '-'):>5}  {size:28} mesh {axis}: {pose}")
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("bounds")
    b.add_argument("stl", nargs="+")
    s = sub.add_parser("sections")
    s.add_argument("stl")
    s.add_argument("--axis", choices="xyz", default="z")
    s.add_argument("--at", type=float, nargs="+")
    s.add_argument("--from", dest="start", type=float)
    s.add_argument("--to", dest="stop", type=float)
    s.add_argument("--step", type=float, default=1.0)
    s.add_argument("--points", type=int, default=24, help="corners listed per loop, 0 for all")
    m = sub.add_parser("3mf")
    m.add_argument("file")
    a = ap.parse_args()
    if a.cmd == "bounds":
        for f in a.stl:
            st = stl_stats(f)
            size = " x ".join(f"{h - l:.2f}" for l, h in zip(st["lo"], st["hi"]))
            print(f"{f}\n   size {size}   {describe(st)}")
        return True
    if a.cmd == "3mf":
        return three_mf(a.file)
    positions = list(a.at or [])
    if a.start is not None and a.stop is not None:
        n = round(abs(a.stop - a.start) / a.step)
        positions += [a.start + i * a.step * (1 if a.stop >= a.start else -1) for i in range(n + 1)]
    if not positions:
        ap.error("sections needs --at, or --from and --to")
    return sections(a.stl, a.axis, positions, a.points)


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
