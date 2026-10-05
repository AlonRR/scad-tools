#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Alon A. Rabinowitz
# SPDX-License-Identifier: MPL-2.0
# /// script
# requires-python = ">=3.11"
# ///
"""Each printed part of an OpenSCAD model as one self-contained .scad file, for Printables, where a model's
files are expected one per part rather than as a folder of files that include each other. Run it from the
root of the repository the parts are in - with scad-tools as a submodule there:

  uv run scad-tools/scripts/printables.py [PART.scad ...] [--out DIR] [--source-url URL] [--settings-suffix SUFFIX]

PART.scad is a file that draws one part - typically a short one that includes the model and picks the part.
With none given, the parts are read from scad-project.toml at the repository's root:

  [printables]
  parts = ["models/box-back.scad", "models/box-cover.scad"]

For each part it writes DIR/<name>.scad (default DIR: printables/) - the part's file with every file it
includes and uses written in - and DIR/<name>.stl, rendered from that one file, and checks that the STL is
the same solid as the one the sources make. DIR is build output: keep it out of git.

Why the one file means the same as the sources:
- `include <f>` is OpenSCAD pasting f in, so it is replaced by f's text.
- `use <f>` brings in f's modules and functions and nothing else. A library used that way must hold
  nothing else - this refuses one that assigns a variable or draws at its top level - so each goes in
  once, at the end.
- A variable assigned again after an include - the usual way to pick a part - takes the later value,
  worked out where it was first assigned. Within one file OpenSCAD warns about the second assignment,
  so the first is given the later value and the later one dropped: the same meaning, and no warning.
- A file's licence header - its opening // lines, when the first is an SPDX tag - is kept once, the part
  file's, at the top. After the settings file (one ending in SUFFIX, default .params.scad) comes the
  Customizer's [Hidden] group, so the Customizer offers the settings and none of the values worked out
  from them.

Exit status: 0 when every part's file renders cleanly to the same solid as its sources, 1 otherwise.
"""
import argparse
import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scadtools import ROOT, problems, render, same_solid, stl_stats  # noqa: E402

STATEMENT = re.compile(r"^\s*(include|use)\s*<([^>]+)>\s*;?\s*(//.*)?$")
ASSIGN_START = re.compile(r"^([A-Za-z_$][A-Za-z0-9_]*)\s*=")
ASSIGN_LINE = re.compile(r"^([A-Za-z_$][A-Za-z0-9_]*)\s*=\s*(.*?);(\s*(//.*|/\*.*?\*/))?\s*$")
DEFINITION = re.compile(r"^(module|function)\s+([A-Za-z_$][A-Za-z0-9_]*)")
MARK = "// ========"


def rel(path):
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def code(lines):
    """The indices of the lines that start outside a /* */ comment."""
    inside = False
    for i, line in enumerate(lines):
        if not inside:
            yield i
        for token in re.findall(r"/\*|\*/|//", line):
            if token == "//" and not inside:
                break
            inside = token == "/*" if token != "//" else inside


def licence(lines):
    """How many lines the file's licence header takes: its opening // lines, when the first is an SPDX tag."""
    if not lines or not lines[0].startswith("// SPDX-"):
        return 0
    n = 0
    while n < len(lines) and lines[n].startswith("//"):
        n += 1
    return n


def read(path):
    return path.read_text(encoding="utf-8").splitlines()


def resolve(name, here):
    """A file include or use names: beside the file that names it, then on OPENSCADPATH."""
    places = [here.parent, *map(Path, filter(None, os.environ.get("OPENSCADPATH", "").split(os.pathsep)))]
    for place in places:
        if (place / name).exists():
            return (place / name).resolve()
    sys.exit(f"{rel(here)}: cannot find {name}")


def join(path, used, suffix):
    """The file, its licence header left out, with every include written in, and every use noted and
    collected for the end."""
    out = []
    lines = read(path)
    for line in lines[licence(lines):]:
        found = STATEMENT.match(line)
        if not found:
            out.append(line)
            continue
        kind, target = found.group(1), resolve(found.group(2), path)
        if kind == "include":
            out += [f"{MARK} {rel(target)} ========", *join(target, used, suffix),
                    f"{MARK} end of {rel(target)} ========"]
            if target.name.endswith(suffix):
                out += ["// Everything below is worked out from the settings above: the Customizer offers only those.",
                        "/* [Hidden] */"]
        else:
            if target not in used:
                used.append(target)
            out.append(f"// {rel(target)} - its modules and functions are at the end of this file")
    return out


