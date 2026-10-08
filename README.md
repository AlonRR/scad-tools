# scad-tools

Shared tools for OpenSCAD projects: libraries a model loads with `use`, and scripts that check a model and
prepare it for publishing. Nothing here knows about any one model; each project has this repository as a
git submodule, pinned to the commit it was checked with.

| | |
|---|---|
| [`lib/shapes.scad`](lib/shapes.scad) | plain shapes - a rounded rectangle, boxes and cylinders by their ends, concave fillets along an edge or round a cylinder - and `spread()`, where a row of slots starts |
| [`lib/routes.scad`](lib/routes.scad) | wire routes as lists of corners: drawn with arcs at the corners, their tightest bend, the gap between two |
| [`lib/axes.scad`](lib/axes.scad) | the red, green and blue xyz arrows for every rendered figure, labelled to face the camera |
| [`lib/gasket.scad`](lib/gasket.scad) | a printed TPU gasket: a hollow bead squeezed in a groove, as a ring round any closed path of rounded corners, with its groove, the vent its hollow needs, a test piece to measure its squeeze, and the distance from its path for clearance checks - and why each is so |
| [`lib/fdm.scad`](lib/fdm.scad) | shapes the printer needs: teardrop holes across the layers, a hole bridged up through a ceiling, a height in whole layers |
| [`lib/springs.scad`](lib/springs.scad) | a printed clip's finger as a cantilever: its force, its root stress, how far a force bends it |
| [`lib/nuts.scad`](lib/nuts.scad) | captive hex nuts in place of heat-set inserts: the slot a nut slides into from one side, and the nut, for fit checks |
| [`scripts/scad-check.sh`](scripts/scad-check.sh) | a part end to end: render, the model's asserts, a manifold mesh - with any repair the slicer made to it, and its own edges - a slice, and the model's `fdm_*` values against the profile it was sliced with; `PARTS=N` for a plate of N separate parts |
| [`scripts/stl-mesh.py`](scripts/stl-mesh.py) | whether an STL is one clean closed body - or `--bodies N` - from its own edges rather than a slicer's report: PrusaSlicer removes degenerate facets as it loads a mesh and then calls it manifold |
| [`scripts/scad-controls.sh`](scripts/scad-controls.sh) | every control in a model README's "Guards" block, rendered, each said to have fired or not |
| [`scripts/scad-preview.sh`](scripts/scad-preview.sh) | previews, cross-sections and slices - of the exported STL, so an export bug cannot hide behind a good render |
| [`scripts/printables.py`](scripts/printables.py) | each printed part as one self-contained `.scad`, and its STL, for Printables - checked to be the same solid as the sources |
| [`scripts/stl-inspect.py`](scripts/stl-inspect.py) | measuring someone else's model before remixing it: an STL's bounds, its cross-sections at chosen heights along any axis - every loop as solid or hole, with its box, area and corners - and how a 3MF's author prints each part |
| [`scripts/scadtools.py`](scripts/scadtools.py) | what the Python scripts share: running OpenSCAD and reading its output, and telling two exports of one solid from two solids |

Libraries in `lib/` define modules and functions only - no variables, nothing drawn - so `use` brings in
everything they offer and nothing can leak into a model, and `printables.py` can write them into one file
without changing what they mean.

## In a project

```sh
git submodule add https://github.com/AlonRR/scad-tools scad-tools
```

- **Libraries**: `use` them by their path from the file that needs them, for example
  `use <../scad-tools/lib/shapes.scad>` from `models/`.
- **Scripts**: run them from the project's root - they find it with git:
  `uv run scad-tools/scripts/printables.py`, `scad-tools/scripts/scad-check.sh models/part.scad`.
- **`scad-project.toml`** at the project's root says what the scripts need to know about it:

  ```toml
  [printables]
  parts = ["models/box-back.scad", "models/box-cover.scad"]   # each part's own file
  ```

- **Updating**: `git -C scad-tools pull`, run the project's checks, and commit the new pin. The project
  records the exact commit; nothing changes under it until it is bumped.

