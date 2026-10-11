# SPDX-FileCopyrightText: 2026 Alon A. Rabinowitz
# SPDX-License-Identifier: MPL-2.0
"""lib/draw2d.scad, drawn by small files that `use` it, each drawing extruded 1 mm so its area is the volume. From the
repository's root:

  uv run --with pytest pytest tests

Needs OpenSCAD with the Manifold backend (OPENSCAD, or openscad on PATH); skipped without it. A dashed run's area is
its dashes' length times the line's weight, plus their round ends; the weight and the text's size come from $lw and
$txt, set by the drawing - doubled, the line's area doubles and a letter's quadruples. The control for each: the
special variable set to its default draws the same as unset, and a weight it does not use must miss the length's area.
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


def area(tmp_path, body, name="t"):
    """The area of what `body` draws in 2D, and OpenSCAD's output."""
    if not OPENSCAD:
        pytest.skip("no OpenSCAD")
    f = tmp_path / f"{name}.scad"
    f.write_text(f"use <{(LIB / 'draw2d.scad').as_posix()}>\n{body}\n", encoding="utf-8")
    out = f.with_suffix(".stl")
    run = subprocess.run([OPENSCAD, "--backend=manifold", "-o", str(out), str(f)], capture_output=True, text=True,
                         check=False)
    log = run.stdout + run.stderr
    assert "WARNING" not in log, log[-800:]
    assert out.exists(), log[-800:]
    return scadtools.stl_stats(out)["volume"]


# Dashes 0.55 long and 0.34 apart along 10 mm: 12 of them, the last cut at 10 mm - 6.05 + 0.21 = 6.26 mm drawn.
DASHED = "linear_extrude(1) dashed([0, 0], [10, 0]);"
DRAWN = 11 * 0.55 + (10 - 11 * 0.89)


def test_dashed_area(tmp_path):
    """The dashes' area: their length times 0.07, plus a little for their round ends (a pentagon each, at this size)."""
    a = area(tmp_path, DASHED)
    assert DRAWN * 0.07 < a < DRAWN * 0.07 * 1.15, a


def test_lw_doubles_the_line(tmp_path):
    """Twice the weight: the dashes' length twice as wide, and their ends four times the area - a little over double."""
    a1 = area(tmp_path, DASHED, "one")
    a2 = area(tmp_path, "$lw = 0.14;\n" + DASHED, "two")
    assert 2 < a2 / a1 < 2.3, (a1, a2)


def test_control_lw_default(tmp_path):
    """$lw set to its default draws what unset draws; a weight the drawing does not use misses the length's area."""
    assert area(tmp_path, "$lw = 0.07;\n" + DASHED, "set") == pytest.approx(area(tmp_path, DASHED, "unset"), rel=1e-9)
    a = area(tmp_path, "$lw = 0.1;\n" + DASHED, "wide")
    assert not DRAWN * 0.07 < a < DRAWN * 0.07 * 1.15, a


def test_txt_scales_the_text(tmp_path):
    a1 = area(tmp_path, 'linear_extrude(1) heading("H", [0, 0]);', "small")
    a2 = area(tmp_path, '$txt = 1.56;\nlinear_extrude(1) heading("H", [0, 0]);', "big")
    assert 3.8 < a2 / a1 < 4.2, (a1, a2)


def test_dimensions_draw(tmp_path):
    """A dimension each way, a leader and an axis render without a warning and draw something."""
    body = ('linear_extrude(1) { dim_h(0, 10, 3, 0, "10"); dim_v(0, 6, 12, 10, "6", right = false); '
            'leader([-3, 2], [0, 0], "corner"); axis("X", 0, 2.6); dashed_rect_at(4, 3, [5, -5]); }')
    assert area(tmp_path, body) > 1
