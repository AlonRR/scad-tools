// SPDX-FileCopyrightText: 2026 Alon A. Rabinowitz
// SPDX-License-Identifier: MPL-2.0
//
// Patterns of holes for a grille or a mesh, in 2-D: extrude them and cut a plate, clipped to its window.
//
//   hemp_leaf_holes(size, tile, bar)    the hemp-leaf pattern (asanoha) over a rectangle
//   honeycomb_holes(size, hole, web)    whole hexagonal holes inside a rectangle, every web the same
//   honeycomb_centres(size, hole, web)  their centres, to count them or to place something at each
//
// Both are centred on the origin. A pattern of many holes cut by linear_extrude needs a convexity there
// (10 is plenty) or a preview draws it as blobs; the render is right either way.

// The hemp-leaf pattern: a lattice of equilateral triangles `tile` long a side, each split in three by spokes from
// its centre to its corners; every side and every spoke is a bar `bar` wide. The holes are the thirds of the
// triangles, each shrunk by half a bar, so their corners stay sharp. One corner of the lattice is at the origin and
// one side runs along X; the rows of corners stand tile * sqrt(3) / 2 apart, every other row moved half a side.
// The holes cover at least `size`, [x, y]: intersect them with the window they are cut in.
// Open: (1 - bar / 2 * (2 * sqrt(3) + 4) / tile)^2 of the area, the inradius of each third shrunk by half a bar.
function hemp_leaf_corner(k, j, tile) = [(j + (k % 2 == 0 ? 0 : 0.5)) * tile, k * tile * sqrt(3) / 2];
module hemp_leaf_holes(size, tile, bar) let(h = tile * sqrt(3) / 2, n = ceil(size[0] / 2 / tile) + 1, m = ceil(size[1] / 2 / h) + 1)
    for (k = [-m : m - 1], j = [-n : n], up = [0, 1])
        let(p = hemp_leaf_corner(up == 1 ? k : k + 1, j, tile), q = p + [tile, 0], o = (p + q) / 2 + [0, up == 1 ? h : -h],
            c = (p + q + o) / 3)
            for (e = [[p, q], [q, o], [o, p]]) offset(delta = -bar / 2) polygon([c, e[0], e[1]]);

// A honeycomb of whole hexagonal holes, `hole` across their flats with webs `web` between them - the same web
// between every two neighbours - all inside the rectangle `size`, [x, y]. The holes' flats face along X; their
// rows run along X, half a row off the middle each side, so an even number of rows stands across Y. Turned a
// quarter, the other way round fits a different count: try both on a long narrow plate.
function honeycomb_centres(size, hole, web) = let(p = hole + web, dy = p * sqrt(3) / 2, r = hole / sqrt(3),
    hx = size[0] / 2, hy = size[1] / 2, m = ceil(hy / dy) + 1, k = ceil(hx / p) + 2)
    [for (i = [-m : m], j = [-k : k]) let(c = [(j + (i % 2 == 0 ? 0 : 0.5)) * p, (i + 0.5) * dy])
        if (abs(c[0]) + hole / 2 <= hx + 1e-9 && abs(c[1]) + r <= hy + 1e-9) c];
module honeycomb_holes(size, hole, web)
    for (c = honeycomb_centres(size, hole, web)) translate(c) rotate(90) circle(r = hole / sqrt(3), $fn = 6);
