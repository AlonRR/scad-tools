# SPDX-FileCopyrightText: 2026 Alon A. Rabinowitz
# SPDX-License-Identifier: MPL-2.0
"""lib/gridfinity.scad, drawn by small files that `use` it. From the repository's root:

  uv run --with pytest pytest tests

Needs OpenSCAD with the Manifold backend (OPENSCAD, or openscad on PATH); skipped without it. The foot's negative is
judged by its mesh: one closed body, its box, and its volume against the slab less each foot worked out from the
profile - each section a frustum between two rounded squares, its corners' arcs as OpenSCAD's offset() draws them.
The control: a clearance the formula does not know must miss it.
"""
import itertools
import math
import os
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
FN = 64
PROFILE = [(0, 0), (0.7, 0.7), (0.7, 2.5), (2.85, 4.65)]
CORE, E = 34, 0.001


def negative(tmp_path, body):
    """The box, volume and faults of what `body` draws."""
    if not OPENSCAD:
        pytest.skip("no OpenSCAD")
    f = tmp_path / "t.scad"
    f.write_text(f"use <{(LIB / 'gridfinity.scad').as_posix()}>\n$fn = {FN};\n{body}\n", encoding="utf-8")
    out = f.with_suffix(".stl")
    run = subprocess.run([OPENSCAD, "--backend=manifold", "-o", str(out), str(f)], capture_output=True, text=True,
                         check=False)
    log = run.stdout + run.stderr
    assert "WARNING" not in log, log[-800:]
    assert out.exists(), log[-800:]
    s = scadtools.stl_stats(out)
    return s["lo"], s["hi"], s["volume"], scadtools.mesh_problems(out)


def rounded_square(r):
    """The area of the core square offset by r, its corners FN-gon arcs with their corners on the circle."""
    return CORE * CORE + 4 * CORE * r + FN / 2 * math.sin(2 * math.pi / FN) * r * r


def foot_volume(clearance):
    """Each section: the hull of a slice E thick at each end - a frustum up to the top slice, then the top slice."""
    total = 0.0
    for (x0, z0), (x1, z1) in itertools.pairwise(PROFILE):
        r0, r1 = (8 / 2 - PROFILE[-1][0] + x - clearance for x in (x0, x1))
        h = z1 - z0 - E
        a0, a1, am = rounded_square(r0), rounded_square(r1), rounded_square((r0 + r1) / 2)
        total += h / 6 * (a0 + 4 * am + a1) + E * a1
    return total


@pytest.mark.parametrize("nx, ny, clearance", [(1, 1, 0), (2, 1, 0), (1, 1, 0.2)])
def test_negative(tmp_path, nx, ny, clearance):
    lo, hi, volume, faults = negative(tmp_path, f"gridfinity_foot_negative({nx}, {ny}, {clearance});")
    assert not faults, faults
    assert lo == pytest.approx([-21 * nx, -21 * ny, 0], abs=1e-3) and hi == pytest.approx([21 * nx, 21 * ny, 4.65], abs=1e-3)
    want = 42 * nx * 42 * ny * 4.65 - nx * ny * foot_volume(clearance)
    assert volume == pytest.approx(want, rel=1e-4), (volume, want)


def test_control_clearance_missed(tmp_path):
    """The clearance shrinks each foot: the negative grows by more than the volume check's tolerance."""
    _, _, volume, _ = negative(tmp_path, "gridfinity_foot_negative(1, 1, 0.2);")
    nominal = 42 * 42 * 4.65 - foot_volume(0)
    assert volume != pytest.approx(nominal, rel=1e-4)


def test_nothing_at_top_level(tmp_path):
    """`use`d, it draws nothing and sets nothing: a file that only uses it renders empty, without a warning."""
    if not OPENSCAD:
        pytest.skip("no OpenSCAD")
    f = tmp_path / "t.scad"
    f.write_text(f"use <{(LIB / 'gridfinity.scad').as_posix()}>\necho(h = gridfinity_foot_h());\n", encoding="utf-8")
    out = f.with_suffix(".echo")
    run = subprocess.run([OPENSCAD, "-o", str(out), str(f)], capture_output=True, text=True, check=False)
    text = out.read_text(encoding="utf-8")
    assert "ECHO: h = 4.65" in text and "WARNING" not in run.stdout + run.stderr + text
