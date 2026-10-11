// SPDX-FileCopyrightText: 2026 Alon A. Rabinowitz
// SPDX-License-Identifier: MPL-2.0

// Gridfinity's foot, as the standard draws it: 42 mm cells, each foot a rounded square 8 mm across its corners'
// circles, its wall's profile up from the bottom out at 45 degrees for 0.7 mm, straight up for 1.8, then out at 45
// degrees for 2.15 - 4.65 mm tall. Modules and functions only: `use` it. $fn comes from the caller - 64 is smooth at
// the 4 mm corners.
//
// gridfinity_foot_negative(nx, ny, clearance) is the material to REMOVE from a flat-bottomed model to leave a foot
// under each of nx by ny cells: in PrusaSlicer, load its STL as a negative volume and set its Z to the model's bottom.
// It is centred on X and Y and stands on Z = 0, exactly 4.65 mm tall. Do not run it on below Z = 0 to keep a face off
// the model's underside: there no foot is cut from it, so the extension would shave the whole bottom off the model.
// `clearance` shrinks each foot on every side - more clearance removes more material and leaves a smaller, looser
// foot; 0 is nominal.
//
// Each section of the profile is a hull() between two offset() rounded squares: a rounded square is convex, and the
// hull of two parallel convex profiles is a convex frustum, so each section - and the three stacked - is manifold by
// construction. Swept round a rounded rectangle instead (gridfinitybasket.scad's sweep_rounded()), the four walls
// meet the four corners' rotate_extrude()s in 50 non-manifold edges. The section at any height is the 34 mm core
// square offset by the profile's x there, so the construction is exact, not an approximation of the sweep.

// The cell's pitch, X and Y.
function gridfinity_cell() = [42, 42];
// The wall's profile, [out, up], from the foot's bottom.
function gridfinity_profile() = [[0, 0], [0.7, 0.7], [0.7, 0.7 + 1.8], [0.7 + 2.15, 0.7 + 1.8 + 2.15]];
// The foot's height.
function gridfinity_foot_h() = gridfinity_profile()[3][1];
// The square each section offsets, and how far, at profile point i: the 8 mm circles' radius in from the profile's
// outermost point, less the clearance.
function _gridfinity_core() = gridfinity_cell()[0] - 8;
function _gridfinity_off(i, clearance) = 8 / 2 - gridfinity_profile()[3][0] + gridfinity_profile()[i][0] - clearance;

// One cell's foot, centred, its bottom on Z = 0; e is each section's end slices' thickness.
module gridfinity_foot(clearance = 0, e = 0.001) let(p = gridfinity_profile())
    for (i = [0 : len(p) - 2]) hull() {
        translate([0, 0, p[i][1]]) linear_extrude(e) offset(r = _gridfinity_off(i, clearance))
            square([_gridfinity_core(), _gridfinity_core()], center = true);
        translate([0, 0, p[i + 1][1] - e]) linear_extrude(e) offset(r = _gridfinity_off(i + 1, clearance))
            square([_gridfinity_core(), _gridfinity_core()], center = true);
    }

// The negative of nx by ny feet: their footprint's slab, 4.65 mm tall, less a foot under each cell.
module gridfinity_foot_negative(nx = 1, ny = 1, clearance = 0, e = 0.001) let(c = gridfinity_cell(), h = gridfinity_foot_h())
    difference() {
        translate([0, 0, h / 2]) cube([nx * c[0], ny * c[1], h], center = true);
        for (x = [0 : nx - 1], y = [0 : ny - 1])
            translate([(x - (nx - 1) / 2) * c[0], (y - (ny - 1) / 2) * c[1], 0]) gridfinity_foot(clearance, e);
    }
