# SPDX-FileCopyrightText: 2026 Alon A. Rabinowitz
# SPDX-License-Identifier: MPL-2.0
"""scripts/stl-mesh.py, and scad-check.sh's use of it. From the repository's root:

  uv run --with pytest pytest tests

The small solids are written here, so each fault is exactly the one named. The fixture flush-clip.scad is a
fault OpenSCAD really made; those tests need OpenSCAD (OPENSCAD, or openscad on PATH) and, for scad-check,
PrusaSlicer, and are skipped without them.
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

MESH = ROOT / "scripts" / "stl-mesh.py"
FIXTURE = ROOT / "tests" / "fixtures" / "flush-clip.scad"
OPENSCAD = os.environ.get("OPENSCAD") or shutil.which("openscad")
PSLICER = os.environ.get("PSLICER") or r"C:\Program Files\Prusa3D\PrusaSlicer\prusa-slicer-console.exe"

# A tetrahedron, its faces wound outwards.
P = [(0, 0, 0), (10, 0, 0), (0, 10, 0), (0, 0, 10)]
TETRA = [(0, 2, 1), (0, 1, 3), (1, 2, 3), (0, 3, 2)]


def stl(path, faces, points=P):
    lines = ["solid t"]
    for f in faces:
        lines += ["facet normal 0 0 0", " outer loop", *(f"  vertex {x} {y} {z}" for x, y, z in (points[i] for i in f)),
                  " endloop", "endfacet"]
    path.write_text("\n".join(lines + ["endsolid t"]) + "\n", encoding="ascii")
    return path


def check(path):
    return scadtools.mesh_problems(path)


def test_a_closed_solid_has_no_problems(tmp_path):
    assert check(stl(tmp_path / "t.stl", TETRA)) == {}


def test_a_missing_face_leaves_open_edges(tmp_path):
    assert check(stl(tmp_path / "t.stl", TETRA[:3]))["open edges"] == 3


def test_a_face_wound_the_wrong_way_is_found(tmp_path):
    faces = TETRA[:3] + [(0, 2, 3)]
    assert check(stl(tmp_path / "t.stl", faces))["edges wound the same way twice"] == 3


def test_two_solids_are_two_bodies(tmp_path):
    far = [(x + 50, y, z) for x, y, z in P]
    faces = TETRA + [tuple(i + 4 for i in f) for f in TETRA]
    assert check(stl(tmp_path / "t.stl", faces, P + far))["bodies"] == 2


def test_two_solids_sharing_an_edge_overshare_it(tmp_path):
    # A second tetrahedron on the first one's edge 0-1, mirrored through the plane z = -y: four faces at that edge.
    q = P + [(0, -10, 0), (0, 0, -10)]
    faces = TETRA + [(0, 1, 4), (0, 5, 1), (1, 5, 4), (0, 4, 5)]
    found = check(stl(tmp_path / "t.stl", faces, q))
    assert found["edges on more than two faces"] == 1


def test_corners_a_hair_apart_make_a_degenerate_facet(tmp_path):
    # Corner 3 split in two, 1e-9 mm apart at z = 10: exact, the solid is closed through a sliver of two
    # facets; as 32-bit floats, as a slicer reads it, the sliver's corners are one point.
    q = P + [(0, 0, 10 + 1e-9)]
    faces = [(0, 2, 1), (0, 1, 3), (1, 2, 4), (0, 4, 2), (1, 4, 3), (0, 3, 4)]
    assert check(stl(tmp_path / "t.stl", faces, q)) == {"degenerate facets": 2}


def test_three_corners_on_a_line_are_left_alone(tmp_path):
    # A corner on the edge 1-2 splits the face 0-2-1 in two but not the face 1-2-3; a facet of no area, 2-1-4,
    # closes the mesh between them, as OpenSCAD writes a corner that sits on another face's edge.
    q = P + [(5, 5, 0)]
    faces = [(0, 2, 4), (0, 4, 1), (2, 1, 4), (0, 1, 3), (1, 2, 3), (0, 3, 2)]
    assert check(stl(tmp_path / "t.stl", faces, q)) == {}


def test_the_script_says_clean_or_not_by_its_exit_code(tmp_path):
    good, bad = stl(tmp_path / "good.stl", TETRA), stl(tmp_path / "bad.stl", TETRA[:3])
    run = lambda f: subprocess.run([sys.executable, str(MESH), str(f)], capture_output=True, text=True, check=False)
    assert run(good).returncode == 0
    out = run(bad)
    assert out.returncode == 1 and "open edges 3" in out.stdout


# ---------------------------------------------------------------- the fault OpenSCAD made
def render(tmp_path, inset):
    if not OPENSCAD:
        pytest.skip("no OpenSCAD")
    out = tmp_path / f"flush-{inset}.stl"
    subprocess.run([OPENSCAD, "--backend=manifold", "-o", str(out), "-D", f"inset={inset}", str(FIXTURE)],
                   capture_output=True, check=True)
    return out


def test_the_flush_clip_is_found(tmp_path):
    # PrusaSlicer reports the same eight, as degenerate_facets, and removes them.
    assert check(render(tmp_path, 0)) == {"degenerate facets": 8}


def test_the_clip_moved_inside_is_clean(tmp_path):
    assert check(render(tmp_path, 0.01)) == {}


@pytest.mark.skipif(not Path(PSLICER).exists(), reason="no PrusaSlicer")
@pytest.mark.parametrize("inset, broken", [(0, True), (0.01, False)])
def test_scad_check_fails_the_flush_clip(tmp_path, inset, broken):
    if not OPENSCAD:
        pytest.skip("no OpenSCAD")
    scad = tmp_path / "flush.scad"
    scad.write_text(FIXTURE.read_text().replace("inset = 0;", f"inset = {inset};"), encoding="utf-8")
    env = dict(os.environ, OPENSCAD=OPENSCAD)
    run = subprocess.run(["sh", str(ROOT / "scripts" / "scad-check.sh"), scad.as_posix()], capture_output=True,
                         text=True, env=env, check=False)
    # It builds and the slicer can print it, so it is a warning (exit 2), not a failure - but never a PASS.
    assert ("~~ the slicer repaired" in run.stdout) == broken, run.stdout
    assert ("~~ mesh: degenerate facets 8" in run.stdout) == broken, run.stdout
    assert run.returncode == (2 if broken else 0), run.stdout
