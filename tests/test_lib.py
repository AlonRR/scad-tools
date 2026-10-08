# SPDX-FileCopyrightText: 2026 Alon A. Rabinowitz
# SPDX-License-Identifier: MPL-2.0
"""lib/gasket.scad, lib/fdm.scad and lib/springs.scad, each drawn or echoed by a small file that `use`s it. From
the repository's root:

  uv run --with pytest pytest tests

Needs OpenSCAD with the Manifold backend (OPENSCAD, or openscad on PATH); skipped without it. A shape is judged
by its mesh - one closed body, its box, its volume against the section's area times the centreline's length -
and each check has a control that must fail it.
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

B = [3, 3, 0.45]  # a small bead: 3 wide, 3 tall, walls of one perimeter
RECT = [[0, 0], [60, 0], [60, 30], [0, 30]]
ELL = [[0, 0], [50, 0], [50, 20], [25, 20], [25, 40], [0, 40]]  # an L: one corner turns right


def source(tmp_path, body, libs):
    if not OPENSCAD:
        pytest.skip("no OpenSCAD")
    f = tmp_path / "t.scad"
    f.write_text("".join(f"use <{(LIB / f'{n}.scad').as_posix()}>\n" for n in libs) + body, encoding="utf-8")
    return f


def draw(tmp_path, body, libs=("gasket",)):
    """The STL's statistics and its faults, and OpenSCAD's output."""
    f = source(tmp_path, body, libs)
    out = f.with_suffix(".stl")
    run = subprocess.run([OPENSCAD, "--backend=manifold", "-o", str(out), str(f)], capture_output=True, text=True,
                         check=False)
    log = run.stdout + run.stderr  # openscad.com on Windows says it all on stdout
    assert out.exists(), log[-1500:]
    return scadtools.stl_stats(out), scadtools.mesh_problems(out), log


def echoes(tmp_path, body, libs=("gasket",)):
    """Each `echo(name = value)` as {name: value}, and OpenSCAD's output."""
    f = source(tmp_path, body, libs)
    out = f.with_suffix(".echo")
    run = subprocess.run([OPENSCAD, "-o", str(out), str(f)], capture_output=True, text=True, check=False)
    log = run.stdout + run.stderr
    found = {}
    for line in out.read_text(encoding="utf-8").splitlines() if out.exists() else []:
        m = re.match(r"ECHO: (\w+) = (.*)$", line)
        if m:
            found[m[1]] = json.loads(re.sub(r"\bundef\b", "null", m[2]))
    return found, log


def section_area(w, h, t):
    """The bead's house section: outside less inside, the inside the outside moved in by t, its corners mitred."""
    outside = w * h - w * w / 4
    wi, eave = w - 2 * t, h - w / 2 + t - t * math.sqrt(2)
    return outside - (wi * (eave - t) + wi * wi / 4)


def centreline(corners, r):
    """The ring's centreline: its sides less each corner's two tangents, plus its arcs - every corner here 90 degrees."""
    sides = sum(math.dist(corners[i - 1], corners[i]) for i in range(len(corners)))
    return sides - len(corners) * 2 * r + len(corners) * math.pi / 2 * r


# ---------------------------------------------------------------- gasket
def test_the_groove_is_the_bead_and_its_room_wide_and_its_squeezed_height_deep(tmp_path):
    found, _ = echoes(tmp_path, f"echo(g = gasket_groove({B}, 0.25, 0.2));\necho(d = gasket_groove({B}));")
    assert found["g"] == pytest.approx([3.5, 2.4])
    assert found["d"] == pytest.approx([3.5, 2.4])  # the defaults: 0.25 each side, squeezed 20 %


@pytest.mark.parametrize("corners", [RECT, ELL], ids=["rectangle", "L"])
def test_a_ring_is_one_closed_body_of_the_sections_volume(tmp_path, corners):
    stats, faults, log = draw(tmp_path, f"gasket_ring({corners}, 5, {B});")
    assert faults == {}, log[-800:]
    expected = section_area(*B) * centreline(corners, 5)
    assert stats["volume"] == pytest.approx(expected, rel=0.01)
    xs, ys = [p[0] for p in corners], [p[1] for p in corners]
    assert stats["lo"] == pytest.approx([min(xs) - 1.5, min(ys) - 1.5, 0], abs=1e-3)
    assert stats["hi"] == pytest.approx([max(xs) + 1.5, max(ys) + 1.5, 3], abs=1e-3)


