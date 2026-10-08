// SPDX-FileCopyrightText: 2026 Alon A. Rabinowitz
// SPDX-License-Identifier: MPL-2.0

/*
A printed spring - a clip's finger, a snap's arm, a detent - as a cantilever: fixed at its root, its tip pushed d.
The beam formulas for the sizes that decide a design; nothing drawn. Load it with `use`, by its path from your
file: `use <../scad-tools/lib/springs.scad>`. E in MPa and lengths in mm give forces in N and stresses in MPa.

- t is the thickness in the direction it bends. The force goes as t^3: a finger two perimeters thick is about 8
  times stiffer than one of a single perimeter.
- Round the root. The stress is highest there, and a sharp inside corner is where a finger cracks or, warm, starts
  to relax. A slit beside the finger with a round end puts a fillet of half the slit's width at the root.
- Warm plastic creeps. For ASA at about 85 degC, a root under ~10 MPa was the limit used - a judgement, since
  stress-relaxation data that hot is scarce - and a test piece baked at service temperature measures what preload
  is left.
*/

// The force at the tip of a cantilever L long, b wide and t thick, bent d by it: 3 E I d / L^3.
function cantilever_force(E, b, t, L, d) = E * b * pow(t, 3) * d / (4 * pow(L, 3));
// The bending stress at its root: 3 E t d / (2 L^2).
function cantilever_stress(E, t, L, d) = 3 * E * t * d / (2 * pow(L, 2));
// How far a force F at its tip bends it.
function cantilever_deflection(F, E, b, t, L) = F * 4 * pow(L, 3) / (E * b * pow(t, 3));