A project's README tells a reader who cloned it to use `git clone --recursive`, and one who downloaded a
ZIP - which GitHub makes without the submodule - how to fetch it. In PowerShell, from the unpacked folder,
with OWNER/PROJECT the project's GitHub repository:

```powershell
$pin = (Invoke-RestMethod https://api.github.com/repos/OWNER/PROJECT/contents/scad-tools).sha
Invoke-WebRequest "https://github.com/AlonRR/scad-tools/archive/$pin.zip" -OutFile scad-tools.zip
Remove-Item -Recurse -ErrorAction SilentlyContinue scad-tools
Expand-Archive scad-tools.zip . ; Rename-Item "scad-tools-$pin" scad-tools ; Remove-Item scad-tools.zip
```

and in a POSIX shell:

```sh
pin=$(curl -s https://api.github.com/repos/OWNER/PROJECT/contents/scad-tools | sed -n 's/.*"sha": *"\([0-9a-f]*\)".*/\1/p')
rm -rf scad-tools && mkdir scad-tools && curl -sL "https://github.com/AlonRR/scad-tools/archive/$pin.tar.gz" | tar xz --strip-components=1 -C scad-tools
```

GitHub reports a submodule's pinned commit at its path, so the fetch gets exactly the version the project
was checked with.

## Needs

[OpenSCAD 2021.01](https://openscad.org/downloads.html) on `PATH` - the release, not a nightly: a nightly
can export a part whose assert failed - and [uv](https://docs.astral.sh/uv/) for the Python scripts.
`scad-check.sh` also slices, with PrusaSlicer. For someone else's large mesh, set `OPENSCAD` to a nightly:
its Manifold backend cuts and unions an 8 MB STL in seconds, where the release takes minutes or hours.

## Tests

```sh
uv run --with pytest pytest tests
```

[`tests/`](tests/) checks `stl-mesh.py` on small solids written for each fault, and on
[`tests/fixtures/flush-clip.scad`](tests/fixtures/flush-clip.scad), a fault OpenSCAD really made - and that
`scad-check.sh` warns on it. Those last tests need OpenSCAD (`OPENSCAD`, with the Manifold backend) and
PrusaSlicer, and are skipped without them.

[`tests/test_lib.py`](tests/test_lib.py) draws or echoes what `gasket.scad`, `fdm.scad`, `springs.scad` and
`shapes.scad`'s `slant` offer, from a small file that `use`s each, and judges the mesh: one closed body, its box,
its volume against the section's area times the centreline's length. Each check has a control that must fail it -
the ring without its vent is two bodies, and a hull() in place of the slant fills an L's concave corner. It needs
OpenSCAD with the Manifold backend too.

[`tests/test_nuts.py`](tests/test_nuts.py) fits a nut in its slot and slides it out through the mouth, and a
pull nut in its pocket's seat and down its way out of the block: each intersection must leave nothing, and a
slot or seat narrower than the nut, or one cut short of the block's face, must leave something.

## Changing it

Several projects add to this repository, sometimes at the same time.

- **Work in a checkout of your own** - a `git worktree` on its own branch, or a separate clone - never in a
  working tree someone else may be editing. Two writers in one tree share its files and its index, so one
  commits or discards the other's unfinished work, and neither is warned.
- **Land on `main` by fast-forward**: fetch, rebase onto the latest `main`, run the tests, push. A refused push
  means `main` moved, so do it again. Never force.
- **A new module or function is open to any project.** Search `lib/` first for one that already does the job.
- **Changing an existing one is more than an edit.** The projects that pin this repository call it by name, and
  a pin hides a break until that project next updates. Run the checks of every project that has this
  repository as a submodule against the change, or add a new name beside the old one.

## Licence

[MPL-2.0](LICENSES/MPL-2.0.txt): use these files in a project under any licence; changes to the files
themselves stay MPL-2.0. Every file carries an SPDX header, and `REUSE.toml` covers the rest.

_Parts of this repository were drafted with the help of an LLM agent; reviewed and verified locally._