@pytest.mark.parametrize("corners", [RECT, ELL], ids=["rectangle", "L"])
def test_without_its_notch_the_hollow_is_a_sealed_void(tmp_path, corners):
    # The control for the notch: closed, the hollow's own surface is a second body.
    _, faults, _ = draw(tmp_path, f"gasket_ring({corners}, 5, {B}, notch = false);")
    assert faults == {"bodies": 2}


# The inner wall of a long side, 1.5 - 0.45 to 1.5 in from its centreline, the cut 0.01 into the hollow.
@pytest.mark.parametrize("corners, y", [(RECT, [1.04, 1.5]), (RECT[::-1], [28.5, 28.96])],
                         ids=["counterclockwise, along y = 0", "clockwise, along y = 30"])
def test_the_notch_opens_the_inner_wall_midway_along_the_longest_side(tmp_path, corners, y):
    # what the notch takes away: the ring without it, less the ring with it
    stats, _, _ = draw(tmp_path, f"difference() {{ gasket_ring({corners}, 5, {B}, notch = false);"
                                 f" gasket_ring({corners}, 5, {B}); }}")
    assert stats["lo"] == pytest.approx([29.5, y[0], 0.45 + 0.05], abs=1e-3)
    assert stats["hi"][:2] == pytest.approx([30.5, y[1]], abs=1e-3)


def test_the_corners_can_each_take_their_own_radius(tmp_path):
    stats, faults, _ = draw(tmp_path, f"gasket_ring({RECT}, [4, 5, 6, 8], {B});")
    assert faults == {}
    sides = 2 * (60 + 30)
    expected = section_area(*B) * (sides - 2 * (4 + 5 + 6 + 8) + math.pi / 2 * (4 + 5 + 6 + 8))
    assert stats["volume"] == pytest.approx(expected, rel=0.01)


@pytest.mark.parametrize("side, inside", [(0.25, True), (-0.2, False)])
def test_the_ring_lies_in_its_groove(tmp_path, side, inside):
    ring, _, _ = draw(tmp_path, f"gasket_ring({ELL}, 5, {B});")
    assert ring["volume"] > 100  # or nothing at all would lie in the groove
    # Whatever of the ring is outside the groove, beside a 1 mm cube far off so the result is never empty.
    body = (f"translate([1000, 0, 0]) cube(1);\n"
            f"difference() {{ gasket_ring({ELL}, 5, {B}); translate([0, 0, -1]) linear_extrude(5)\n"
            f"    gasket_groove_2d({ELL}, 5, gasket_groove({B}, {side})[0]); }}")
    stats, _, _ = draw(tmp_path, body)
    assert (abs(stats["volume"] - 1) < 1e-3) == inside, stats["volume"]


def test_the_groove_is_its_width_about_the_centreline(tmp_path):
    # a band about a line has the line's length times its width, whatever the line's bends
    stats, faults, _ = draw(tmp_path, f"linear_extrude(1) gasket_groove_2d({ELL}, 5, 3.5);")
    assert faults == {}
    assert stats["volume"] == pytest.approx(3.5 * centreline(ELL, 5), rel=0.002)


def test_a_run_and_a_bend_join_into_one_body(tmp_path):
    stats, faults, _ = draw(tmp_path, f"gasket_run([0, -20], [0, 0], {B}); gasket_bend([5, 0], 5, 90, 90, {B});")
    assert faults == {}
    assert stats["volume"] == pytest.approx(section_area(*B) * (20 + math.pi / 2 * 5), rel=0.01)


def test_the_path_and_the_distance_from_it(tmp_path):
    rect = [[0, 0], [40, 0], [40, 20], [0, 20]]
    body = "".join(f"echo({k} = {v});\n" for k, v in {
        "n": f"len(gasket_path({rect}, 4))",
        "mid": f"path_distance([20, 10], gasket_path({rect}, 4))",
        "out": f"path_distance([-5, 10], gasket_path({rect}, 4))",
        "corner": f"path_distance([-3, -3], gasket_path({rect}, 4))",
    }.items())
    found, _ = echoes(tmp_path, body)
    assert found["n"] == 4 * 9  # each corner's arc, 8 steps: 9 points
    assert found["mid"] == pytest.approx(10, abs=1e-3)
    assert found["out"] == pytest.approx(5, abs=1e-3)
    assert found["corner"] == pytest.approx(math.hypot(7, 7) - 4, abs=1e-3)


