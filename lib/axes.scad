// SPDX-FileCopyrightText: 2026 Alon A. Rabinowitz
// SPDX-License-Identifier: MPL-2.0

/*
The xyz arrows for every rendered figure, so that a reading taken on a part in hand ("about
0.7 mm loose in x") maps onto the model without guessing which way is which. Red +x, green +y, blue +z,
each labelled at its tip. They show the axes of the model drawn, in that picture.

    use <../scad-tools/lib/axes.scad>      // the path from your file to scad-tools
    axes([x, y, z], l = 15, cam = [rx, ry, rz]);

cam is the picture's --camera angles: the labels are turned by them so that they face the camera. An
arrow pointing nearly at the camera lands its label on another's; nudge moves each label ([x], [y], [z])
across the picture, in label heights, so it holds at any size.
*/

module axes(p = [0, 0, 0], l = 15, cam = [0, 0, 0], nudge = [[0, 0], [0, 0], [0, 0]]) {
    d = l / 10;         // the shafts
    s = l / 3.2;        // the labels' size
    tip = 0.24 * l;     // the heads' length
    arms = [[[1, 0, 0], [0, 90, 0], "+x", [0.85, 0.12, 0.10]],
            [[0, 1, 0], [-90, 0, 0], "+y", [0.10, 0.55, 0.15]],
            [[0, 0, 1], [0, 0, 0], "+z", [0.10, 0.30, 0.90]]];
    translate(p) {
        color([0.25, 0.25, 0.25]) sphere(d = 1.6 * d, $fn = 16);
        for (i = [0 : 2]) let(a = arms[i]) color(a[3]) {
            rotate(a[1]) {
                cylinder(d = d, h = l - tip, $fn = 16);
                translate([0, 0, l - tip]) cylinder(d1 = 2.6 * d, d2 = 0, h = tip, $fn = 24);
            }
            translate(a[0] * (l + 0.8 * s)) rotate(cam) translate(nudge[i] * s) linear_extrude(0.2)
                text(a[2], size = s, halign = "center", valign = "center", font = "Liberation Sans:style=Bold");
        }
    }
}
