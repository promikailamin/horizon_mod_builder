# Issue #11 verification: glibc-compatible builds and AirJump for 26.3

Date: 2026-11-15 (GitHub Actions runner, Ubuntu 26.04, glibc 2.43)

Issue #11 reported that imported builds crash on the user's machine with:

```text
/lib/x86_64-linux-gnu/libm.so.6: version 'GLIBC_2.43' not found
```

The old release was compiled directly on `ubuntu-latest` (Ubuntu 26.04,
glibc 2.43). The official Horizon Linux binaries target glibc 2.35, so the
release is now compiled in an Ubuntu 22.04/Jammy container with the same
baseline.

## Code changes

- `docker/portable-builder.Dockerfile` — Ubuntu 22.04 (glibc 2.35) compiler
  image with Java 25 and the native/X11/audio build dependencies.
- `scripts/build_mods.py` — new `--portable` mode. Preparation still runs on
  the host; only `horizon-launcher native-build` runs in Docker/Podman. Secret
  values are passed by variable name, never on the logged command line.
- `build.sh` — builds the portable image automatically for `--portable`.
- `.github/workflows/build.yml` — every Actions build now compiles with
  `--portable`, so published artifacts no longer require the runner's glibc.
- `mods/airjump/horizon-mixin.toml` — version `0.0.2-26.3`, targeting
  Minecraft 26.3 on the latest Horizon Nightly (`nightly-2026-11-13-9f42064`,
  revision `9f42064`).
- `.agent-work/tests/check_glibc.sh` — fails if a build requires a GLIBC
  symbol newer than 2.35.
- Tests updated for the new AirJump version and portable container command.

## Tests

```bash
python3 .agent-work/tests/test_build_mods.py
```

Result: 10 tests passed (`../logs/issue11-tests.log`).

## Build

```bash
HORIZON_BUILDER_SKIP_DEPS=1 ./build.sh --portable mods/airjump \
  --profile dev --horizon-version nightly-2026-11-13-9f42064
```

Result: exit 0, built in 8 min 8 s (dev, first build).

- Built version: `native-9f42064-7d0d9e4b6ceb`
- Mod in `native-mods.json`: `airjump 0.0.2-26.3`
- `.hnmod` native metadata: `game` 26.3, `horizon` 9f42064, `mixins` 5a64af9
- Package: `dist/builds/airjump-native-9f42064-7d0d9e4b6ceb.zip` (59 MiB)
- `.hnmod`: `dist/hnmod/airjump-0.0.2-26.3.hnmod`
- Package SHA-256: `a61f29cd32f8cb7ccd4abec9a3f97488474ef2a263ecdd184ef10a91f6209f02`
- `.hnmod` SHA-256: `4010803b48eaba30992896844c3094af8352365f484b7713a9bad4461e108d52`

Full log: `../logs/issue11-build.log.gz`; launcher log: `../logs/issue11-build.log.gz`
also contains the container command and cargo output.

## GLIBC verification

```bash
.agent-work/tests/check_glibc.sh dist/builds/airjump-native-9f42064-7d0d9e4b6ceb.zip
```

Result: exit 0.

```text
horizon-prepare          max GLIBC 2.34
horizon-server           max GLIBC 2.34
horizon-ctl              max GLIBC 2.34
horizon-client           max GLIBC 2.35
OK: every binary requires at most GLIBC 2.35
```

The previous release's `horizon-client` required `GLIBC_2.43`.

## Import and runtime verification

```bash
.agent-work/tests/test_import_built.sh dist/builds/airjump-native-9f42064-7d0d9e4b6ceb.zip
```

Result: exit 0.

```text
Imported imported-2026-11-15-f5d7fdb and selected it. It is prepared already, from another installed version.
Imported and smoke-tested: .../.work/launcher/versions/imported-2026-11-15-f5d7fdb
```

The imported `horizon-client --help` was also executed inside the glibc 2.35
container:

```text
ldd (Ubuntu GLIBC 2.35-0ubuntu3.15) 2.35
horizon-client --help exit 0 in glibc 2.35
GLIBC_2.35
```

Log: `../logs/issue11-glibc-run.log`.

## Release

<https://github.com/promikailamin/horizon_mod_builder/releases/tag/airjump-v0.0.2-26.3>

The previous broken `airjump-v0.0.1-26.1.2` release/tag was removed and the new
release was created from `main`. Uploaded assets were downloaded back and their
SHA-256 values matched the local build:

- `airjump-0.0.2-26.3.hnmod` — `4010803b48eaba30992896844c3094af8352365f484b7713a9bad4461e108d52`
- `airjump-native-9f42064-7d0d9e4b6ceb.zip` — `a61f29cd32f8cb7ccd4abec9a3f97488474ef2a263ecdd184ef10a91f6209f02`

Log: `../logs/issue11-release.log`.

## Preserved files

- `issue11-manifest.json` — build manifest
- `issue11-sha256.txt` — artifact hashes
- `release-notes-airjump-0.0.2-26.3.md` — release notes
- `../logs/issue11-build.log.gz` — full portable build
- `../logs/issue11-import.log` — import and smoke test
- `../logs/issue11-glibc-run.log` — runtime check inside glibc 2.35
- `../logs/issue11-tests.log` — unit tests
- `../logs/issue11-docker-build.log` — portable image build
- `../logs/issue11-release.log` — release replacement and asset verification
