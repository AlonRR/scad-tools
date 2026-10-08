// SPDX-FileCopyrightText: 2026 Alon A. Rabinowitz
// SPDX-License-Identifier: MPL-2.0

/*
A printed TPU gasket: a hollow bead that lies in a groove in one part and is squeezed by the other. Load it with
`use`, by its path from your file: `use <../scad-tools/lib/gasket.scad>`. Every size comes in as a parameter; the
names starting with _gk_ are this file's own helpers.

A bead is b = [w, h, t]: its width, its height free, and its wall. Its section is a hollow house - a flat base,
upright sides, a 45 degree roof, and the same shape inside - so it prints lying down with nothing hanging. A ring
of it follows a closed path of corners, each rounded to its own radius on the bead's centreline, and its groove
follows the same path, so the two always agree.

Why it is made this way - each learned on a part that was printed or checked:
- HOLLOW. Printed TPU 95A is too stiff to squeeze solid: a flat strip under a box about 150 mm square was
  estimated to want ~17 kN to seal, against the ~4 kN its six M3 screws could give. A hollow bead's stiffness
  falls as (t / w)^3, so a wall of one perimeter is about 8 times softer than two.
- THE SQUEEZE IS SET BY GEOMETRY, NOT BY TORQUE. Let the parts meet plastic on plastic - a hard stop - and the
  groove's depth sets the squeeze: h * (1 - squeeze), 20 % in the designs this came from. The groove leaves room
  each side for the bead to bulge into. A lip of the hard part over the bead also keeps hot air off the TPU.
- THE LAND. The part that presses the bead needs a flat as wide as the bead plus however far it can shift on its
  screws, each side, or a shifted lid presses the bead half off its land. Between screws it must be stiff enough
  that its sag stays well under the squeeze; half of it was the limit used.
- VENTED. A closed ring's hollow is a sealed void: air shut in at print temperature stiffens the bead and pushes
  as it warms, and the mesh is two bodies - the void's own surface is the second. gasket_ring() cuts a notch
  through the ring's inner wall; open to one side only, it is a dead end, and the outer wall and the ridge still
  seal. A bead that crosses a ring should meet it hollow to hollow, so the one notch vents both.
- RUNS REACH PAST THEIR ENDS. A run that only touched its bend face to face exported as a second body once
  rounding left a hairline between them, so each run reaches e past its ends, into the bend.
- MEASURE THE FORCE. What a millimetre of bead pushes back with at its squeeze is on no datasheet for printed TPU.
  Print gasket_coupon(), squeeze it under a known weight, and only then count screws.
*/

// ------------------------------------------------------------------ the bead
// The groove a bead lies in, as [its width, its depth]: side of room each side to bulge into, and as deep as the
// bead's height less the fraction squeeze it is pressed by.
function gasket_groove(b, side = 0.25, squeeze = 0.2) = [b[0] + 2 * side, b[1] * (1 - squeeze)];

function _gk_house(w, h) = [[-w / 2, 0], [w / 2, 0], [w / 2, h - w / 2], [0, h], [-w / 2, h - w / 2]];

// The bead's section: its base on y = 0, centred on x = 0, its ridge up.
module gasket_section(b) difference() {
    polygon(_gk_house(b[0], b[1]));
    offset(delta = -b[2]) polygon(_gk_house(b[0], b[1]));
}

// A straight bead from p0 to p1, each [x, y], lying on z = 0. It reaches e past each end, into what joins it.
module gasket_run(p0, p1, b, e = 0.01) let(v = p1 - p0)
    translate([p0[0], p0[1], 0]) rotate([0, 0, atan2(v[1], v[0])]) rotate([90, 0, 90])
        translate([0, 0, -e]) linear_extrude(height = norm(v) + 2 * e) gasket_section(b);

// A bend of radius r - on the bead's centreline - about c, from the angle a0 through a degrees counterclockwise.
module gasket_bend(c, r, a0, a, b, fn = 48) {
    assert(r > b[0] / 2, str("a bend's radius ", r, " is under half the bead's width ", b[0]));
    translate([c[0], c[1], 0]) rotate([0, 0, a0])
        rotate_extrude(angle = a, $fn = fn) translate([r, 0]) gasket_section(b);
}

// ------------------------------------------------------------------ the ring and its groove
function _gk_unit(v) = v / norm(v);
function _gk_r(R, i) = is_list(R) ? R[i] : R;
function _gk_sum(v, i = 0) = i >= len(v) ? 0 : v[i] + _gk_sum(v, i + 1);
// twice the signed area of the corners: positive when they run counterclockwise
function _gk_area2(V) = _gk_sum([for (i = [0 : len(V) - 1]) let(a = V[i], b = V[(i + 1) % len(V)]) a[0] * b[1] - b[0] * a[1]]);
// Corner i of the closed path V, rounded to its radius: [where its arc leaves the side before, where it joins the
// side after, its centre, the angle of its first point about the centre, its turn - positive to the left].
function _gk_corner(V, R, i) = let(
    n = len(V), r = _gk_r(R, i),
    d1 = _gk_unit(V[i] - V[(i + n - 1) % n]), d2 = _gk_unit(V[(i + 1) % n] - V[i]),
    th = atan2(d1[0] * d2[1] - d1[1] * d2[0], d1 * d2),
    t1 = V[i] - d1 * r * tan(abs(th) / 2),
    c = t1 + (th > 0 ? [-d1[1], d1[0]] : [d1[1], -d1[0]]) * r)
    [t1, V[i] + d2 * r * tan(abs(th) / 2), c, atan2(t1[1] - c[1], t1[0] - c[0]), th];
