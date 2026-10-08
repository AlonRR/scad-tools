// SPDX-FileCopyrightText: 2026 Alon A. Rabinowitz
// SPDX-License-Identifier: MPL-2.0

/*
Captive hex nuts, in place of heat-set inserts: a slot a nut slides into flat, from one side; a pull nut's pocket,
which a nut goes up into from below; and the nut itself, for fit checks. Load it with `use`, by its path from your file: `use <../scad-tools/lib/nuts.scad>`. Every size
comes in as a parameter; an M3 nut, ISO 4032, is 5.5 across its flats and 2.4 tall.

Both are drawn with the screw's axis on Z, and the slot opening along +X: rotate and move them into place. The nut
lies with its flats facing +-Y and its corners along X, as it slides. The slot is the nut's flats wide, plus fit
each side - a hole's compensation and the nut's play together. Behind the axis it ends where the nut's back corner
stops with the nut on the axis, give or take fit; ahead it runs `out` past the axis, to its mouth. Its height h is
the caller's: the nut's, plus play, in whole layers (fdm.scad's whole_layers). A screw through the nut holds it in;
the roof printed over the slot takes the screw's hole as a bridged_hole (fdm.scad).
*/

// The slot, its floor at z = 0.
module nut_slot(af, h, out, fit = 0.3) {
    ac = af / cos(30);
    translate([-(ac / 2 + fit), -(af / 2 + fit), 0]) cube([ac / 2 + fit + out, af + 2 * fit, h]);
}

// The nut, its underside at z = 0. In a fit check, raise it by half the slot's play in height.
module hex_nut(af, h) cylinder(r = af / 2 / cos(30), h = h, $fn = 6);

// A pull nut's pocket, for a screw from above: the nut goes up the pocket from its open foot, and the screw pulls it
// into the seat at the top, which holds it. Drawn with the screw's axis on Z and the seat's roof at z = 0, the pocket
// below it: the seat h tall, af + 2 fit across its flats; under it the way, `way` long, af + 2 way_fit across, open
// at its foot; the corners along X, as hex_nut's. A fit is a hole's compensation and the nut's play together: a seat
// a little tighter than the way holds a nut once a spare screw has pulled it in. The roof over the seat takes the
// screw's hole as a bridged_hole (fdm.scad), its span the seat's corners, (af + 2 fit) / cos(30).
module pull_nut_pocket(af, h, way, fit = 0.2, way_fit = 0.25, e = 0.01) {
    translate([0, 0, -h]) cylinder(r = (af / 2 + fit) / cos(30), h = h, $fn = 6);
    translate([0, 0, -h - way]) cylinder(r = (af / 2 + way_fit) / cos(30), h = way + e, $fn = 6);
}
