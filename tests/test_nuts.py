# SPDX-FileCopyrightText: 2026 Alon A. Rabinowitz
# SPDX-License-Identifier: MPL-2.0
"""lib/nuts.scad, drawn by small files that `use` it. From the repository's root:

  uv run --with pytest pytest tests

Needs OpenSCAD with the Manifold backend (OPENSCAD, or openscad on PATH); skipped without it. A fit is judged by
what an intersection leaves - nothing, for a nut that fits - and each fit has a control that must leave something.
"""
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

# An M3 nut, ISO 4032: 5.5 across its flats, 2.4 tall; its slot 2.8 tall, the nut centred in it.
AF, H, SLOT_H = 5.5, 2.4, 2.8
# A block the slot is cut into, its +X face 8 past the axis: a slot cut 10 out opens through it, one cut 1 out does not.
BLOCK = "difference() { translate([-12, -12, -3]) cube([20, 24, 8.8]); nut_slot(5.5, 2.8, out = %s, fit = %s); }"
NUT = "translate([0, 0, 0.2]) hex_nut(5.5, 2.4)"


def volume(tmp_path, body):
    """The volume of what `body` draws, 0 when it draws nothing - as a fit check's intersection should."""
    if not OPENSCAD:
        pytest.skip("no OpenSCAD")
    f = tmp_path / "t.scad"
    f.write_text(f"use <{(LIB / 'nuts.scad').as_posix()}>\n{body}\n", encoding="utf-8")
    out = f.with_suffix(".stl")
    run = subprocess.run([OPENSCAD, "--backend=manifold", "-o", str(out), str(f)], capture_output=True, text=True,
                         check=False)
    log = run.stdout + run.stderr
    assert "WARNING: Ignoring unknown module" not in log, log[-800:]
    if not out.exists() or out.stat().st_size == 0:
        assert "empty" in log.lower(), log[-800:]
        return 0.0
    return abs(scadtools.stl_stats(out)["volume"])


def box(tmp_path, body):
    if not OPENSCAD:
        pytest.skip("no OpenSCAD")
    f = tmp_path / "b.scad"
    f.write_text(f"use <{(LIB / 'nuts.scad').as_posix()}>\n{body}\n", encoding="utf-8")
    out = f.with_suffix(".stl")
    subprocess.run([OPENSCAD, "--backend=manifold", "-o", str(out), str(f)], capture_output=True, check=False)
    s = scadtools.stl_stats(out)
    return [round(v, 3) for v in s["lo"] + s["hi"]]


def test_the_nut_is_its_flats_across_y_and_its_corners_along_x(tmp_path):
    ac = AF / 2 / 0.8660254037844386
    assert box(tmp_path, "hex_nut(5.5, 2.4);") == [round(-ac, 3), -2.75, 0, round(ac, 3), 2.75, 2.4]


def test_the_slot_is_the_flats_plus_fit_wide_and_ends_behind_the_axis_at_the_back_corner(tmp_path):
    ac = AF / 2 / 0.8660254037844386
    assert box(tmp_path, "nut_slot(5.5, 2.8, out = 10, fit = 0.3);") == [round(-ac - 0.3, 3), -3.05, 0, 10, 3.05, 2.8]


@pytest.mark.parametrize("fit, fits", [(0.3, True), (-0.1, False)])
def test_the_nut_fits_its_slot(tmp_path, fit, fits):
    left = volume(tmp_path, f"intersection() {{ {BLOCK % (10, fit)} {NUT}; }}")
    assert (left == 0) == fits, left


@pytest.mark.parametrize("out, opens", [(10, True), (1, False)])
def test_the_nut_slides_out_through_the_mouth(tmp_path, out, opens):
    way = f"hull() for (x = [0, 12]) translate([x, 0, 0]) {NUT};"
    left = volume(tmp_path, f"intersection() {{ {BLOCK % (out, 0.3)} {way} }}")
    assert (left == 0) == opens, left


# A pull nut's pocket, its seat's roof at z = 0: the seat 2.8 tall, 0.2 a side; under it the way, 5 long, 0.25 a
# side, open at its foot. In a block whose underside is 6 under the roof, the way opens through it; 1 long, it does not.
POCKET = "pull_nut_pocket(5.5, 2.8, way = %s, fit = %s, way_fit = 0.25)"
PBLOCK = f"difference() {{ translate([-8, -8, -6]) cube([16, 16, 8]); {POCKET}; }}"
PULLED = "translate([0, 0, -0.01 - 2.4]) hex_nut(5.5, 2.4)"  # pulled up to the roof, a hair under it


def test_a_pull_pocket_is_its_seat_over_its_way_the_corners_along_x(tmp_path):
    ac_way = (5.5 / 2 + 0.25) / 0.8660254037844386
    assert box(tmp_path, POCKET % (5, 0.2) + ";") == [round(-ac_way, 3), -3.0, -7.8, round(ac_way, 3), 3.0, 0]


@pytest.mark.parametrize("fit, fits", [(0.2, True), (-0.1, False)])
def test_the_nut_fits_its_seat(tmp_path, fit, fits):
    left = volume(tmp_path, f"intersection() {{ {PBLOCK % (5, fit)} {PULLED}; }}")
    assert (left == 0) == fits, left


@pytest.mark.parametrize("way, opens", [(5, True), (1, False)])
def test_the_nut_comes_up_the_way_from_under_the_block(tmp_path, way, opens):
    path = "hull() for (z = [0, -8]) translate([0, 0, z]) " + PULLED + ";"
    left = volume(tmp_path, f"intersection() {{ {PBLOCK % (way, 0.2)} {path} }}")
    assert (left == 0) == opens, left