function _gk_corners(V, R) = [for (i = [0 : len(V) - 1]) _gk_corner(V, R, i)];

// The ring's centreline as points, in order round it: each corner's arc in n steps, the sides straight between.
function gasket_path(V, R, n = 8) = [for (k = _gk_corners(V, R)) each abs(k[4]) < 1e-6 ? [k[0]]
    : [for (j = [0 : n]) let(a = k[3] + k[4] * j / n) k[2] + norm(k[0] - k[2]) * [cos(a), sin(a)]]];

function _gk_seg(p, a, b) = let(ab = b - a) ab * ab == 0 ? norm(p - a)
    : let(s = max(0, min(1, (p - a) * ab / (ab * ab)))) norm(p - (a + ab * s));
// The least distance from the point p to a closed path of points, such as gasket_path() gives: for the checks that a
// screw's hole stays clear of a groove.
function path_distance(p, path) = min([for (i = [0 : len(path) - 1]) _gk_seg(p, path[i], path[(i + 1) % len(path)])]);

// A closed ring of bead round the corners V - each [x, y], in either direction - each rounded on the bead's
// centreline to its radius in R: one number for all, or a list, one each. It lies on z = 0, its ridge up. notch:
// the vent through its inner wall, 1 mm long, midway along its longest side.
module gasket_ring(V, R, b, notch = true, e = 0.01, fn = 48) {
    n = len(V);
    K = _gk_corners(V, R);
    radii = [for (i = [0 : n - 1]) _gk_r(R, i)];
    assert(min(radii) > b[0] / 2, str("a corner's radius ", min(radii), " is under half the bead's width ", b[0],
        ": its bend would cross its own centre"));
    for (i = [0 : n - 1]) let(j = (i + 1) % n)
        assert(norm(K[i][1] - V[i]) + norm(K[j][0] - V[j]) <= norm(V[j] - V[i]) + 1e-6,
            str("the side from ", V[i], " to ", V[j], " is too short for the bends at its ends"));
    runs = [for (i = [0 : n - 1]) [K[i][1], K[(i + 1) % n][0]]];
    lens = [for (r = runs) norm(r[1] - r[0])];
    longest = [for (i = [0 : n - 1]) if (lens[i] == max(lens)) i][0];
    difference() {
        union() for (i = [0 : n - 1]) {
            if (abs(K[i][4]) > 1e-6)
                gasket_bend(K[i][2], radii[i], K[i][4] > 0 ? K[i][3] : K[i][3] + K[i][4], abs(K[i][4]), b, fn);
            if (lens[i] > 1e-6) gasket_run(runs[i][0], runs[i][1], b, e);
        }
        if (notch) _gk_notch(runs[longest], _gk_area2(V) > 0, b, e);
    }
}
// The vent: 1 mm along the run at its middle, through the wall on the ring's inside - left of the run when the ring
// runs counterclockwise - from just over the hollow's floor to the eaves. Its sill stands 0.05 over the floor: cut
// level with it, the mesh had four degenerate facets, which a slicer silently removes.
module _gk_notch(run, ccw, b, e, sill = 0.05) let(u = run[1] - run[0], m = (run[0] + run[1]) / 2)
    translate([m[0], m[1], 0]) rotate([0, 0, atan2(u[1], u[0])]) scale([1, ccw ? 1 : -1, 1])
        translate([-0.5, b[0] / 2 - b[2] - e, b[2] + sill]) cube([1, b[2] + 2 * e, b[1] - b[0] / 2 - b[2] - sill]);

// The ring's groove in plan: a band width wide about the same centreline - gasket_groove(b)[0] wide, extruded as
// deep as gasket_groove(b)[1].
module gasket_groove_2d(V, R, width, n = 16) let(p = gasket_path(V, R, n)) difference() {
    offset(delta = width / 2) polygon(p);
    offset(delta = -width / 2) polygon(p);
}

// ------------------------------------------------------------------ the squeeze test
function _gk_y(beads, i, gap) = i == 0 ? 0 : _gk_y(beads, i - 1, gap) + (beads[i - 1][0] + beads[i][0]) / 2 + gap;
// l of each bead in beads, along +X side by side gap apart, joined at x = 0 by a web web thick and 5 mm long, so
// they print and handle as one piece. Squeeze each, clear of the web, by its groove's squeeze under a known weight:
// the force per mm is what decides how many screws, and how far apart.
module gasket_coupon(beads, l = 100, gap = 5, web = 0.4) {
    ys = [for (i = [0 : len(beads) - 1]) _gk_y(beads, i, gap)];
    for (i = [0 : len(beads) - 1]) gasket_run([0, ys[i]], [l, ys[i]], beads[i], 0);
    if (len(beads) > 1) cube([5, ys[len(ys) - 1], web]);
}
