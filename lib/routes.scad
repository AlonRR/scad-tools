// SPDX-FileCopyrightText: 2026 Alon A. Rabinowitz
// SPDX-License-Identifier: MPL-2.0

/*
Wire routes, as pure functions of their corners - nothing here knows about any one model. Load it with
`use`, by its path from your file: `use <../scad-tools/lib/routes.scad>`. The names starting with _ are this
file's own helpers.

A route is a list of corners. Each corner is drawn as a circular arc of radius r where the segments leave
room for one: an end segment may give all its length to its one bend, a middle segment half to each of its
two. Where they do not, the arc is tighter - min_radius() reports it.
*/

function _unit(v) = v / norm(v);
function _turn(pts, i) = acos(max(-1, min(1, _unit(pts[i] - pts[i - 1]) * _unit(pts[i + 1] - pts[i]))));
function _cut_max(pts, i) = min(norm(pts[i] - pts[i - 1]) / (i == 1 ? 1 : 2),
                                norm(pts[i + 1] - pts[i]) / (i == len(pts) - 2 ? 1 : 2));
function _cut(pts, i, r) = min(r * tan(_turn(pts, i) / 2), _cut_max(pts, i));
function _arc(pts, i, r, n = 8) = let(th = _turn(pts, i), p = pts[i]) th < 0.5 ? [p] : let(
    ui = _unit(p - pts[i - 1]), uo = _unit(pts[i + 1] - p),
    ra = _cut(pts, i, r) / tan(th / 2), n1 = _unit(uo - ui * (ui * uo)), o = p - ui * _cut(pts, i, r) + n1 * ra)
    [for (k = [0 : n]) let(f = th * k / n) o - n1 * ra * cos(f) + ui * ra * sin(f)];

// The route as drawn: every corner replaced by its arc.
function rounded(pts, r) = concat([pts[0]], [for (i = [1 : len(pts) - 2]) each _arc(pts, i, r)], [pts[len(pts) - 1]]);
// The tightest bend the route is drawn with, given r: less than r where a segment is too short for its bend.
function min_radius(pts, r) = min([for (i = [1 : len(pts) - 2])
    _turn(pts, i) < 0.5 ? 1e9 : _cut(pts, i, r) / tan(_turn(pts, i) / 2)]);
// for the clearance checks: the drawn route, a point every step mm
function dense(pts, step = 0.4) = concat([for (i = [0 : len(pts) - 2]) let(a = pts[i], b = pts[i + 1],
    n = max(1, ceil(norm(b - a) / step))) each [for (k = [0 : n - 1]) a + (b - a) * k / n]], [pts[len(pts) - 1]]);
// The least distance between two lists of points.
function min_gap(p, q) = min([for (a = p) min([for (b = q) norm(a - b)])]);
function last(v) = v[len(v) - 1];

// A wire of diameter d and colour c along a route, its bends of radius r; s shrinks it all round, so a
// collision check passes a wire that only rests against a surface.
module wire(pts, c, d, r, s = 0, fn = 10) let(q = rounded(pts, r)) color(c) for (i = [0 : len(q) - 2])
    hull() { translate(q[i]) sphere(d = d - 2 * s, $fn = fn); translate(q[i + 1]) sphere(d = d - 2 * s, $fn = fn); }
