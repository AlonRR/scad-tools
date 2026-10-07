// SPDX-FileCopyrightText: 2026 Alon A. Rabinowitz
// SPDX-License-Identifier: MPL-2.0

// A mesh fault the slicer repairs without saying so in its summary: a plate with half-teeth standing on it,
// the teeth clipped to the plate's sides - computed two ways that differ in the last bit, the plate from its
// width and the clip from a half-width plus a margin. Clipped exactly there (inset = 0), the Manifold
// backend leaves near-duplicate corners along the sides: 12 broken faces, three bodies by their edges, and
// eight degenerate facets that PrusaSlicer removes before calling the mesh manifold. Moved inside by 0.01 mm
// it is one clean body. Found in a real part's end caps, 7 Oct 2026.
inset = 0;
inner = 37.7;
margin = 0.1;
h = 20;
eps = 0.01;
pitch = inner / 11;
fdm_layer_h = 0.2;
fdm_extrusion_w = 0.45;

w = inner + 2 * margin;
translate([-w / 2, 0, 0]) cube([w, h, 1.6]);
translate([0, 0, 1.6 - eps]) linear_extrude(4 + eps) intersection() {
    translate([-inner / 2 - margin + inset, 0]) square([inner + 2 * (margin - inset), h]);
    for (i = [0 : 11]) let(x = -inner / 2 + i * pitch) polygon([[x - 1.5, 0], [x + 1.5, 0], [x, 17]]);
}