@pytest.mark.parametrize("body, says", [
    (f"gasket_ring({RECT}, 1, {B});", "a corner's radius 1 is under half the bead's width"),
    (f"gasket_ring({[[0, 0], [10, 0], [10, 10], [0, 10]]}, 6, {B});", "too short for the bends"),
    (f"gasket_bend([0, 0], 1, 0, 90, {B});", "a bend's radius 1 is under half the bead's width"),
], ids=["ring radius", "short side", "bend radius"])
def test_a_shape_that_cannot_be_drawn_says_why(tmp_path, body, says):
    f = source(tmp_path, body, ("gasket",))
    run = subprocess.run([OPENSCAD, "--backend=manifold", "-o", str(f.with_suffix(".stl")), str(f)],
                         capture_output=True, text=True, check=False)
    log = run.stdout + run.stderr
    assert "Assertion" in log and says in log, log[-800:]


def test_the_coupon_is_one_piece(tmp_path):
    stats, faults, _ = draw(tmp_path, f"gasket_coupon([[6, 6, 0.9], {B}], 100);")
    assert faults == {}
    assert stats["hi"][0] == pytest.approx(100, abs=1e-3)
    # each bead's length, and the web where it shows: 5 mm long, across the 5 mm between them, 2 layers thick
    # (under each bead it is inside the bead's floor)
    beads = (section_area(6, 6, 0.9) + section_area(*B)) * 100
    assert stats["volume"] == pytest.approx(beads + 5 * 5 * 0.4, rel=1e-4)


# ---------------------------------------------------------------- fdm
def test_whole_layers(tmp_path):
    found, _ = echoes(tmp_path, "echo(a = whole_layers(0.5, 0.2)); echo(b = whole_layers(0.4, 0.2));"
                      "echo(c = whole_layers(0, 0.2)); echo(d = whole_layers(1.01));", ("fdm",))
    assert found == pytest.approx({"a": 0.6, "b": 0.4, "c": 0, "d": 1.2})


@pytest.mark.parametrize("top, z_top", [("undef", 3 * math.sqrt(2)), ("2", 2)])
def test_a_teardrop_hole_has_a_45_degree_roof_or_a_flat_one(tmp_path, top, z_top):
    stats, faults, _ = draw(tmp_path, f"$fn = 64; teardrop_hole_x(6, 10, {top});", ("fdm",))
    assert faults == {}
    assert stats["lo"] == pytest.approx([0, -3, -3], abs=1e-3)
    assert stats["hi"] == pytest.approx([10, 3, z_top], abs=1e-3)


ROUND = 0.5 * 64 * 1.5 ** 2 * math.sin(2 * math.pi / 64)  # a 3 mm circle as 64 sides


@pytest.mark.parametrize("z, size, area", [(0.1, [10, 3], 30), (0.3, [3, 3], 9), (0.5, [3, 3], ROUND)],
                         ids=["slot", "square", "round"])
def test_a_bridged_hole_is_a_slot_then_a_square_then_round(tmp_path, z, size, area):
    # a 0.1 mm slice through the middle of each layer
    body = f"$fn = 64; intersection() {{ bridged_hole(10, 3, 5, 0.2); translate([-50, -50, {z - 0.05}]) cube([100, 100, 0.1]); }}"
    stats, _, _ = draw(tmp_path, body, ("fdm",))
    assert [stats["hi"][k] - stats["lo"][k] for k in (0, 1)] == pytest.approx(size, abs=1e-3)
    assert stats["volume"] == pytest.approx(area * 0.1, abs=1e-3)


# ---------------------------------------------------------------- springs
def test_a_cantilevers_force_and_root_stress_are_the_beam_formulas(tmp_path):
    E, b, t, L, d = 2000, 2.0, 0.9, 14.5, 0.7
    found, _ = echoes(tmp_path, f"echo(f = cantilever_force({E}, {b}, {t}, {L}, {d}));\n"
                      f"echo(s = cantilever_stress({E}, {t}, {L}, {d}));\n"
                      f"echo(d = cantilever_deflection(cantilever_force({E}, {b}, {t}, {L}, {d}), {E}, {b}, {t}, {L}));",
                      ("springs",))
    i = b * t ** 3 / 12
    force = 3 * E * i * d / L ** 3  # a tip load's deflection is F L^3 / 3 E I
    assert found["f"] == pytest.approx(force, rel=1e-4)
    assert found["s"] == pytest.approx(force * L * (t / 2) / i, rel=1e-4)  # M c / I at the root
    assert found["d"] == pytest.approx(d, rel=1e-4)
