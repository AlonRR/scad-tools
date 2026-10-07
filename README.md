# scad-tools

Shared tools for OpenSCAD projects: libraries a model loads with `use`, and scripts that check a model and
prepare it for publishing. Nothing here knows about any one model; each project has this repository as a
git submodule, pinned to the commit it was checked with.

| | |
|---|---|
| [`lib/shapes.scad`](lib/shapes.scad) | plain shapes - a rounded rectangle, boxes and cylinders by their ends, concave fillets along an edge or round a cylinder - and `spread()`, where a row of slots starts |
| [`lib/routes.scad`](lib/routes.scad) | wire routes as lists of corners: drawn with arcs at the corners, their tightest bend, the gap between two |
| [`lib/axes.scad`](lib/axes.scad) | the red, green and blue xyz arrows for every rendered figure, labelled to face the camera |
| [`scripts/scad-check.sh`](scripts/scad-check.sh) | a part end to end: render, the model's asserts, a manifold mesh - with any repair the slicer made to it, and its own edges - a slice, and the model's `fdm_*` values against the profile it was sliced with |
| [`scripts/stl-mesh.py`](scripts/stl-mesh.py) | whether an STL is one clean closed body, from its own edges rather than a slicer's report: PrusaSlicer removes degenerate facets as it loads a mesh and then calls it manifold |
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

## Licence

[MPL-2.0](LICENSES/MPL-2.0.txt): use these files in a project under any licence; changes to the files
themselves stay MPL-2.0. Every file carries an SPDX header, and `REUSE.toml` covers the rest.

_Parts of this repository were drafted with the help of an LLM agent; reviewed and verified locally._
