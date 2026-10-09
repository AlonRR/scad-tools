# SPDX-FileCopyrightText: 2026 Alon A. Rabinowitz
# SPDX-License-Identifier: MPL-2.0
"""lib/patterns.scad, drawn or echoed by small files that `use` it. From the repository's root:

  uv run --with pytest pytest tests

Needs OpenSCAD with the Manifold backend (OPENSCAD, or openscad on PATH); skipped without it. A pattern is judged by
the plate it cuts, 1 mm thick: its volume against the open area worked out from the pattern's own geometry, and
for the honeycomb every hole inside the rectangle with the same web to its neighbours. Each check has a control
that must fail it.
"""
import json
import math
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import scadtools

OPENSCAD = os.environ.get("OPENSCAD") or shutil.which("openscad")
LIB = ROOT / "lib"


def source(tmp_path, body):
    if not OPENSCAD:
        pytest.skip("no OpenSCAD")
    f = tmp_path / "t.scad"
    f.write_text(f"use <{(LIB / 'patterns.scad').as_posix()}>\n{body}\n", encoding="utf-8")
    return f


def plate(tmp_path, body):
    """The volume of what `body` draws, and its faults."""
    f = source(tmp_path, body)
    out = f.with_suffix(".stl")
    run = subprocess.run([OPENSCAD, "--backend=manifold", "-o", str(out), str(f)], capture_output=True, text=True,
                         check=False)
    log = run.stdout + run.stderr
    assert "WARNING: Ignoring unknown" not in log, log[-800:]
    assert out.exists(), log[-800:]
    return scadtools.stl_stats(out)["volume"], scadtools.mesh_problems(out)


def centres(tmp_path, size, hole, web):
    f = source(tmp_path, f"echo(c = honeycomb_centres({size}, {hole}, {web}));")
    out = f.with_suffix(".echo")
    subprocess.run([OPENSCAD, "-o", str(out), str(f)], capture_output=True, text=True, check=False)
    m = re.search(r"ECHO: c = (.*)$", out.read_text(encoding="utf-8"), re.MULTILINE)
    return [tuple(c) for c in json.loads(m[1])]


# ---------------------------------------------------------------- the hemp-leaf pattern
TILE = 18.94
ROWS = TILE * math.sqrt(3)  # two rows of triangles: the lattice repeats every TILE along X and ROWS along Y


def hemp_open(tile, bar):
    """The open share: each third of a triangle shrunk by half a bar, as its inradius is."""
    return (1 - bar / 2 * (2 * math.sqrt(3) + 4) / tile) ** 2


def hemp_window(bar):
    # one period of the lattice, anywhere: it holds the same holes, cut up differently
    return (f"linear_extrude(1, convexity = 10) intersection() {{ translate([3.1, -5.3]) square([{TILE}, {ROWS}]);"
            f" hemp_leaf_holes([60, 80], {TILE}, {bar}); }}")


@pytest.mark.parametrize("bar", [1.2, 2.5])
def test_one_period_of_the_hemp_leaf_pattern_is_open_by_its_shrunk_thirds(tmp_path, bar):
    volume, faults = plate(tmp_path, hemp_window(bar))
    assert faults == {} or set(faults) <= {"bodies"}  # a period's holes are many separate pieces
    assert volume == pytest.approx(TILE * ROWS * hemp_open(TILE, bar), rel=1e-4)


def test_the_check_tells_one_bar_from_another(tmp_path):
    # The control: bars half as wide leave more open than the 1.2 mm bars' sum says.
    volume, _ = plate(tmp_path, hemp_window(0.6))
    assert volume != pytest.approx(TILE * ROWS * hemp_open(TILE, 1.2), rel=1e-2)


# ---------------------------------------------------------------- the honeycomb
SIZE, HOLE, WEB = [89.6, 29.6], 3.2, 0.9  # a 95 x 35 grill's mesh inside a rim of 2.7


def honeycomb_faults(cs, size, hole, web):
    """Holes outside the rectangle, and holes whose nearest neighbour is not hole + web away."""
    r = hole / math.sqrt(3)
    outside = [c for c in cs if abs(c[0]) + hole / 2 > size[0] / 2 + 1e-4 or abs(c[1]) + r > size[1] / 2 + 1e-4]
    uneven = [a for a in cs if min(math.dist(a, b) for b in cs if b != a) != pytest.approx(hole + web, abs=1e-4)]  # echo keeps 6 digits
    return outside, uneven


def test_the_honeycomb_keeps_its_holes_inside_with_every_web_the_same(tmp_path):
    cs = centres(tmp_path, SIZE, HOLE, WEB)
    assert len(cs) == 172
    assert honeycomb_faults(cs, SIZE, HOLE, WEB) == ([], [])


def test_a_plate_cut_by_the_honeycomb_keeps_all_but_its_holes(tmp_path):
    n = len(centres(tmp_path, SIZE, HOLE, WEB))
    volume, faults = plate(tmp_path, f"linear_extrude(1, convexity = 10) difference() {{ square({SIZE}, center = true);"
                                     f" honeycomb_holes({SIZE}, {HOLE}, {WEB}); }}")
    assert faults == {}
    assert volume == pytest.approx(SIZE[0] * SIZE[1] - n * math.sqrt(3) / 2 * HOLE ** 2, rel=1e-6)


def test_holes_that_overlap_are_caught(tmp_path):
    # The control: a negative web runs the holes into each other - the webs' check and the plate's volume both see it.
    cs = centres(tmp_path, SIZE, HOLE, -0.2)
    assert honeycomb_faults(cs, SIZE, HOLE, WEB)[1] != []
    volume, _ = plate(tmp_path, f"linear_extrude(1, convexity = 10) difference() {{ square({SIZE}, center = true);"
                                f" honeycomb_holes({SIZE}, {HOLE}, -0.2); }}")
    assert volume != pytest.approx(SIZE[0] * SIZE[1] - len(cs) * math.sqrt(3) / 2 * HOLE ** 2, rel=1e-4)
