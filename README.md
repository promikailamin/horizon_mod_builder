# Horizon Mod Builder

Compile [Horizon](https://github.com/horizon-rust/horizon) native mods on GitHub Actions (or
locally) and download **one importable game package** containing all the mods you selected.

The builder uses the official **Horizon Launcher** as the compiler. The launcher resolves each
mod's pinned Horizon commit, downloads the exact Horizon and
[horizon-mixins](https://github.com/horizon-rust/horizon-mixins) sources, applies the mixins, runs
Cargo, and installs the result as `native-<commit>-<key>`. This repository wraps that into a
reproducible builder, packs the result as a zip, and uploads it as a GitHub Actions artifact.

## What it builds

For every mod it accepts:

- a **bundle folder** (`horizon-mixin.toml` or `horizon-native.json`)
- a **`.hnmod`** file, packed or unpacked
- a folder of bundles / `.hnmod` files, or a zip of them
- a **git/GitHub URL** (a release `.hnmod` is preferred when one exists)
- issue text containing mod URLs, or the **test mods from issue #1**

If you give it **more than one mod, it compiles them together into one package by default**
(`--combine`). That package is a single zip you import once with `import-build`; all mods are in
that one game. Use `--separate` if you explicitly want one package per mod.

Output under `dist/`:

```
dist/
├── builds/<mods>-<native-build>.zip   # compiled game + BUILD-INFO.txt + INSTALL.txt + mod sources
├── hnmod/<id>-<version>.hnmod         # packed source bundle(s)
├── logs/<id>.log                      # full launcher/Cargo output
└── manifest.json                      # versions, hashes, artifact names, failures
```

The game archive excludes `.local/` (the prepared Minecraft resources, about 600 MB). It contains
the compiled `horizon-client`, `horizon-server`, `horizon-ctl`, `horizon-prepare`,
`native-mods.json`, and the rest of the launcher's version folder. Install the same base Horizon
version with the launcher to play it.

## Quick start (local)

```bash
./build.sh                              # test mods from issue #1
./build.sh /path/to/mod                 # one bundle or a folder of bundles
./build.sh /path/to/mod.hnmod           # a packed .hnmod
./build.sh /path/to/mods.zip            # a zip of mods
./build.sh https://github.com/user/repo
./build.sh --issue-body "$(cat issue.txt)"

./build.sh mod-a/ mod-b/ mod-c.hnmod    # all three in ONE package (default)
./build.sh --separate mod-a/ mod-b/     # one package per mod instead
```

Useful options:

```bash
./build.sh --profile dev            # fastest rebuilds; slower game
./build.sh --profile release        # smallest/fastest game; slowest build
./build.sh --horizon-version latest # release or Nightly tag (default: latest)
./build.sh --no-release             # clone GitHub repos instead of release .hnmod assets
./build.sh --ignore-pins            # build every mod on the base revision
./build.sh --include-resources      # include .local/ resources in the archive
./build.sh --portable mods/airjump  # compile in the glibc 2.35 container (releases)
```

The builder installs its own Rust toolchain, Horizon sources, Cargo cache, and game files inside
`.work/` (or `HORIZON_LAUNCHER_HOME`). No system Rust is used. Native compile dependencies are
installed through `apt` on first use: `build-essential`, `pkg-config`, `libasound2-dev`,
`libudev-dev`, plus the launcher's X11 libraries.

### Portable builds and glibc

A binary compiled on `ubuntu-latest` is tied to that runner's glibc. In November 2026 the runner is
Ubuntu 26.04 with glibc 2.43, so those builds fail on Ubuntu 24.04/22.04 and Debian 12 with errors
like `version 'GLIBC_2.43' not found` in `libm.so.6`.

`--portable` compiles the game in the `docker/portable-builder.Dockerfile` image
(`eclipse-temurin:25-jdk-jammy`, glibc 2.35), which matches the official Horizon Linux binaries.
The GitHub Actions workflow always uses it, so release packages run on Ubuntu 22.04+, Ubuntu 24.04
and Debian 12. Preparation still runs on the host; only `horizon-launcher native-build` is
containerized. Docker or Podman is required for `--portable`.

## Install a built package on your computer

Prebuilt Actions packages are **Linux x86_64 games** compiled against glibc 2.35, so they run on
Ubuntu 22.04/24.04, Debian 12, and newer glibc distributions. They do not require the runner's
glibc 2.43. On Windows, macOS, or an older distribution, build locally instead
(see [Build locally](#build-locally-any-os)).

1. Download the workflow artifact `horizon-mod-build-<run-number>` and extract it.
2. Find the build zip under `builds/`. Its `BUILD-INFO.txt` and `INSTALL.txt` name the **Base
   Horizon** version, for example `nightly-2026-11-13-9f42064`.
3. Install and prepare that base version once (preparation uses your own Minecraft install):

   ```bash
   horizon-launcher install nightly-2026-11-13-9f42064
   horizon-launcher prepare --version nightly-2026-11-13-9f42064
   ```

4. Import the built zip and trust the unsigned Actions build:

   ```bash
   horizon-launcher import-build path/to/<mods>-<native-build>.zip --trust-unsigned
   ```

   Or pass the base explicitly:

   ```bash
   horizon-launcher import-build path/to/<mods>-<native-build>.zip \
     --version nightly-2026-11-13-9f42064 --trust-unsigned
   ```

5. Play:

   ```bash
   horizon-launcher play
   ```

The launcher prints something like:

```text
Imported imported-2026-11-15-354dfdb and selected it. It is prepared already, from another installed version.
```

**That is success, not an error.** The import worked and reuses the prepared base game files.
`Imported ... and selected it` means the package is now the selected version. You can confirm with
`horizon-launcher versions --installed`.

You can also use the launcher window: install and prepare the base version on the **Versions**
page, then drop the build zip on the window (or import it from the Versions page) and press
**Play**.

If you built with `--separate`, each zip is a different game and is imported separately. If you
used the default combined mode, one zip contains every mod.

### Verify the package without importing

```bash
unzip -p builds/<mods>-<native-build>.zip BUILD-INFO.txt
unzip -l builds/<mods>-<native-build>.zip | grep -E 'horizon-client$|native-mods.json|mod-source/'
```

## Upload local mods and build on GitHub Actions

`upload.sh` packs mods from your computer, uploads them as a temporary GitHub release asset, and
starts the **Build Horizon Mod** workflow. This is the easiest way to build a collection of local
mods without committing them to the repository.

Requirements: `bash`, `python3`, `git`, and the [GitHub CLI](https://cli.github.com) logged in with
`gh auth login`.

```bash
./upload.sh                                  # HORIZON_MODS_DIR, ~/horizon-mods, or current folder
./upload.sh ~/Downloads/mod-menu.hnmod
./upload.sh ~/my-mods mod_menu.hnmod         # all built into one package by default
./upload.sh --separate ~/my-mods             # one package per mod
./upload.sh --profile dev --watch ~/my-mods  # wait for the run and show the result
./upload.sh --dry-run ~/my-mods              # package only; print the commands without uploading
./upload.sh --repo OWNER/REPO ~/my-mods      # override the detected repository
```

Options: `--horizon-version TAG`, `--profile performance|dev|release`,
`--mode combined|separate`, `--watch`, `--cleanup` (delete the temporary release after watching),
`--keep-upload`, `--dry-run`, `--repo OWNER/REPO`.

When the run finishes, download `horizon-mod-build-<run-number>` from **Actions → the run →
Artifacts**, then use the import steps above. Temporary upload releases are visible on the public
repository, so do not upload private mod sources.

## GitHub Actions

Manual `workflow_dispatch` inputs:

- `mod_source`: folder, `.hnmod` URL, zip URL, git/GitHub URL, or `test` (blank uses test mods)
- `horizon_version`: tag or `latest`
- `native_profile`: `performance` (default), `dev`, or `release`
- `mode`: `combined` (default, one package) or `separate` (one package per mod)
- `ignore_pins`: build every mod on `horizon_version` even when it pins another Horizon commit
  (default `false`)

The launcher normally builds a combined package on the newest Horizon commit pinned by its mods.
If an older mod does not compile there, set `horizon_version` to the matching Nightly and turn on
`ignore_pins`, which forces all mods onto that version's commit.

The workflow also runs when:

- an issue is opened/reopened with the **`build-mod`** label, or receives that label later;
- an issue comment contains **`/build`**, optionally with URLs.

Artifacts are uploaded as `horizon-mod-build-<run-number>`. The Actions run summary lists every
built mod, its Horizon revision, `.hnmod` SHA-256, the import command, and the downloadable
archive. The workflow passes its GitHub token to the launcher as `HORIZON_GITHUB_TOKEN` so resolving
Horizon/horizon-mixins revisions uses authenticated GitHub API requests instead of the shared
anonymous rate limit.

## Test mods (issue #1)

`configs/test-mods.json` points at the two mods from issue #1:

| Mod | Source | Form |
| --- | --- | --- |
| Enchantment Hints | `d3grando/enchantmenthints` | source bundle |
| Mod Menu | `tariksabanuz/ModMenuHorizon` | release `.hnmod` (`mod_menu-0.3.5.hnmod`) |

`./build.sh` (or `./build.sh --test-mods`) builds both. They pin different Horizon commits, so the
combined build is made on the newest pinned revision (`fdc87ae`) with both mods included.

Last verified build (combined, dev profile, base `nightly-2026-11-13-9f42064`):

- `enchantmenthints` + `mod_menu` → `native-fdc87ae-a9845d89dc7b`
- Verified locally and in GitHub Actions
  ([run #17](https://github.com/promikailamin/horizon_mod_builder/actions/runs/43683190389),
  artifact `horizon-mod-build-17`). Both packages were imported with
  `horizon-launcher import-build ... --trust-unsigned` and selected successfully; the imported
  `horizon-client --help` starts and exits 0.
- The combined package lists both mods in `native-mods.json` and contains both `.hnmod` sources
  under `mod-source/`.

## Provided mods from issue #12

`mods.zip` from issue #12 holds `enchantmenthints 0.1.0`, `freecam_plus 1.1.0` and
`mod_menu 0.3.5`. `mod_menu 0.3.5` targets `fdc87ae` and does not compile on `9f42064` (it uses
the removed `options_to_game` field), so the three mods are built together on
`nightly-2026-11-08-fdc87ae` with `ignore_pins`:

```bash
./build.sh --portable mods.zip \
  --horizon-version nightly-2026-11-08-fdc87ae --ignore-pins
```

Last verified build (combined, performance profile, artifact `horizon-mod-build-30`):
`native-fdc87ae-54435fc46b4b`, containing all three mods with nothing left out. The package was
imported and smoke-tested, and every binary requires at most GLIBC 2.35. Full details are in
`.agent-work/outputs/issue12-verification.md`.

## AirJump native port (issue #9)

[`mods/airjump`](mods/airjump) is the Horizon native port of the Fabric AirJump mod
(`promikailamin/AirJump`). It provides AirJump, SuperLaunch and NoFall, with settings in
`config/airjump.json`.

```bash
./build.sh --portable mods/airjump --profile dev --horizon-version nightly-2026-11-13-9f42064
.agent-work/tests/test_import_built.sh dist/builds/airjump-native-*.zip
```

The finished release is
[AirJump 0.0.2-26.3](https://github.com/promikailamin/horizon_mod_builder/releases/tag/airjump-v0.0.2-26.3).
It targets Minecraft 26.3 and the latest Horizon Nightly (`nightly-2026-11-13-9f42064`), and
contains the `airjump-0.0.2-26.3.hnmod` source bundle plus a precompiled Linux x86_64 package built
against glibc 2.35. See [`mods/airjump/README.md`](mods/airjump/README.md) for the conversion notes
and install commands.

## Build locally (any OS)

This is the recommended route on Windows and macOS, and it lets the launcher compile the mod for
your own platform.

1. Install a Horizon version and prepare it:

   ```bash
   horizon-launcher install latest
   horizon-launcher prepare
   ```

2. Install the mod(s) into your instance:

   ```bash
   # From a GitHub repository (the latest release .hnmod, or its default branch)
   horizon-launcher mods add-github https://github.com/OWNER/REPO --trust-native-code

   # From Horizon's registry, by project id or slug
   horizon-launcher mods install MOD_ID --source horizon
   ```

   For downloaded `.hnmod` files, open the launcher's **Mods** page with your instance selected and
   add them there (or drop them on the launcher window).

3. Build the game with the mods and play:

   ```bash
   horizon-launcher native-build --trust-native-code
   horizon-launcher play
   ```

   The first native build downloads Rust and takes roughly 20–30 minutes; later builds are
   incremental. You can do the same from the **Mods** page with **Build** and then **Play**.

> `.hnmod` is a **source bundle**, not a compiled game. There is no copy into a vanilla `mods/`
> folder: the launcher installs it, and `native-build` compiles it into the game. Native mods are
> not sandboxed, so only install sources you trust.

## How compilation works

1. **Base version** — install a Horizon release/Nightly and prepare its resources from
   `configs/minecraft/.minecraft` (the checked-in client jar and libraries; no Microsoft account is
   needed).
2. **Resolve the mods** — source bundles are staged, `.hnmod` files and zips are safely extracted,
   and a GitHub repo uses its latest release `.hnmod` or is cloned.
3. **Combine** — with more than one mod, the builder gathers every bundle into one folder.
4. **Compile** — `horizon_launcher native-build FOLDER --version BASE --trust-native-code
   --allow-version-mismatch`. The launcher downloads the mods' pinned Horizon commit, applies
   Horizon's mixins, builds the game, and records the result in `native-mods.json`.
5. **Validate** — the builder checks that the new `native-*` version exists, contains the expected
   mod ids, has a compiled `horizon-client`, and that every packed `.hnmod` has the registry layout
   (`horizon-native.json` + `mixins/<id>/horizon-mixin.toml`).
6. **Publish** — archives, `.hnmod` files, logs, and `manifest.json` go to `dist/`.

## Repository layout

```
horizon_mod_builder/
├── horizon_launcher                  # official Horizon Launcher (the compiler)
├── scripts/build_mods.py             # source resolution, compile, package, manifest
├── scripts/pack_mods_zip.py          # packs local mods for upload.sh
├── docker/portable-builder.Dockerfile # glibc 2.35 compiler image for releases
├── build.sh                          # dependency setup + builder entry point
├── upload.sh                         # upload local mods and dispatch the workflow
├── configs/test-mods.json            # issue #1 test mods
├── mods/airjump/                     # Horizon native port of the Fabric AirJump mod
├── configs/minecraft/.minecraft/     # Minecraft 26.3 client jar + libraries for prepare
├── .github/workflows/build.yml       # Actions build, summary, artifact upload
└── rust/horizon-prepare/             # legacy Horizon prepare source copy (not used by the builder)
```

## Security

Native mods are not sandboxed: they compile into the game and run with the runner's rights. The
builder passes `--trust-native-code` only because this is an explicit compile workflow for mods you
choose to build. Review sources before building. No tokens or Minecraft credentials are written to
the repository or logs. `.hnmod` and build outputs are gitignored and only uploaded as Actions
artifacts.
