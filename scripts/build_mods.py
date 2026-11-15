#!/usr/bin/env python3
"""Build Horizon native mods with the official Horizon launcher.

The launcher already contains Horizon's complete native-mod compiler: it
downloads the exact Horizon and horizon-mixins source a mod pins, applies the
mixins, compiles the game, and installs the result as ``native-<commit>-<key>``.
This script turns that into a reproducible builder:

* accepts source bundles, unpacked/packed ``.hnmod`` files, local folders,
  git/GitHub URLs, and the test mods from issue #1;
* installs and prepares a Horizon base version in an isolated launcher home;
* compiles every mod with ``horizon_launcher native-build``;
* packs source bundles into valid ``.hnmod`` files;
* writes downloadable native-build archives and a ``manifest.json`` under
  ``dist/``.

Nothing is installed system-wide and no Microsoft/Minecraft credentials are
needed: preparation uses the client jar and libraries in
``configs/minecraft/.minecraft``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Iterable

try:
    import tomllib
except ModuleNotFoundError:  # Python < 3.11
    tomllib = None  # type: ignore[assignment]

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "horizon_launcher"
DEFAULT_MINECRAFT = ROOT / "configs" / "minecraft" / ".minecraft"
TEST_MODS_FILE = ROOT / "configs" / "test-mods.json"
DIST = ROOT / "dist"
WORK = ROOT / ".work"

# Repositories that are the engine, not a mod source. Issue text often links them.
IGNORED_REPOS = {
    "horizon-rust/horizon",
    "horizon-rust/horizon-mixins",
    "horizon-rust/horizon-site",
    "horizon-rust/horizon-server",
}

GITHUB_RE = re.compile(r"github\.com[/:]([^/\s]+)/([^/\s#?]+)")
URL_RE = re.compile(r"https?://[^\s<>\"')\]]+")


class BuildError(RuntimeError):
    pass


def say(message: str = "") -> None:
    print(message, flush=True)


def safe_name(text: str) -> str:
    text = re.sub(r"[^A-Za-z0-9._-]+", "-", text.strip())
    return text.strip("-") or "mod"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(
    command: list[str],
    *,
    env: dict[str, str],
    log_path: Path | None = None,
    cwd: Path | None = None,
    check: bool = True,
) -> tuple[int, str]:
    """Run a command, stream its output, and optionally keep it in a log file."""
    rendered = " ".join(str(part) for part in command)
    say(f"+ {rendered}")
    output: list[str] = []
    log_file = None
    if log_path is not None:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_file = log_path.open("a", encoding="utf-8")
        log_file.write(f"+ {rendered}\n")
        log_file.flush()
    try:
        process = subprocess.Popen(
            command,
            cwd=str(cwd) if cwd else None,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
        )
        assert process.stdout is not None
        for line in process.stdout:
            sys.stdout.write(line)
            sys.stdout.flush()
            output.append(line)
            if log_file is not None:
                log_file.write(line)
                log_file.flush()
        code = process.wait()
    finally:
        if log_file is not None:
            log_file.close()
    if check and code != 0:
        raise BuildError(f"command failed with exit code {code}: {rendered}")
    return code, "".join(output)


def download(url: str, destination: Path, *, env: dict[str, str]) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    say(f"+ download {url}")
    headers = {"User-Agent": "horizon-mod-builder"}
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token and url.startswith(
        ("https://github.com/", "https://api.github.com/", "https://objects.githubusercontent.com/")
    ):
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request) as response, destination.open("wb") as file:
            shutil.copyfileobj(response, file)
    except urllib.error.URLError as error:
        raise BuildError(f"could not download {url}: {error}") from error
    return destination


def github_api(url: str) -> dict:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "horizon-mod-builder",
            "Accept": "application/vnd.github+json",
        },
    )
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request) as response:
            return json.load(response)
    except (urllib.error.URLError, json.JSONDecodeError) as error:
        raise BuildError(f"GitHub API request failed for {url}: {error}") from error


def repo_from_url(url: str) -> str | None:
    match = GITHUB_RE.search(url)
    if not match:
        return None
    owner, repo = match.group(1), match.group(2)
    if repo.endswith(".git"):
        repo = repo[:-4]
    return f"{owner}/{repo}"


def is_github_repo_url(url: str) -> bool:
    repo = repo_from_url(url)
    if not repo:
        return False
    # A release asset or a deep link is not a repository root.
    tail = url.split("github.com", 1)[-1]
    if any(part in tail for part in ("/issues/", "/pull/", "/actions/", "/commit/", "/tree/")):
        return False
    if tail.count("/") > 2 and not url.endswith(".git"):
        return False
    return True


SKIP_DIRS = {
    ".git",
    ".work",
    "target",
    "dist",
    "build",
    "out",
    "node_modules",
    "__pycache__",
    ".cargo",
    ".gradle",
    ".venv",
    "venv",
}


def valid_bundle(directory: Path) -> bool:
    return (directory / "horizon-mixin.toml").is_file() or (
        directory / "horizon-native.json"
    ).is_file()


def bundle_manifests(directory: Path) -> list[Path]:
    direct = [directory / "horizon-mixin.toml", directory / "horizon-native.json"]
    if any(path.is_file() for path in direct):
        return [directory]
    mixins = directory / "mixins"
    found: list[Path] = []
    if mixins.is_dir():
        for manifest in sorted(mixins.glob("*/horizon-mixin.toml")):
            found.append(manifest.parent)
    if found:
        return found
    for child in sorted(directory.iterdir()):
        if child.is_dir() and valid_bundle(child):
            found.append(child)
    return found


def _extract_zip(path: Path, destination: Path) -> Path:
    """Safely extract a zip with no assumptions about its layout."""
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path) as archive:
        for member in archive.infolist():
            name = member.filename.replace("\\", "/")
            if not name or name.startswith("/") or ":" in name.split("/")[0]:
                raise BuildError(f"{path}: unsafe zip entry {member.filename!r}")
            parts = [part for part in name.split("/") if part not in ("", ".")]
            if not parts:
                continue
            if any(part == ".." for part in parts):
                raise BuildError(f"{path}: unsafe zip entry {member.filename!r}")
            target = destination.joinpath(*parts)
            if member.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as source, target.open("wb") as file:
                shutil.copyfileobj(source, file)
    return destination


def extract_hnmod(path: Path, destination: Path) -> Path:
    _extract_zip(path, destination)
    if not valid_bundle(destination):
        raise BuildError(f"{path}: not a Horizon mod (.hnmod) archive")
    return destination


def bundle_roots(directory: Path) -> list[Path]:
    """Find Horizon bundles in an extracted archive, allowing wrappers and nesting."""
    roots: list[Path] = []
    if valid_bundle(directory) or ((directory / "mixins").is_dir() and any(
        (directory / "mixins").glob("*/horizon-mixin.toml")
    )):
        return [directory]
    direct = bundle_manifests(directory)
    if direct:
        return direct
    for manifest in sorted(directory.rglob("horizon-native.json")):
        if SKIP_DIRS.intersection(manifest.relative_to(directory).parts):
            continue
        roots.append(manifest.parent)
    for manifest in sorted(directory.rglob("horizon-mixin.toml")):
        if SKIP_DIRS.intersection(manifest.relative_to(directory).parts):
            continue
        parent = manifest.parent
        native = parent
        while native != directory.parent:
            if (native / "horizon-native.json").is_file():
                parent = native
                break
            if native == directory:
                break
            native = native.parent
        roots.append(parent)
    unique: list[Path] = []
    for root in sorted(set(roots), key=lambda path: (len(path.parts), str(path))):
        if any(root == known or known in root.parents for known in unique):
            continue
        unique.append(root)
    if unique:
        return unique
    # GitHub source archives wrap the checkout in one directory.
    children = [child for child in sorted(directory.iterdir()) if child.is_dir()]
    if len(children) == 1:
        return bundle_roots(children[0])
    return []


def read_manifest(directory: Path) -> tuple[str, str, dict]:
    """Return (id, version, manifest mapping) for a bundle."""
    native_path = directory / "horizon-native.json"
    if native_path.is_file():
        native = json.loads(native_path.read_text(encoding="utf-8"))
        return str(native.get("id", "")), str(native.get("version", "")), native
    mixin_path = directory / "horizon-mixin.toml"
    if not mixin_path.is_file():
        return "", "", {}
    if tomllib is None:
        raise BuildError("Python 3.11 or newer is needed to read horizon-mixin.toml")
    mixin = tomllib.loads(mixin_path.read_text(encoding="utf-8"))
    mod = mixin.get("mod", {})
    return str(mod.get("id", "")), str(mod.get("version", "")), mixin


class Job:
    def __init__(self, name: str, bundle: Path, source: str, original_hnmod: Path | None = None):
        self.name = name
        self.bundle = bundle
        self.source = source
        self.original_hnmod = original_hnmod
        self.mod_id = ""
        self.mod_version = ""
        self.manifest: dict = {}
        self.mod_id, self.mod_version, self.manifest = read_manifest(bundle)
        if not self.mod_id:
            self.mod_id = safe_name(bundle.name)
        if not self.name:
            self.name = self.mod_id


def stage_bundle(source: Path, stage_root: Path, job_name: str) -> Job:
    target = stage_root / safe_name(job_name)
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)

    def ignore(_directory: str, names: list[str]) -> set[str]:
        return {name for name in names if name in SKIP_DIRS}

    shutil.copytree(source, target, dirs_exist_ok=True, ignore=ignore)
    return Job(job_name, target, str(source))


def jobs_from_tree(directory: Path, source: str, stage_root: Path) -> list[Job]:
    """Turn an extracted archive or a folder into buildable mod jobs."""
    roots = bundle_roots(directory)
    jobs: list[Job] = []
    seen: set[str] = set()
    for root in roots:
        name = root.name if root != directory else directory.name
        base = safe_name(name)
        candidate = base
        counter = 2
        while candidate in seen:
            candidate = f"{base}-{counter}"
            counter += 1
        seen.add(candidate)
        job = stage_bundle(root, stage_root, candidate)
        job.source = source
        jobs.append(job)
    for hnmod in sorted(directory.rglob("*.hnmod")):
        if SKIP_DIRS.intersection(hnmod.relative_to(directory).parts):
            continue
        if any(root == hnmod.parent or root in hnmod.parents for root in roots):
            continue
        try:
            unpacked = extract_hnmod(hnmod, stage_root / safe_name(hnmod.stem))
        except (OSError, zipfile.BadZipFile) as error:
            raise BuildError(f"{hnmod}: invalid .hnmod archive: {error}") from error
        jobs.append(Job(hnmod.stem, unpacked, source, original_hnmod=hnmod))
    return jobs


def jobs_from_archive(path: Path, source: str, stage_root: Path) -> list[Job]:
    extracted = _extract_zip(path, stage_root / "archives" / safe_name(path.stem))
    jobs = jobs_from_tree(extracted, source, stage_root)
    if not jobs:
        raise BuildError(f"{path}: archive holds no Horizon mod bundle or .hnmod")
    return jobs


def url_path(url: str) -> str:
    return url.split("#", 1)[0].split("?", 1)[0]


def resolve_source(
    source: str,
    stage_root: Path,
    env: dict[str, str],
    *,
    prefer_release: bool,
) -> list[Job]:
    source = source.strip()
    if not source:
        return []

    path = Path(source).expanduser()
    if path.exists():
        if path.is_file():
            if path.suffix == ".hnmod":
                unpacked = extract_hnmod(path, stage_root / safe_name(path.stem))
                return [Job(path.stem, unpacked, str(path), original_hnmod=path)]
            if zipfile.is_zipfile(path):
                return jobs_from_archive(path, str(path), stage_root)
            raise BuildError(f"{path}: expected a .hnmod, a zip, or a mod folder")
        jobs = jobs_from_tree(path, str(path), stage_root)
        if jobs:
            return jobs
        raise BuildError(f"{path}: no horizon-mixin.toml, horizon-native.json, or .hnmod found")

    if source.startswith(("http://", "https://")):
        remote_path = url_path(source)
        if remote_path.endswith(".hnmod"):
            name = safe_name(Path(remote_path).name)
            downloaded = download(source, stage_root / "downloads" / name, env=env)
            unpacked = extract_hnmod(downloaded, stage_root / safe_name(downloaded.stem))
            return [Job(downloaded.stem, unpacked, source, original_hnmod=downloaded)]
        if remote_path.endswith(".zip"):
            name = safe_name(Path(remote_path).name)
            downloaded = download(source, stage_root / "downloads" / name, env=env)
            return jobs_from_archive(downloaded, source, stage_root)
        repo = repo_from_url(source)
        if repo and is_github_repo_url(source) and prefer_release:
            try:
                data = github_api(f"https://api.github.com/repos/{repo}/releases/latest")
                assets = [
                    asset
                    for asset in data.get("assets", [])
                    if str(asset.get("name", "")).endswith(".hnmod")
                ]
                if assets:
                    jobs = []
                    for asset in assets:
                        url = str(asset.get("browser_download_url", ""))
                        name = str(asset.get("name", "mod.hnmod"))
                        downloaded = download(url, stage_root / "downloads" / name, env=env)
                        unpacked = extract_hnmod(
                            downloaded, stage_root / safe_name(downloaded.stem)
                        )
                        jobs.append(Job(downloaded.stem, unpacked, source, original_hnmod=downloaded))
                    return jobs
            except BuildError as error:
                say(f"note: {error}; falling back to cloning the repository")
        clone = stage_root / "sources" / safe_name(repo or source)
        if clone.exists():
            shutil.rmtree(clone)
        clone.parent.mkdir(parents=True, exist_ok=True)
        run(["git", "clone", "--depth", "1", source, str(clone)], env=env)
        jobs = jobs_from_tree(clone, source, stage_root)
        if not jobs:
            raise BuildError(f"{source}: cloned repository holds no Horizon mod bundle")
        return jobs

    raise BuildError(f"unsupported mod source: {source}")


def urls_from_text(text: str) -> list[str]:
    found: list[str] = []
    for url in URL_RE.findall(text or ""):
        url = url.rstrip(".,;:")
        repo = repo_from_url(url)
        if repo and repo in IGNORED_REPOS:
            continue
        if repo and any(
            part in url for part in ("/issues/", "/pull/", "/actions/", "/commit/", "/tree/")
        ):
            continue
        if url_path(url).endswith((".hnmod", ".zip")) or is_github_repo_url(url):
            if url not in found:
                found.append(url)
    return found


def test_mod_sources() -> list[tuple[str, bool]]:
    if TEST_MODS_FILE.is_file():
        data = json.loads(TEST_MODS_FILE.read_text(encoding="utf-8"))
        result: list[tuple[str, bool]] = []
        for entry in data.get("mods", []):
            if isinstance(entry, str):
                result.append((entry, True))
            else:
                result.append((str(entry["source"]), bool(entry.get("prefer_release", True))))
        if result:
            return result
    return [
        ("https://github.com/d3grando/enchantmenthints.git", True),
        ("https://github.com/tariksabanuz/ModMenuHorizon", True),
    ]


def launcher_env(args: argparse.Namespace) -> tuple[dict[str, str], Path, Path]:
    launcher_home = Path(
        args.launcher_home
        or os.environ.get("HORIZON_LAUNCHER_HOME")
        or WORK / "launcher"
    ).resolve()
    game_home = Path(
        args.game_home or os.environ.get("HORIZON_HOME") or WORK / "game"
    ).resolve()
    launcher_home.mkdir(parents=True, exist_ok=True)
    game_home.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update(
        {
            "HORIZON_LAUNCHER_HOME": str(launcher_home),
            "HORIZON_HOME": str(game_home),
            "HORIZON_NO_AUDIO": "1",
            "HORIZON_LAUNCHER_NO_SELF_UPDATE": "1",
            "HORIZON_LAUNCHER_TRASH": str(launcher_home / "trash"),
            "HORIZON_LAUNCHER_CLIPBOARD": str(launcher_home / "clipboard"),
            "HORIZON_LAUNCHER_DESKTOP": str(launcher_home / "desktop"),
        }
    )
    env.setdefault(
        "CARGO_BUILD_JOBS", str(max(1, min(8, os.cpu_count() or 4)))
    )
    return env, launcher_home, game_home


def installed_versions(env: dict[str, str], log: Path) -> list[str]:
    _, output = run(
        [str(LAUNCHER), "versions", "--installed", "--json"],
        env=env,
        log_path=log,
        check=False,
    )
    start = output.find("{")
    if start < 0:
        return []
    try:
        return list(json.loads(output[start:]).get("installed", []))
    except json.JSONDecodeError:
        return []


def ensure_horizon(args: argparse.Namespace, env: dict[str, str], logs: Path) -> str:
    version = args.horizon_version or os.environ.get("HORIZON_VERSION") or "latest"
    log = logs / "launcher.log"
    installed = installed_versions(env, log)
    if version.lower() == "latest":
        before = set(installed)
        _, output = run(
            [str(LAUNCHER), "install", "latest"], env=env, log_path=log
        )
        after = installed_versions(env, log)
        added = [tag for tag in after if tag not in before]
        if added:
            return added[-1]
        match = re.search(r"Installed\s+([^\s]+)", output)
        if match:
            return match.group(1).rstrip(".,;:")
        _, listing = run(
            [str(LAUNCHER), "versions", "--json"],
            env=env,
            log_path=log,
            check=False,
        )
        start = listing.find("[")
        if start >= 0:
            try:
                releases = json.loads(listing[start:])
                for release in releases:
                    if release.get("available_here"):
                        return str(release["tag"])
            except (json.JSONDecodeError, KeyError):
                pass
        installed = installed_versions(env, log)
        if not installed:
            raise BuildError("the launcher installed no Horizon version")
        return installed[0]
    if version not in installed:
        run([str(LAUNCHER), "install", version], env=env, log_path=log)
    return version


def version_prepared(env: dict[str, str], tag: str, log: Path) -> bool:
    _, output = run(
        [str(LAUNCHER), "versions", "--installed"],
        env=env,
        log_path=log,
        check=False,
    )
    for line in output.splitlines():
        if re.search(rf"(^|\s){re.escape(tag)}(\s|$)", line):
            return "prepared" in line and "not prepared" not in line
    return False


def ensure_prepared(
    args: argparse.Namespace, env: dict[str, str], tag: str, logs: Path
) -> None:
    log = logs / "launcher.log"
    if version_prepared(env, tag, log):
        say(f"{tag} is already prepared")
        return
    minecraft = Path(args.minecraft_dir or DEFAULT_MINECRAFT).resolve()
    if not minecraft.is_dir():
        raise BuildError(f"Minecraft folder not found: {minecraft}")
    run(
        [
            str(LAUNCHER),
            "prepare",
            "--version",
            tag,
            "--minecraft",
            str(minecraft),
        ],
        env=env,
        log_path=log,
    )


def build_job(
    job: Job,
    args: argparse.Namespace,
    env: dict[str, str],
    base: str,
    logs: Path,
) -> tuple[str, Path, str]:
    log = logs / f"{safe_name(job.name)}.log"
    before = set((Path(env["HORIZON_LAUNCHER_HOME"]) / "versions").glob("native-*"))
    command = [
        str(LAUNCHER),
        "native-build",
        str(job.bundle),
        "--version",
        base,
        "--trust-native-code",
        "--allow-version-mismatch",
        "--profile",
        args.profile,
    ]
    if args.ignore_pins:
        command.append("--ignore-pins")
    say(f"Building {job.mod_id} {job.mod_version} from {job.source}")
    _, output = run(command, env=env, log_path=log)
    match = re.search(r"(\S+) built and selected for its instance", output)
    built = match.group(1) if match else ""
    if not built:
        after = set(
            (Path(env["HORIZON_LAUNCHER_HOME"]) / "versions").glob("native-*")
        ) - before
        built = sorted(after, key=lambda path: path.stat().st_mtime)[-1].name if after else ""
    if not built:
        raise BuildError(f"could not find the build produced for {job.mod_id}")
    build_dir = Path(env["HORIZON_LAUNCHER_HOME"]) / "versions" / built
    native_json = build_dir / "native-mods.json"
    if not native_json.is_file():
        raise BuildError(f"{build_dir} has no native-mods.json")
    metadata = json.loads(native_json.read_text(encoding="utf-8"))
    ids = [str(mod.get("id", "")) for mod in metadata.get("mods", [])]
    if ids and job.mod_id not in ids and job.name != "combined":
        raise BuildError(
            f"{built} does not contain {job.mod_id} (it holds: {', '.join(ids)})"
        )
    if not (build_dir / "horizon-client").is_file():
        raise BuildError(f"{built} has no compiled horizon-client")
    return built, build_dir, output


def toml_value(manifest: dict, *keys: str) -> str:
    value: object = manifest
    for key in keys:
        if not isinstance(value, dict):
            return ""
        value = value.get(key)
    return str(value) if value else ""


def find_compat(job: Job) -> dict:
    candidates = [job.bundle / "compatibility.json"]
    if job.source and Path(job.source).is_dir():
        candidates.extend(
            [
                Path(job.source) / "compatibility.json",
                Path(job.source).parent / "compatibility.json",
            ]
        )
    for path in candidates:
        if path.is_file():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
    return {}


def write_hnmod(
    job: Job,
    build_dir: Path,
    destination: Path,
) -> Path:
    """Pack a source bundle as a registry-schema .hnmod (or keep the input file)."""
    if job.original_hnmod and job.original_hnmod.is_file():
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(job.original_hnmod, destination)
        return destination

    native_path = job.bundle / "horizon-native.json"
    if native_path.is_file():
        native = json.loads(native_path.read_text(encoding="utf-8"))
        mod_id = str(native.get("id", job.mod_id))
        base = job.bundle / "mixins" / mod_id
        if not base.is_dir():
            base = job.bundle
        files = {"horizon-native.json": native_path.read_bytes()}
        prefix = f"mixins/{mod_id}/"
        for path in sorted(base.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(base)
            if path.suffix in {".rs", ".toml"} or relative.parts[:1] == ("data",):
                files[prefix + relative.as_posix()] = path.read_bytes()
    else:
        if tomllib is None:
            raise BuildError("Python 3.11 or newer is needed to pack .hnmod files")
        mixin = tomllib.loads((job.bundle / "horizon-mixin.toml").read_text(encoding="utf-8"))
        mod = mixin.get("mod", {})
        compatibility = mixin.get("compatibility", {})
        native_meta = json.loads((build_dir / "native-mods.json").read_text(encoding="utf-8"))
        game = "26.3"
        lock = build_dir / "research-lock.json"
        if lock.is_file():
            game = str(
                json.loads(lock.read_text(encoding="utf-8"))
                .get("minecraft", {})
                .get("version", game)
            )
        compat = find_compat(job)
        native = {
            "schema": 1,
            "id": str(mod.get("id", job.mod_id)),
            "version": str(mod.get("version", job.mod_version)),
            "game": game,
            "horizon": str(
                compatibility.get("horizon_revision")
                or native_meta.get("horizon")
                or ""
            ),
            "mixins": str(
                compat.get("horizon_mixins_revision")
                or native_meta.get("horizon_mixins")
                or ""
            ),
        }
        files = {
            "horizon-native.json": (
                json.dumps(native, indent=2, sort_keys=True) + "\n"
            ).encode()
        }
        for path in sorted(job.bundle.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(job.bundle)
            if path.suffix in {".rs", ".toml"} or relative.parts[:1] == ("data",):
                files[f"mixins/{native['id']}/{relative.as_posix()}"] = path.read_bytes()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in sorted(files.items()):
            info = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, content)
    validate_hnmod(destination)
    return destination


def validate_hnmod(path: Path) -> None:
    with zipfile.ZipFile(path) as archive:
        names = [name for name in archive.namelist() if not name.endswith("/")]
        if "horizon-native.json" not in names:
            raise BuildError(f"{path}: no horizon-native.json")
        native = json.loads(archive.read("horizon-native.json"))
        mod_id = str(native.get("id", ""))
        if not mod_id:
            raise BuildError(f"{path}: horizon-native.json has no id")
        if f"mixins/{mod_id}/horizon-mixin.toml" not in names:
            raise BuildError(f"{path}: no mixins/{mod_id}/horizon-mixin.toml")
        for name in names:
            if name == "horizon-native.json":
                continue
            if not name.startswith(f"mixins/{mod_id}/"):
                raise BuildError(f"{path}: entry outside mixins/{mod_id}/: {name}")
            if ".." in Path(name).parts or name.startswith("/"):
                raise BuildError(f"{path}: unsafe entry: {name}")


def archive_build(
    job: Job,
    built: str,
    build_dir: Path,
    destination: Path,
    hnmods: list[Path],
    metadata: dict,
    include_resources: bool,
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    base = metadata.get("base")
    mods = metadata.get("mods", [])
    mod_lines = "\n".join(
        f"  - {mod.get('id', '?')} {mod.get('version', '')}".rstrip() for mod in mods
    ) or f"  - {job.mod_id} {job.mod_version}".rstrip()
    info = (
        f"Horizon native build {built}\n"
        f"Base Horizon: {base}\n"
        f"Built Horizon revision: {metadata.get('horizon')}\n"
        f"horizon-mixins: {metadata.get('horizon_mixins')}\n"
        f"Profile: {metadata.get('profile')}\n"
        f"Source: {job.source}\n"
        "\n"
        "Mods in this build:\n"
        f"{mod_lines}\n"
        "\n"
        "The archive holds the compiled game. The mods are compiled into\n"
        "horizon-client; do not copy anything into a vanilla mods/ folder.\n"
        "The prepared Minecraft resources are not included.\n"
    ).encode()
    install = (
        f"Horizon native build {built}\n"
        f"Base Horizon: {base}\n"
        "\n"
        "Mods:\n"
        f"{mod_lines}\n"
        "\n"
        "Install and play on Linux:\n"
        f"  horizon-launcher install {base}\n"
        f"  horizon-launcher prepare --version {base}\n"
        f"  horizon-launcher import-build <this-zip> --version {base} --trust-unsigned\n"
        "  horizon-launcher play\n"
        "\n"
        "If the base version is already installed and prepared, this is enough:\n"
        "  horizon-launcher import-build <this-zip> --trust-unsigned\n"
        "  horizon-launcher play\n"
        "\n"
        'The message "It is prepared already, from another installed version."\n'
        "means the import succeeded and reuses the prepared base resources. It is\n"
        "not an error. The imported build is selected automatically.\n"
        "\n"
        "You can also use the launcher window: install and prepare the base\n"
        "version on the Versions page, then drop the zip on the window or import\n"
        "it from the Versions page, and press Play.\n"
        "\n"
        "These archives are Linux x86_64 builds made on GitHub Actions. To build\n"
        "for Windows or macOS, build locally instead (see the project README).\n"
    ).encode()
    skip_top = set() if include_resources else {".local"}
    with zipfile.ZipFile(
        destination, "w", zipfile.ZIP_DEFLATED, compresslevel=6
    ) as archive:
        archive.writestr("BUILD-INFO.txt", info)
        archive.writestr("INSTALL.txt", install)
        for entry in sorted(build_dir.iterdir()):
            if entry.name in skip_top:
                continue
            if entry.is_dir():
                for path in sorted(entry.rglob("*")):
                    if path.is_file():
                        archive.write(path, path.relative_to(build_dir).as_posix())
            elif entry.is_file():
                archive.write(entry, entry.name)
        for hnmod in hnmods:
            if hnmod.is_file():
                archive.write(hnmod, f"mod-source/{hnmod.name}")


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compile Horizon native mods and collect downloadable artifacts."
    )
    parser.add_argument("sources", nargs="*", help="mod folders, .hnmod files, git/GitHub URLs")
    parser.add_argument("--test-mods", action="store_true", help="build the test mods from issue #1")
    parser.add_argument("--issue-body", action="append", default=[], help="extract mod URLs from issue text")
    parser.add_argument("--comment-body", action="append", default=[], help="extract mod URLs from comment text")
    parser.add_argument("--horizon-version", help="installed Horizon tag or 'latest' (default: latest)")
    parser.add_argument("--profile", choices=["performance", "dev", "release"], default="performance")
    parser.add_argument("--minecraft-dir", help="Minecraft folder used to prepare the base version")
    parser.add_argument("--launcher-home", help="isolated Horizon launcher data folder")
    parser.add_argument("--game-home", help="isolated Horizon game folder")
    parser.add_argument("--dist", help="output folder (default: dist)")
    parser.add_argument("--include-resources", action="store_true", help="include prepared .local resources")
    parser.add_argument("--ignore-pins", action="store_true", help="build every mod on the base revision")
    parser.add_argument("--no-release", action="store_true", help="clone GitHub repos instead of using release .hnmod assets")
    parser.add_argument("--combine", action="store_true", help="compile all mods into one package (default when more than one mod is given)")
    parser.add_argument("--separate", action="store_true", help="build every mod as its own importable archive")
    parser.add_argument("--fail-fast", action="store_true", help="stop after the first mod that fails")
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.combine and args.separate:
        parser.error("--combine and --separate cannot be used together")

    global DIST
    if args.dist:
        DIST = Path(args.dist).resolve()
    DIST.mkdir(parents=True, exist_ok=True)
    logs = DIST / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)
    staging = WORK / "staging"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)

    if not LAUNCHER.is_file():
        say(f"error: {LAUNCHER} is missing")
        return 2
    LAUNCHER.chmod(LAUNCHER.stat().st_mode | 0o111)

    env, _, _ = launcher_env(args)

    sources: list[tuple[str, bool]] = [(source, not args.no_release) for source in args.sources]
    for text in args.issue_body + args.comment_body:
        for url in urls_from_text(text):
            sources.append((url, not args.no_release))
    if args.test_mods or not sources:
        if not sources:
            say("No mod source given; using the test mods from issue #1.")
        sources.extend(test_mod_sources())

    # Keep order but drop duplicates.
    seen: set[str] = set()
    sources = [item for item in sources if not (item[0] in seen or seen.add(item[0]))]

    jobs: list[Job] = []
    failures: list[str] = []
    for source, prefer_release in sources:
        try:
            found = resolve_source(source, staging, env, prefer_release=prefer_release)
            if not found:
                raise BuildError(f"{source}: no mod bundle found")
            jobs.extend(found)
        except (BuildError, OSError, zipfile.BadZipFile) as error:
            failures.append(f"{source}: {error}")
            say(f"error: {error}")

    if not jobs:
        summary = {"ok": False, "errors": failures, "jobs": []}
        (DIST / "manifest.json").write_text(json.dumps(summary, indent=2) + "\n")
        return 1

    try:
        base = ensure_horizon(args, env, logs)
        say(f"Using Horizon {base}")
        ensure_prepared(args, env, base, logs)
    except BuildError as error:
        say(f"error: {error}")
        failures.append(str(error))
        summary = {"ok": False, "errors": failures, "jobs": []}
        (DIST / "manifest.json").write_text(json.dumps(summary, indent=2) + "\n")
        return 1

    combine = not args.separate
    groups: list[tuple[str, Job, list[Job]]] = []
    if combine and len(jobs) > 1:
        combined = staging / "combined"
        combined.mkdir(parents=True, exist_ok=True)
        used: set[str] = set()
        for job in jobs:
            base_name = safe_name(job.mod_id or job.name)
            candidate = base_name
            counter = 2
            while candidate in used:
                candidate = f"{base_name}-{counter}"
                counter += 1
            used.add(candidate)
            shutil.copytree(job.bundle, combined / candidate, dirs_exist_ok=True)
        combined_job = Job("combined", combined, ", ".join(job.source for job in jobs))
        groups.append(("combined", combined_job, jobs))
        say(f"Combining {len(jobs)} mods into one importable package")
    else:
        groups = [(job.name, job, [job]) for job in jobs]

    results: list[dict] = []
    for name, build_target, source_jobs in groups:
        try:
            built, build_dir, _ = build_job(build_target, args, env, base, logs)
            metadata = json.loads((build_dir / "native-mods.json").read_text(encoding="utf-8"))
            mods = [
                {
                    "id": str(mod.get("id", "")),
                    "version": str(mod.get("version", "")),
                }
                for mod in metadata.get("mods", [])
            ]
            if combine and len(jobs) > 1:
                expected = {source_job.mod_id for source_job in source_jobs}
                actual = {mod["id"] for mod in mods if mod["id"]}
                missing = sorted(expected - actual)
                if missing:
                    left_out = metadata.get("left_out", [])
                    raise BuildError(
                        f"combined build is missing {', '.join(missing)}"
                        + (f" (left out: {left_out})" if left_out else "")
                    )
                ids = [mod["id"] for mod in mods if mod["id"]]
                build_target.mod_id = "+".join(ids) if ids else build_target.mod_id
                build_target.mod_version = "+".join(
                    mod["version"] for mod in mods if mod["version"]
                )
            hnmods: list[Path] = []
            used_hnmods: set[str] = set()
            for source_job in source_jobs:
                filename = (
                    f"{safe_name(source_job.mod_id)}-"
                    f"{safe_name(source_job.mod_version or 'build')}.hnmod"
                )
                candidate = filename
                counter = 2
                while candidate in used_hnmods:
                    stem = Path(filename).stem
                    candidate = f"{stem}-{counter}.hnmod"
                    counter += 1
                used_hnmods.add(candidate)
                hnmods.append(
                    write_hnmod(source_job, build_dir, DIST / "hnmod" / candidate)
                )
            archive = DIST / "builds" / f"{safe_name(build_target.mod_id)}-{built}.zip"
            archive_build(
                build_target,
                built,
                build_dir,
                archive,
                hnmods,
                metadata,
                args.include_resources,
            )
            hnmod_entries = [
                {
                    "path": str(hnmod.relative_to(DIST)),
                    "sha256": sha256(hnmod),
                }
                for hnmod in hnmods
            ]
            result = {
                "status": "built",
                "name": name,
                "mod_id": build_target.mod_id,
                "mod_version": build_target.mod_version,
                "mods": mods,
                "source": build_target.source,
                "horizon_base": metadata.get("base"),
                "horizon_revision": metadata.get("horizon"),
                "horizon_mixins": metadata.get("horizon_mixins"),
                "profile": metadata.get("profile"),
                "built_version": built,
                "hnmod": hnmod_entries[0]["path"] if len(hnmod_entries) == 1 else None,
                "hnmod_sha256": hnmod_entries[0]["sha256"] if len(hnmod_entries) == 1 else None,
                "hnmods": hnmod_entries,
                "artifact": str(archive.relative_to(DIST)),
                "artifact_bytes": archive.stat().st_size,
                "artifact_sha256": sha256(archive),
                "log": str((logs / f"{safe_name(name)}.log").relative_to(DIST)),
            }
            results.append(result)
            say(
                f"Built {build_target.mod_id} {build_target.mod_version}: {archive} "
                f"({archive.stat().st_size // (1024 * 1024)} MiB)"
            )
        except (BuildError, OSError, zipfile.BadZipFile, json.JSONDecodeError) as error:
            message = f"{name}: {error}"
            failures.append(message)
            say(f"error: {message}")
            results.append({"status": "failed", "name": name, "error": str(error)})
            if args.fail_fast:
                break

    summary = {
        "ok": not failures,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "horizon_version": base,
        "profile": args.profile,
        "errors": failures,
        "jobs": results,
    }
    (DIST / "manifest.json").write_text(json.dumps(summary, indent=2) + "\n")
    say(f"Wrote {DIST / 'manifest.json'}")
    return 0 if not failures else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
