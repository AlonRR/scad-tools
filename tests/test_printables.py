# SPDX-FileCopyrightText: 2026 Alon A. Rabinowitz
# SPDX-License-Identifier: MPL-2.0
"""scripts/printables.py: an include or a use written inside a /* */ comment is text, not a statement. From the
repository's root:

  uv run --with pytest pytest tests

A library's usage note shows the `use` line a reader copies, as lib/axes.scad's does; and a model's comment can
name a file as an example. Neither is to be written in, looked for, or reported as left over. The last two tests
run printables.py itself and need OpenSCAD (OPENSCAD, or openscad on PATH); they are skipped without it. The
control: the same lines outside the comment are statements, and are found.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import printables

OPENSCAD = os.environ.get("OPENSCAD") or shutil.which("openscad")
SCRIPT = ROOT / "scripts" / "printables.py"

LIB = """// SPDX-FileCopyrightText: 2026 Alon A. Rabinowitz
// SPDX-License-Identifier: MPL-2.0

/*
A mark, used the way this note says:

    use <lib.scad>      // the path from your file to this one
    mark();
*/

module mark() translate([3, 0, 0]) cube(1);
"""

MODEL = """/*
An example, naming a file that is not there:

    include <missing.scad>
*/
use <lib.scad>

size = 2;
module part() { cube(size); mark(); }
"""


def project(tmp_path):
    (tmp_path / "lib.scad").write_text(LIB, encoding="utf-8")
    (tmp_path / "model.scad").write_text(MODEL, encoding="utf-8")
    (tmp_path / "part.scad").write_text("include <model.scad>\npart();\n", encoding="utf-8")
    (tmp_path / "mark.scad").write_text("use <lib.scad>\nmark();\n", encoding="utf-8")
    return tmp_path


def test_statements_are_found_outside_comments_only():
    lines = ["use <a.scad>", "/*", "    use <b.scad>      // a note", "include <c.scad>", "*/",
             "  include <d.scad> // the model", "// use <e.scad>"]
    assert printables.statements(lines) == [0, 5]


def test_a_comment_naming_a_missing_file_is_kept_as_text(tmp_path):
    part = project(tmp_path) / "part.scad"
    used = []
    lines = printables.join(part, used, ".params.scad")
    assert "    include <missing.scad>" in lines
    assert used == [(tmp_path / "lib.scad").resolve()]


def test_the_control_a_missing_file_outside_a_comment_stops_it(tmp_path):
    (tmp_path / "part.scad").write_text("include <missing.scad>\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        printables.join(tmp_path / "part.scad", [], ".params.scad")


def run(where, *parts):
    if not OPENSCAD:
        pytest.skip("no OpenSCAD")
    done = subprocess.run([sys.executable, str(SCRIPT), *parts], cwd=where, capture_output=True, text=True,
                          check=False, env={**os.environ, "OPENSCAD": OPENSCAD})
    return done.returncode, done.stdout + done.stderr


def test_a_library_whose_note_shows_its_use_is_written_in(tmp_path):
    code, out = run(project(tmp_path), "part.scad", "mark.scad")
    assert code == 0, out
    assert out.count("the same solid as its sources") == 2, out
    text = (tmp_path / "printables" / "mark.scad").read_text(encoding="utf-8")
    assert "    use <lib.scad>      // the path from your file to this one" in text
    assert printables.statements(text.splitlines()) == []


def test_lib_axes_is_written_in(tmp_path):
    (tmp_path / "axes-part.scad").write_text(f"use <{(ROOT / 'lib' / 'axes.scad').as_posix()}>\n"
                                             "cube(5);\naxes([5, 5, 5]);\n", encoding="utf-8")
    code, out = run(tmp_path, "axes-part.scad")
    assert code == 0, out
    assert "the same solid as its sources" in out, out
