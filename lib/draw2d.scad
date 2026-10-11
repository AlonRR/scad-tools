// SPDX-FileCopyrightText: 2026 Alon A. Rabinowitz
// SPDX-License-Identifier: MPL-2.0

// Drafting in 2D, for a dimensioned drawing generated from a model's own values - so it cannot drift from the model:
// dimension lines with their extension lines and arrowheads, leaders, headings, axes, and dashed runs. A dashed line
// is the convention for a size not yet known: a solid line always means the number is real. Modules and functions
// only: `use` it.
//
// The sizes come from special variables the drawing sets once, at its top, and every call reads: $txt the text's size
// (0.78 unset), $lw the lines' weight (0.07), $ah an arrowhead's length (0.55). Each call's colour is its `col`, near
// black unset. Text is DejaVu Sans Bold.

function _d2_txt() = is_undef($txt) ? 0.78 : $txt;
function _d2_lw() = is_undef($lw) ? 0.07 : $lw;
function _d2_ah() = is_undef($ah) ? 0.55 : $ah;
function _d2_ink() = [0.13, 0.13, 0.13];

module arrow_at(p, ang, col = _d2_ink()) let(ah = _d2_ah())
    color(col) translate(p) rotate(ang) polygon([[0, 0], [-ah, ah * 0.32], [-ah, -ah * 0.32]]);

// A horizontal dimension: x1..x2, drawn at height y_dim, its extension lines reaching back to the feature at y_feat;
// the label above the line, or under it.
module dim_h(x1, x2, y_dim, y_feat, label, col = _d2_ink(), above = true) let(lw = _d2_lw(), txt = _d2_txt()) {
    over = (y_dim > y_feat) ? 0.5 : -0.5;
    color(col) {
        for (x = [x1, x2]) /* extension lines */
            translate([x - lw / 2, min(y_feat, y_dim + over)])
                square([lw, abs(y_dim + over - y_feat)]);
        translate([x1, y_dim - lw / 2]) square([x2 - x1, lw]); /* dim line */
    }
    arrow_at([x1, y_dim], 0, col);
    arrow_at([x2, y_dim], 180, col);
    color(col) translate([(x1 + x2) / 2, y_dim + (above ? txt * 0.55 : -txt * 1.5)])
        text(label, size = txt, halign = "center", font = "DejaVu Sans:style=Bold");
}

// A vertical dimension: y1..y2, drawn at x_dim, its extension lines reaching back to x_feat. The label stands beside
// the line rather than turned along it: easier to read on a reference drawing.
module dim_v(y1, y2, x_dim, x_feat, label, col = _d2_ink(), right = true) let(lw = _d2_lw(), txt = _d2_txt()) {
    over = (x_dim > x_feat) ? 0.5 : -0.5;
    color(col) {
        for (y = [y1, y2]) /* extension lines */
            translate([min(x_feat, x_dim + over), y - lw / 2])
                square([abs(x_dim + over - x_feat), lw]);
        translate([x_dim - lw / 2, y1]) square([lw, y2 - y1]); /* dim line */
    }
    arrow_at([x_dim, y1], 90, col);
    arrow_at([x_dim, y2], 270, col);
    color(col) translate([x_dim + (right ? 0.5 : -0.5), (y1 + y2) / 2 - txt * 0.36])
        text(label, size = txt, halign = right ? "left" : "right", font = "DejaVu Sans:style=Bold");
}

// A leader, for a feature rather than a span: from the label at `at` to the arrow at `from`.
module leader(at, from, label, col = _d2_ink()) let(lw = _d2_lw(), txt = _d2_txt(), ah = _d2_ah()) {
    d = from - at;
    u = d / norm(d);
    color(col) {
        hull() {
            translate(at + u * 0.1) circle(r = lw / 2);
            translate(from - u * ah) circle(r = lw / 2);
        }
        translate(at - [0, txt * 0.36] - u * 0.4)
            text(label, size = txt, halign = (at[0] < from[0]) ? "right" : "left", font = "DejaVu Sans:style=Bold");
    }
    arrow_at(from, atan2(-u[1], -u[0]), col);
}

module heading(t, at, col = _d2_ink()) color(col) translate(at) text(t, size = _d2_txt() * 1.25, font = "DejaVu Sans:style=Bold");

// An axis from the origin at angle ang, len long, its label past its arrow.
module axis(label, ang, len, col = _d2_ink()) let(lw = _d2_lw(), txt = _d2_txt(), ah = _d2_ah()) {
    color(col) {
        rotate(ang) translate([0, -lw / 2]) square([len - ah, lw]);
        translate([cos(ang) * (len + 0.85) - txt * 0.32, sin(ang) * (len + 0.85) - txt * 0.4])
            text(label, size = txt, font = "DejaVu Sans:style=Bold");
    }
    arrow_at([cos(ang) * len, sin(ang) * len], ang + 180, col);
}

// A dashed run from a to b: a size not yet known.
module dashed(a, b, dash = 0.55, gap = 0.34, col = [0.1, 0.1, 0.1]) let(lw = _d2_lw()) {
    d = b - a;
    L = norm(d);
    n = floor(L / (dash + gap));
    u = d / L;
    color(col) for (i = [0 : max(n, 0)]) {
        s = i * (dash + gap);
        e = min(s + dash, L);
        if (e > s)
            hull() {
                translate(a + u * s) circle(r = lw / 2);
                translate(a + u * e) circle(r = lw / 2);
            }
    }
}

// A dashed rectangle, centred on the origin, or on `at`: an outline of unknown size.
module dashed_rect(w, h, col = [0.1, 0.1, 0.1]) {
    dashed([-w / 2, -h / 2], [w / 2, -h / 2], col = col);
    dashed([w / 2, -h / 2], [w / 2, h / 2], col = col);
    dashed([w / 2, h / 2], [-w / 2, h / 2], col = col);
    dashed([-w / 2, h / 2], [-w / 2, -h / 2], col = col);
}
module dashed_rect_at(w, h, at, col = [0.1, 0.1, 0.1]) translate(at) dashed_rect(w, h, col);
