// SPDX-FileCopyrightText: 2026 Alon A. Rabinowitz
// SPDX-License-Identifier: MPL-2.0

/*
Captive hex nuts, in place of heat-set inserts: a slot a nut slides into flat, from one side, and the nut itself,
for fit checks. Load it with `use`, by its path from your file: `use <../scad-tools/lib/nuts.scad>`. Every size
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
