# Issue #9 completion: AirJump native port and release

Date: 2026-11-15 (GitHub Actions runner)

Issue #9 asked to clone the Fabric AirJump mod, convert it to a Horizon
`.hnmod`, build it, and publish a release containing the mod and the build
output. The conversion source was recovered from the cancelled run in
`mods/airjump`; this run built, verified and released it.

## Source conversion

- Upstream: private Fabric repository `promikailamin/AirJump` (Minecraft 26.1.2,
  Fabric Loader 0.19.2, Java 25).
- Horizon bundle: `mods/airjump/horizon-mixin.toml`, `airjump.rs`, `runtime.rs`.
- Horizon pin: `9f42064c11efe7ef3e5ed2baad7ddc2a3b36eea0`.
- Hook: `horizon_client::game::native_hooks::Game<'_>::native_client_tick_post`
  at HEAD.
- Ported behaviour: AirJump, SuperLaunch, NoFall, explosion particles, launch
  sound, sneak guard, and `config/airjump.json` with the original keys.
- The Fabric/Mod Menu settings screen has no Horizon equivalent, so settings
  are edited through `config/airjump.json`.

## Build

```bash
HORIZON_BUILDER_SKIP_DEPS=1 ./build.sh mods/airjump \
  --profile dev --horizon-version nightly-2026-11-13-9f42064
```

Result: exit 0.

- Built version: `native-9f42064-a8abd820b571`
- Mod in `native-mods.json`: `airjump 0.0.1-26.1.2`
- `left_out`: empty
- Package: `dist/builds/airjump-native-9f42064-a8abd820b571.zip` (about 61 MiB)
- `.hnmod`: `dist/hnmod/airjump-0.0.1-26.1.2.hnmod`
- Package SHA-256: `f376a5404e317cef41ea2b00c32328a79ebfb07a380b7d675e9110697ac9bdeb`
- `.hnmod` SHA-256: `13842a75ac95ce33e2f717b4c59e0687d290ffe387cc4a7e49e5e76f42fc2e7c`

The package contains `BUILD-INFO.txt`, `INSTALL.txt`, the compiled
`horizon-client`, `native-mods.json`, and `mod-source/airjump-0.0.1-26.1.2.hnmod`.

## Import verification

```bash
.agent-work/tests/test_import_built.sh dist/builds/airjump-native-9f42064-a8abd820b571.zip
```

Result: exit 0.

```text
Imported imported-2026-11-15-748fde6 and selected it. It is prepared already, from another installed version.
Imported and smoke-tested: /home/runner/work/horizon_mod_builder/horizon_mod_builder/.work/launcher/versions/imported-2026-11-15-748fde6
```

The imported `horizon-client --help` also exited 0.

## Release

<https://github.com/promikailamin/horizon_mod_builder/releases/tag/airjump-v0.0.1-26.1.2>

Uploaded assets (download and SHA-256 verified):

- `airjump-0.0.1-26.1.2.hnmod` (3,499 bytes)
- `airjump-native-9f42064-a8abd820b571.zip` (63,509,616 bytes)

## Tests

```bash
python3 .agent-work/tests/test_build_mods.py
```

The suite includes `AirJumpBundleTests`, which checks the bundle metadata,
Horizon pin, hook target and `.hnmod` packing.

## Preserved files

- `issue9-manifest.json` — build manifest
- `issue9-sha256.txt` — artifact hashes
- `release-notes-airjump.md` — published release notes
- `../logs/issue9-build.log.gz` — full launcher/Cargo build log
- `../logs/issue9-import.log` — import and smoke-test log
- `../logs/issue9-release.log` — release creation and asset listing
