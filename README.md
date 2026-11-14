# Horizon Mod Builder

A GitHub Actions-powered compiler for [Horizon](https://github.com/horizon-rust/horizon) native mods.

It uses the official **Horizon Launcher** as the compiler. The launcher is the same tool players use:
it resolves each mod's pinned Horizon commit, downloads the exact Horizon and
[horizon-mixins](https://github.com/horizon-rust/horizon-mixins) sources, applies the mixins, runs
Cargo, and installs the compiled game as `native-<commit>-<key>`. This repository wraps that into a
reproducible builder that also packs `.hnmod` sources and publishes downloadable GitHub Actions
artifacts.

## What it builds

For every mod it accepts:

- a **bundle folder** (`horizon-mixin.toml` or `horizon-native.json`)
- a **`.hnmod`** file, packed or unpacked
- a folder of bundles / `.hnmod` files
- a **git/GitHub URL** (a release `.hnmod` is preferred when one exists)
- issue text containing mod URLs, or the **test mods from issue #1**

and produces under `dist/`:

```
dist/
├── builds/<id>-<native-build>.zip   # compiled horizon-client + mod sources + BUILD-INFO.txt
├── hnmod/<id>-<version>.hnmod       # registry-schema source bundle
├── logs/<id>.log                    # full launcher/Cargo output
└── manifest.json                    # versions, hashes, artifact names, failures
```

The native-build archive excludes `.local/` (the prepared Minecraft resources, about 600 MB). It
contains the compiled `horizon-client`, `horizon-server`, `horizon-ctl`, `horizon-prepare`,
`native-mods.json`, the staged `mods/`, and the rest of the launcher's version folder. Install the
same base Horizon version with the launcher to play it (see
[Install and play on your computer](#install-and-play-on-your-computer)).

## Quick start

```bash
./build.sh                         # test mods from issue #1
./build.sh /path/to/mod            # a bundle or folder of bundles
./build.sh /path/to/mod.hnmod      # a packed .hnmod
./build.sh https://github.com/user/repo
./build.sh --issue-body "$(cat issue.txt)"
```

Useful options:

```bash
./build.sh --profile dev            # fastest rebuilds; slower game
./build.sh --profile release        # smallest/fastest game; slowest build
./build.sh --horizon-version latest # release or Nightly tag (default: latest)
./build.sh --no-release             # clone GitHub repos instead of release .hnmod assets
./build.sh --combine                # compile all mods into one game build
./build.sh --include-resources      # include .local/ resources in the archive
```

The builder installs its own Rust toolchain, Horizon sources, Cargo cache, and game files inside
`.work/` (or `HORIZON_LAUNCHER_HOME`). No system Rust is used. Native compile dependencies are
installed through `apt` on first use: `build-essential`, `pkg-config`, `libasound2-dev`,
`libudev-dev`, plus the launcher's X11 libraries.

## Install and play on your computer

Every Actions run publishes artifacts under **Actions → the run → Artifacts**:

- `dist/builds/<mod>-<native-build>.zip` — the compiled game and mod sources
- `dist/hnmod/<mod>-<version>.hnmod` — the packed source bundle
- `dist/manifest.json` — build versions, hashes, and archive names

Download `horizon-mod-build-<run-number>.zip` and extract it first.

The builder runs on `ubuntu-latest`, so prebuilt archives are **Linux x86_64 games**. Use them on
Linux; on Windows or macOS, build locally with the launcher (option 2).

### Option 1: Use a prebuilt archive (Linux)

1. Extract `builds/<mod>-<native-build>.zip`. Its `BUILD-INFO.txt` names the **Base Horizon**
   version, for example `v2026.10.13`.
2. Install and prepare that base version (preparation needs your own Minecraft install):

   ```bash
   horizon-launcher install <base-tag>
   horizon-launcher prepare --version <base-tag>
   ```

3. Import the build. Pass the extracted zip (it contains `horizon-client`), and mark the unsigned
   Actions build as trusted:

   ```bash
   horizon-launcher import-build path/to/<mod>-<native-build>.zip \
     --version <base-tag> --trust-unsigned
   ```

   The build is added as its own version on the base's game files and selected.
4. Play it:

   ```bash
   horizon-launcher play
   ```

   You can also do steps 2–4 from the launcher window: install the base version on the Versions
   page, prepare it, then import the zip/drop it on the window and press Play.

If you built with `--combine`, one archive holds all the mods. Otherwise each archive holds one mod,
and each may be built on a different Horizon commit — import them separately if you want to play
them that way.

### Option 2: Add the mod and build it locally (any OS)

This is the recommended route on Windows and macOS, and it lets the launcher compile the mod for
your own platform.

1. Install a Horizon version and prepare it:

   ```bash
   horizon-launcher install latest
   horizon-launcher prepare
   ```

2. Install the mod into your instance:

   ```bash
   # From a GitHub repository (the latest release .hnmod, or its default branch)
   horizon-launcher mods add-github https://github.com/OWNER/REPO --trust-native-code

   # From Horizon's registry, by project id or slug
   horizon-launcher mods install MOD_ID --source horizon
   ```

   For a downloaded `.hnmod`, open the launcher's **Mods** page with your instance selected and add
   the `.hnmod` there (or drop it on the launcher window).

3. Build the game with the mod and play:

   ```bash
   horizon-launcher native-build --trust-native-code
   horizon-launcher play
   ```

   The first native build downloads Rust and takes roughly 20–30 minutes; later builds are
   incremental. You can do the same from the **Mods** page with **Build** and then **Play**.

> `.hnmod` is a **source bundle**, not a compiled game. There is no copy into a vanilla `mods/`
> folder: the launcher installs it, and `native-build` compiles it into the game. Native mods are
> not sandboxed, so only install sources you trust.

## GitHub Actions

`workflow_dispatch` inputs:

- `mod_source`: folder, `.hnmod` URL, git/GitHub URL, or `test` (blank uses test mods)
- `horizon_version`: tag or `latest`
- `native_profile`: `performance` (default), `dev`, or `release`

The workflow also runs when:

- an issue is opened/reopened with the **`build-mod`** label, or receives that label later;
- an issue comment contains **`/build`**, optionally with URLs.

Artifacts are uploaded as `horizon-mod-build-<run-number>`. The Actions run summary lists every
built mod, its Horizon revision, `.hnmod` SHA-256, and downloadable archive.

## Test mods (issue #1)

`configs/test-mods.json` points at the two mods from issue #1:

| Mod | Source | Form |
| --- | --- | --- |
| Enchantment Hints | `d3grando/enchantmenthints` | source bundle |
| Mod Menu | `tariksabanuz/ModMenuHorizon` | release `.hnmod` (`mod_menu-0.3.5.hnmod`) |

`./build.sh --test-mods` (or just `./build.sh`) builds both. They pin different Horizon commits, so
they are compiled as independent games by default. The builder has been run locally against both:

- `enchantmenthints` → `native-9f42064-0bde960edb43`
- `mod_menu` → `native-fdc87ae-2fcdb6a9e930`

## How compilation works

1. **Base version** — install a Horizon release/Nightly and prepare its resources from
   `configs/minecraft/.minecraft` (the checked-in client jar and libraries; no Microsoft account is
   needed).
2. **Resolve the mod** — a source bundle is staged; a `.hnmod` is safely extracted; a GitHub repo
   uses its latest release `.hnmod` or is cloned.
3. **Compile** — `horizon_launcher native-build FOLDER --version BASE --trust-native-code
   --allow-version-mismatch`. The launcher downloads the mod's pinned Horizon commit, applies
   Horizon's mixins, builds the game, and records the result in `native-mods.json`.
4. **Validate** — the builder checks that the new `native-*` version exists, contains the expected
   mod id, has a compiled `horizon-client`, and that the packed `.hnmod` has the registry layout
   (`horizon-native.json` + `mixins/<id>/horizon-mixin.toml`).
5. **Publish** — archives, `.hnmod` files, logs, and `manifest.json` go to `dist/`.

## Repository layout

```
horizon_mod_builder/
├── horizon_launcher              # official Horizon Launcher (the compiler)
├── scripts/build_mods.py         # source resolution, compile, package, manifest
├── build.sh                      # dependency setup + builder entry point
├── configs/test-mods.json        # issue #1 test mods
├── configs/minecraft/.minecraft/ # Minecraft 26.3 client jar + libraries for prepare
├── .github/workflows/build.yml   # Actions build, summary, artifact upload
└── rust/horizon-prepare/         # legacy Horizon prepare source copy (not used by the builder)
```

## Security

Native mods are not sandboxed: they compile into the game and run with the runner's rights. The
builder passes `--trust-native-code` only because this is an explicit compile workflow for mods you
choose to build. Review sources before building. No tokens or Minecraft credentials are written to
the repository or logs. `.hnmod` and build outputs are gitignored and only uploaded as Actions
artifacts.
