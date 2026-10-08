// SPDX-FileCopyrightText: 2026 Alon A. Rabinowitz
// SPDX-License-Identifier: MPL-2.0

/*
Shapes that know nothing about the box: every size comes in as a parameter, so each draws the same thing
wherever it is called from. Load it with `use`, by its path from your file - `use <../scad-tools/lib/
shapes.scad>` - which brings in the modules and functions and none of the variables; this file defines none,
so nothing here can read or shadow a model's settings.
*/

// A 2D rectangle with its convex corners rounded: shrink, then grow.
module rrect(w, h, r) {
    if (r > 0) offset(r = r) offset(delta = -r) square([w, h]);
    else square([w, h]);
}

// A block spanning the given X, Y and Z ranges, its corners rounded as seen from the front.
module slab_xz(x0, x1, y0, y1, z0, z1, r = 0) {
    translate([0, y1, 0])
        rotate([90, 0, 0])
            linear_extrude(height = y1 - y0)
                translate([x0, z0]) rrect(x1 - x0, z1 - z0, r);
}
// A box from corner to corner.
module box3(a, b) translate(a) cube(b - a);

// Where to start each of as many w-wide slots as fit across [a0, a1], rib apart, the row centred in it.
function spread(a0, a1, w, rib) = let(n = floor((a1 - a0 + rib) / (w + rib)), used = n * w + (n - 1) * rib,
    start = a0 + (a1 - a0 - used) / 2) n > 0 ? [for (i = [0 : n - 1]) start + i * (w + rib)] : [];

// A cylinder along Y, and one along X.
module cyl_y(x, z, r, y0, y1, fn = 0) {
    translate([x, y0, z]) rotate([-90, 0, 0])
        if (fn > 0) cylinder(r = r, h = y1 - y0, $fn = fn); else cylinder(r = r, h = y1 - y0);
}
module cyl_x(y, z, r, x0, x1) {
    translate([x0, y, z]) rotate([0, 90, 0]) cylinder(r = r, h = x1 - x0);
}

// The solid under a 45-degree slope over any outline, its child: at z = 0 the outline inset by d, at height z inset by
// d - z, up to z = rise. Minkowski's sum of the inset outline and a cone, so it is exact where the outline's convex
// turns are at least d round - sharper ones come out rounded - and its concave corners stay sharp, where hull()
// would fill them. Cut it out of a part for a 45-degree chamfer round an edge of any shape, or out of a collar for
// its slope. The cone has an odd number of facets, fn, so its slope does not land on the outline's own vertices;
// between them it falls short of the true offset by up to rise (1 - cos(180 / fn)) - carry `rise` a little past
// the outline where the slope must reach it.
module slant(d, rise, fn = 23, e = 0.01) minkowski() {
    linear_extrude(e) offset(delta = -d) children();
    cylinder(r1 = 0, r2 = rise, h = rise, $fn = fn);
}

// ------------------------------------------------------------------ coves: concave fillets
// The cove in its own frame: the face it stands on along +X, the feature up +Y, radius r. It reaches e
// past both, into the face and the feature, so it joins them by a face rather than an edge.
module cove2d(r, e = 0.01) difference() {
    translate([-e, -e]) square([r + e, r + e]);
    translate([r, r]) circle(r = r, $fn = 32);
}
// A cove of radius r along a straight root: p on the root edge, u along the face away from the feature,
// v up the feature, w along the edge for len.
module cove_line(p, u, v, w, len, r)
    multmatrix([[u[0], v[0], w[0], p[0]], [u[1], v[1], w[1], p[1]], [u[2], v[2], w[2], p[2]], [0, 0, 0, 1]])
        linear_extrude(height = len) cove2d(r);
// A cove of radius r round a cylinder of radius rc along Y, standing on the face Y = y0.
module cove_ring_y(x, z, rc, y0, r)
    translate([x, y0, z]) rotate([-90, 0, 0]) rotate_extrude($fn = 64) translate([rc, 0]) cove2d(r);
