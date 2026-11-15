#!/usr/bin/env python3
"""Pack local Horizon mods into one zip for upload.sh.

The archive keeps each bundle folder and each .hnmod file intact. The builder
can then scan the uploaded zip and compile every mod it finds.
"""

from __future__ import annotations

import argparse
import os
import sys
import zipfile
from pathlib import Path

from build_mods import SKIP_DIRS, bundle_roots, safe_name


def collect(paths: list[str]) -> list[tuple[Path, str]]:
    items: list[tuple[Path, str]] = []
    seen_paths: set[Path] = set()

    def add(path: Path, name: str) -> None:
        resolved = path.resolve()
        if resolved in seen_paths:
            return
        seen_paths.add(resolved)
        items.append((path, name))

    for raw in paths:
        path = Path(raw).expanduser().resolve()
        if not path.exists():
            raise SystemExit(f"error: {raw}: no such file or folder")
        if path.is_file():
            if path.suffix.lower() not in {".hnmod", ".zip"}:
                raise SystemExit(
                    f"error: {path}: expected a mod folder, .hnmod or .zip file"
                )
            add(path, path.name)
            continue
        roots = bundle_roots(path)
        for root in roots:
            name = root.name if root != path else path.name
            add(root, safe_name(name))
        for hnmod in sorted(path.rglob("*.hnmod")):
            if SKIP_DIRS.intersection(hnmod.relative_to(path).parts):
                continue
            if any(root == hnmod.parent or root in hnmod.parents for root in roots):
                continue
            add(hnmod, hnmod.name)
    if not items:
        raise SystemExit(
            "error: no Horizon mods found. Pass a bundle folder, a folder of "
            "bundles, or .hnmod files."
        )
    return items


def unique_name(base: str, used: set[str], *, suffix: str = "") -> str:
    candidate = base
    counter = 2
    while candidate.lower() in used:
        if suffix:
            candidate = f"{Path(base).stem}-{counter}{suffix}"
        else:
            candidate = f"{base}-{counter}"
        counter += 1
    used.add(candidate.lower())
    return candidate


def write_zip(items: list[tuple[Path, str]], output: Path) -> int:
    output.parent.mkdir(parents=True, exist_ok=True)
    used: set[str] = set()
    written = 0
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path, name in items:
            if path.is_file():
                archive.write(path, unique_name(name, used))
                written += 1
                continue
            arcname = unique_name(name, used)
            for directory, dirnames, filenames in os.walk(path, followlinks=False):
                dirnames[:] = sorted(
                    dirname for dirname in dirnames if dirname not in SKIP_DIRS
                )
                for filename in sorted(filenames):
                    file_path = Path(directory) / filename
                    if file_path.resolve() == output.resolve():
                        continue
                    relative = file_path.relative_to(path)
                    archive.write(file_path, f"{arcname}/{relative.as_posix()}")
                    written += 1
        archive.writestr(
            "HORIZON-MODS.txt",
            "Local mods packed for the Horizon mod builder:\n"
            + "\n".join(f"- {name}" for _, name in items)
            + "\n",
        )
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pack local Horizon mods into one zip.")
    parser.add_argument("paths", nargs="+", help="mod folders, folders of mods, .hnmod or .zip files")
    parser.add_argument("--output", required=True, help="zip file to write")
    args = parser.parse_args(argv)

    items = collect(args.paths)
    output = Path(args.output).expanduser().resolve()
    written = write_zip(items, output)
    print(f"Packed {len(items)} mod source(s), {written} file(s): {output}", file=sys.stderr)
    for path, _ in items:
        print(f"  - {path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
