// SPDX-FileCopyrightText: 2026 Alon A. Rabinowitz
// SPDX-License-Identifier: MPL-2.0

/*
Shapes that are the way they are because a printer builds them a layer at a time, on what is already there. Load it
with `use`, by its path from your file: `use <../scad-tools/lib/fdm.scad>`. Every size comes in as a parameter.
*/

// A height rounded up to whole layers of layer_h: how tall a feature really prints.
function whole_layers(z, layer_h = 0.2) = ceil(z / layer_h - 1e-6) * layer_h;

// A teardrop: a circle of diameter d with a 45 degree roof in place of the bridge over it, its point up +Y - or cut
// flat at top over its centre, where the point would reach too far; the flat is then a short bridge. A hole of this
// section, lying across the layers, prints without support.
module teardrop2d(d, top = undef) intersection() {
    hull() {
        circle(d = d);
        polygon([[-d / 2 * sin(45), d / 2 * cos(45)], [d / 2 * sin(45), d / 2 * cos(45)], [0, d / 2 * sqrt(2)]]);
    }
    if (!is_undef(top)) translate([-d, -d]) square([2 * d, d + top]);
}
// A hole of that section along +X, from x = 0 to l, its point up +Z.
module teardrop_hole_x(d, l, top = undef) rotate([90, 0, 90]) linear_extrude(height = l) teardrop2d(d, top);

// A round hole of diameter d up through a ceiling, l deep, printed with no support: the three-layer two-bridge.
// Authored with the ceiling's underside at z = 0 and the room under it; the print's up is +Z. One layer each: a slot
// the hole's width right across the room below (span long, along X), bridged from wall to wall; then the hole's
// square, bridged across the slot; then the round hole, which stands on the square's edges. Each is a superset of the
// next, so the order of the cuts cannot matter.
module bridged_hole(span, d, l, layer_h = 0.2, e = 0.01) {
    translate([-span / 2, -d / 2, -e]) cube([span, d, layer_h + e]);
    translate([-d / 2, -d / 2, -e]) cube([d, d, 2 * layer_h + e]);
    translate([0, 0, -e]) cylinder(h = l + e, d = d);
}
