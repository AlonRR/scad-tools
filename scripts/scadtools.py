#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Alon A. Rabinowitz
# SPDX-License-Identifier: MPL-2.0
"""What the OpenSCAD scripts share: running OpenSCAD and reading what it says, and telling two exports of
one solid from two different solids. Nothing here knows about any one model. The scripts that use it run
from a repository's root, or anywhere inside it.

OPENSCAD names the binary (default: openscad on PATH); JOBS sets how many renders run at once.
"""
import hashlib
import math
import os
import re
import shutil
import struct
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


def _repository():
    """The root of the git repository the script is run in, or the folder it is run in if there is none."""
    run = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    return Path(run.stdout.strip()) if run.returncode == 0 and run.stdout.strip() else Path.cwd()


ROOT = _repository()
OPENSCAD = os.environ.get("OPENSCAD") or shutil.which("openscad") or "openscad"
JOBS = int(os.environ.get("JOBS", max(1, (os.cpu_count() or 2) // 2)))


# ---------------------------------------------------------------- STL: size and shape
def triangles(path):
    """The triangles of an ASCII or binary STL, as three (x, y, z) tuples each."""
    data = Path(path).read_bytes()
    if data[:5] == b"solid" and b"facet" in data[:400]:
        corners = [tuple(map(float, line.split()[1:4]))
                   for line in data.decode("ascii", "replace").splitlines() if line.strip().startswith("vertex")]
        return [corners[i:i + 3] for i in range(0, len(corners) - 2, 3)]
    count = struct.unpack("<I", data[80:84])[0]
    return [[tuple(f[k:k + 3]) for k in (0, 3, 6)]
            for f in (struct.unpack("<9f", data[84 + i * 50 + 12:84 + i * 50 + 48]) for i in range(count))]


def stl_stats(path):
    """Facets, volume, area, bounding box and a hash of the distinct corners - enough to tell two exports of
    the same solid from two different solids, where comparing the files' bytes cannot: OpenSCAD's facet order
    follows the source, not the shape."""
    tris = triangles(path)
    volume = sum((a[0] * (b[1] * c[2] - b[2] * c[1]) - a[1] * (b[0] * c[2] - b[2] * c[0])
                  + a[2] * (b[0] * c[1] - b[1] * c[0])) / 6 for a, b, c in tris)
    area = sum(math.dist((0, 0, 0), cross(sub(b, a), sub(c, a))) / 2 for a, b, c in tris)
    corners = {tuple(round(x, 3) + 0.0 for x in p) for t in tris for p in t}
    lo = [min(p[k] for p in corners) for k in range(3)] if corners else [0, 0, 0]
    hi = [max(p[k] for p in corners) for k in range(3)] if corners else [0, 0, 0]
    digest = hashlib.sha256(repr(sorted(corners)).encode()).hexdigest()[:16]
    return {"facets": len(tris), "volume": volume, "area": area, "lo": lo, "hi": hi, "corners": len(corners),
            "hash": digest}


def sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def describe(s):
    return (f"facets {s['facets']}  volume {s['volume']:.3f} mm3  area {s['area']:.3f} mm2  "
            f"box {[round(x, 3) for x in s['lo']]} .. {[round(x, 3) for x in s['hi']]}  "
            f"corners {s['corners']} #{s['hash']}")


def same_solid(a, b):
    """Two exports of one solid: the same volume, area, box and corners. The facet count may differ."""
    return (abs(a["volume"] - b["volume"]) < 1e-3 and abs(a["area"] - b["area"]) < 1e-3
            and all(abs(x - y) < 1e-4 for x, y in zip(a["lo"] + a["hi"], b["lo"] + b["hi"]))
            and a["hash"] == b["hash"])


# ---------------------------------------------------------------- OpenSCAD
def render(out, scad, args):
    """Run OpenSCAD from the repository's root; return its exit code and its whole output."""
    run = subprocess.run([OPENSCAD, "-o", str(out), *args, scad], cwd=ROOT, capture_output=True, text=True)
    return run.returncode, run.stdout + run.stderr


# Two parts that touch intersect in a solid of no volume, which CGAL calls "not a valid 2-manifold": expected
# from check_parts, and harmless in a control, where the volume is what is read.
DEGENERATE = "WARNING: Object may not be a valid 2-manifold"


def problems(log, allowed=()):
    """OpenSCAD's own errors and warnings - not the model's ECHO "WARNING: ..." design notes, which are
    reported by scad-check.sh and are a judgement call, not a failure."""
    return [line for line in log.splitlines()
            if re.match(r"(ERROR|WARNING):", line) and not line.startswith(tuple(allowed))]


def defines(settings):
    return [x for name, value in settings for x in ("-D", f"{name}={value}")]


def parallel(fn, items):
    with ThreadPoolExecutor(max_workers=JOBS) as pool:
        return list(pool.map(fn, items))
