# Project layout

How an OpenSCAD project that uses scad-tools lays out its files: the files you open at the top, and what they are
built from in folders, one kind each. It is the pattern large OpenSCAD projects use - one file per printed part
([Mendel90](https://github.com/nophead/Mendel90)'s `scad/`, the
[OpenFlexure microscope](https://gitlab.com/openflexure/openflexure-microscope)'s `openscad/`), shared helpers that
draw nothing (their `utils/` and `libs/`), bought parts apart from printed ones (Mendel90's and
[NopSCADlib](https://github.com/nophead/NopSCADlib)'s `vitamins/`), the settings in a file of their own, and the
positions every part reads in another (Mendel90's `conf/` and `positions.scad`).

**A small model does not need it.** One part, or a few hundred lines, stays as two files: `<part>.params.scad`, every
value set, and `<part>.scad`, which includes it and draws the part. Split when the model holds several parts, or
when one file has grown past what a reader can hold.

## The tree

```
<project>/
  models/<model>/
    <model>.scad             the entry: includes the rest in order and draws what `draw` names. Render this one
    <model>.params.scad      every value set, and nothing else - change a number here
    <model>.layout.scad      the values derived from the settings that more than one part reads; draws nothing
    vitamins/                the bought parts, one file each: what the part is, and its model
    lib/                     the model's own helpers: modules and functions only - no values, nothing drawn
    parts/                   the printed parts, one file per part or family: its own values beside its geometry
      print.scad             each part as it prints - the names draw and scad-check use - and the "all" plate
    assembly/                the parts together: where each part and each bought part sits, the assembled view,
                             and the exploded drawings
    checks/                  what the project's check scripts read: a model of the air or the clearances,
                             the guards (asserts), and the report (echoes)
    README.md                these files, and the rules below
    .check/                  scad-check's wrappers and its output - ignored by git
  scripts/
    checks/  analysis/  figures/  tools/      by what a script does; scripts/README.md lists them
  docs/                      the documents; docs/diagrams/<model>/ the figures the scripts write
  archive/                   superseded files, each at the path it had; archive/README.md says why each went
  scad-tools/                this repository, as a git submodule
```

## The rules

- **The include order is the value order.** OpenSCAD reads a model's top-level values in order, top to bottom
  through the files it includes, and a value read before it is set is `undef` - the render says
  `WARNING: Ignoring unknown variable`. Modules and functions can be read from anywhere. So the entry includes:
  the settings; the bought parts' files; `lib/`; the layout; the parts, each after every part whose values it
  reads; `assembly/`; `checks/`. A render shows no warnings.
- **`include` within the model, `use` for a library.** The model's files share its values, so the entry includes
  them. A library - `scad-tools/lib/`, or another model whose parts this one borrows - is `use`d: a `use`d file
  keeps its own values, so it draws what it always drew whatever the including model sets.
- **A setting goes in the params file - except a bought part's own numbers**, which go in its file under
  `vitamins/`: what the part *is*, measured or as sold - its size, its holes, its cable - each tagged `MEASURED`
  or `<<CONFIRM>>`. What we *decide* about it - its pilots, its clearances, the bosses it sits on, where it sits -
  stays in the params file, or in the part that places it.
- **A derived value lives with the part it describes**, in a file included before every file that reads it. A value
  that is no one part's - a level, where a section starts, a groove every seal shares - goes in the layout file.
- **A part or a bought part is drawn at its own origin, or where it sits - and its file says which.** `assembly/`
  places what is drawn at its own origin, in `<name>_home()` modules, which the assembled view, the exploded
  drawings and the checks all share.
- **Nothing in `lib/`, the layout or `vitamins/` draws on its own, and only the entry decides what is drawn**: its
  `draw` menu, whose printed parts' names are `print_part()`'s and scad-check's wrappers'.
- **Every file opens with its SPDX header and a comment** saying what it holds, that the entry includes it, and
  that it is not a model on its own.
- **Module names do not change in a reorganisation.** Check scripts and documents name them.
- **Scripts run from the project's root** and find it from their own path, one `.parent` per folder level.

## Traps the layout meets

- **A cut face takes the colour given outside the cut.** A drawing that cuts parts in half - an exploded view, a
  section - colours each part outside the cut (`color("white") cut() part();`). A colour set only inside the part's
  module leaves the cut faces in the default colour.
- **A model that fuses its own pieces by overlapping them `eps`** reaches that overlap into whatever sits beside
  them. A clearance check judges an overlap by its depth - its volume over half its surface - not its volume, or it
  reads the model's own fusing as an interference.
- **A solid that meets itself along an edge** is one closed solid to Manifold, but an exported STL merges the
  corners and gives the edge four faces, which trimesh calls open. Measure volumes as Manifold reads them.

## Moving a model into this layout

Reorganising must change nothing a check can see, and the way to know is to compare everything before and after:

1. **Record the baseline first:** the model's echo with `draw = ""`, the render's warnings, each printed part's
   fingerprint (volume, facet count, vertices), the project's checks, and every figure.
2. **Split by script, not by hand:** line ranges of the old file to new files, asserting that every line lands in
   exactly one, unless it is blank. Keep each moved line as it was.
3. **Settings copied from another model's params:** echo every copied value through the model before and after,
   and require the two tables to be identical; refuse any name set twice - a second assignment does not always warn.
4. **Prove it:** the echo identical, no warnings, every fingerprint identical, every check's lines identical, every
   figure pixel-identical. A figure whose pixels change has a cause - find it, as with the cut faces above.
5. **Move with `git mv`**, so history follows the files, and update every path that names them.