def library(path):
    """A used file's text, once it is clear it only defines: a variable assigned or a shape drawn at its top
    level would be hidden by `use`, and would not be in one file."""
    lines = read(path)
    lines = lines[licence(lines):]
    for i in code(lines):
        line = lines[i]
        if STATEMENT.match(line):
            sys.exit(f"{rel(path)}:{i + 1}: a library that includes or uses another is not handled")
        if line[:1].isalpha() and not DEFINITION.match(line):
            sys.exit(f"{rel(path)}:{i + 1}: assigns or draws at its top level - `use` hides that, one file would not")
    return [f"{MARK} {rel(path)}, used ========", *lines, f"{MARK} end of {rel(path)} ========"]


def settle(lines):
    """Each variable assigned more than once takes its last value at its first place; the rest are dropped.
    Returns the lines and the names it settled."""
    where = {}
    for i in code(lines):
        found = ASSIGN_START.match(lines[i])
        if found:
            where.setdefault(found.group(1), []).append(i)
    settled = []
    for name, places in where.items():
        if len(places) < 2:
            continue
        whole = [ASSIGN_LINE.match(lines[i]) for i in places]
        if not all(whole):
            sys.exit(f"{name} is assigned {len(places)} times, not all on one line - cannot settle it")
        lines[places[0]] = f"{name} = {whole[-1].group(2)};{whole[0].group(3) or ''}"
        for i in places[1:]:
            lines[i] = None
        settled.append(name)
    lines = [line for line in lines if line is not None]
    names = [found.group(0) for found in (DEFINITION.match(lines[i]) for i in code(lines)) if found]
    twice = sorted({n for n in names if names.count(n) > 1})
    if twice:
        sys.exit(f"defined twice: {', '.join(twice)}")
    return lines, settled


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def public_url():
    """The repository's GitHub address, from a remote that points there, if any does."""
    for remote in git("remote").split():
        url = git("remote", "get-url", remote)
        if "github.com" in url:
            return re.sub(r"\.git$", "", re.sub(r"^git@github\.com:", "https://github.com/", url))
    return ""


def bundle(part, suffix, url):
    path = ROOT / part
    used = []
    lines = join(path, used, suffix)
    # the part file's own opening comment says why it exists in the repository; the header below replaces it
    while lines and not lines[0].startswith(MARK) and (lines[0].startswith("//") or not lines[0].strip()):
        lines.pop(0)
    for library_path in used:
        lines += ["", *library(library_path)]
    lines, settled = settle(lines)
    edited = git("status", "--porcelain", "--", ".")
    commit = (git("rev-parse", "--short", "HEAD") or "unknown") + ("+edits" if edited else "")
    script = rel(Path(__file__).resolve())
    own = read(path)
    head = [*own[:licence(own)], "//",
            f"// One file for Printables: {part} with every file it includes and uses",
            f"// written in, by {script} at commit {commit}. Open it in OpenSCAD and render (F6);",
            "// the Customizer offers the settings. Its sources, one job to a file, are at",
            (f"// {url}" if url else "// the repository it came from")
            + " - change those and make this again, rather than editing it.", ""]
    return "\n".join(head + lines) + "\n", settled


def configured_parts():
    config = ROOT / "scad-project.toml"
    if not config.exists():
        sys.exit("name the part files, or list them in scad-project.toml under [printables] parts")
    return tomllib.loads(config.read_text(encoding="utf-8")).get("printables", {}).get("parts", [])


def main():
    ask = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ask.add_argument("parts", nargs="*", help="files that each draw one part (default: scad-project.toml)")
    ask.add_argument("--out", default="printables", help="where the one-file parts go (default: printables)")
    ask.add_argument("--source-url", help="where the sources are, for the header (default: a GitHub remote)")
    ask.add_argument("--settings-suffix", default=".params.scad", help="the settings file's ending")
    given = ask.parse_args()
    parts = given.parts or configured_parts()
    url = given.source_url if given.source_url is not None else public_url()
    out = ROOT / given.out
    out.mkdir(parents=True, exist_ok=True)
    ok = True
    for part in parts:
        name = Path(part).stem
        text, settled = bundle(part, given.settings_suffix, url)
        scad, stl, original = out / f"{name}.scad", out / f"{name}.stl", out / f"{name}.sources.stl"
        scad.write_text(text, encoding="utf-8", newline="\n")
        for f in (stl, original):
            f.unlink(missing_ok=True)
        _, log = render(stl, rel(scad), [])
        render(original, part, [])
        bad = problems(log)
        left = [line for line in text.splitlines() if STATEMENT.match(line)]
        same = stl.exists() and original.exists() and same_solid(stl_stats(stl), stl_stats(original))
        original.unlink(missing_ok=True)
        verdict = ("FAIL  " + "; ".join(bad)[:200] if bad else "FAIL  an include or use is left" if left
                   else "ok    the same solid as its sources" if same else "FAIL  not the same solid as its sources")
        ok &= verdict.startswith("ok")
        print(f"{rel(scad):40} {len(text.splitlines()):5} lines   {verdict}"
              + (f"   (settled: {', '.join(settled)})" if settled else ""))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
