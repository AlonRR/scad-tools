#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Alon A. Rabinowitz
# SPDX-License-Identifier: MPL-2.0
# /// script
# requires-python = ">=3.11"
# ///
"""Is each STL one closed solid? Read from the file's own corners, not from a slicer's report:

  uv run stl-mesh.py FILE.stl [FILE.stl ...]

Every edge must be on exactly two faces, run once each way, with no flat facets, and the faces must make one
body. PrusaSlicer repairs a mesh as it loads it - removing degenerate facets, closing small gaps - and then
calls the result manifold, so its "manifold = yes" can stand over a mesh with broken faces. Exit status: 0
every file is clean, 1 any is not.
"""
import sys

from scadtools import mesh_problems


def main(paths):
    if not paths:
        sys.exit(__doc__)
    clean = True
    for p in paths:
        found = mesh_problems(p)
        clean &= not found
        print(f"{p}: " + ("one closed body" if not found else ", ".join(f"{k} {v}" for k, v in found.items())))
    return 0 if clean else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
