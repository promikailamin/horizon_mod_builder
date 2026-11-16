# Issue #12 verification: build the provided mods as one package

Date: 2026-11-16 (GitHub Actions runner, Ubuntu 26.04, glibc 2.43)

Issue #12 asked to run the build workflow with the attached `mods.zip` and produce one
importable package.

## Provided mods

`mods.zip` is preserved at `issue12-mods.zip` in this folder. It contains:

| Mod | Version | Pinned Horizon | Pinned horizon-mixins |
| --- | --- | --- | --- |
| `enchantmenthints` | 0.1.0 | `142388e` (2026-10-28) | `0d6b103` |
| `freecam_plus` | 1.1.0 | `9f42064` (2026-11-13) | `e59da90` |
| `mod_menu` | 0.3.5 | `fdc87ae` (2026-11-08) | `d9c83d7` |

## Why the default build could not include all three

The first GitHub Actions attempt used the newest Nightly (`nightly-2026-11-13-9f42064`).
`enchantmenthints` and `freecam_plus` compiled, but `mod_menu` 0.3.5 failed on that revision:

```text
error[E0609]: no field `options_to_game` on type `&mut game::Game<'_>`
```

`mod_menu` 0.3.5 was made for `fdc87ae`, where those fields still exist. The launcher's
`--allow-version-mismatch` builds a combined package on the newest pinned revision, and `--ignore-pins`
alone still could not compile `mod_menu` on the newest revision.

Building on `mod_menu`'s Nightly (`nightly-2026-11-08-fdc87ae`) with `--ignore-pins` forces all
three mods onto `fdc87ae`; all three then compile and are included.

## Code change

- `.github/workflows/build.yml` — new manual input `ignore_pins` (default `false`), passed to
  `scripts/build_mods.py --ignore-pins`.
- `README.md` — documents the input and when to use it.

## Local build and import

```bash
HORIZON_PORTABLE_SKIP_IMAGE=1 ./build.sh --portable \
  .agent-work/tmp/issue-12/mods.zip \
  --profile dev --horizon-version nightly-2026-11-08-fdc87ae --ignore-pins
```

Result: exit 0.

- Built version: `native-fdc87ae-cd0f3ccb6014`
- `native-mods.json`: `enchantmenthints 0.1.0`, `freecam_plus 1.1.0`, `mod_menu 0.3.5`;
  `left_out` is empty.
- Package: `dist/builds/enchantmenthints-freecam_plus-mod_menu-native-fdc87ae-cd0f3ccb6014.zip`
- The package was imported with `horizon-launcher import-build ... --trust-unsigned`; the
  imported `horizon-client --help` exited 0.
- `check_glibc.sh`: OK, every binary requires at most GLIBC 2.35.

Logs: `../logs/issue12-build-fdc87ae-ignore-pins.log`, `../logs/issue12-import.log`,
`../logs/issue12-glibc.log`.

## GitHub Actions build

<https://github.com/promikailamin/horizon_mod_builder/actions/runs/43800593165>

Result: success in 13m43s (`performance` profile, `combined` mode, `ignore_pins=true`).

- Artifact: `horizon-mod-build-30`
- Base Horizon: `nightly-2026-11-08-fdc87ae`
- Built version: `native-fdc87ae-54435fc46b4b`
- Horizon revision: `fdc87aecdbd116bf1e08adcd062fcbaea8c2e2ca`
- horizon-mixins: `e59da9094f0c2fdda6c627fe9eff22dec6a906f0`
- Package: `builds/enchantmenthints-freecam_plus-mod_menu-native-fdc87ae-54435fc46b4b.zip`
- Package SHA-256: `ca0155c4b3ab64f035c87fd6fdb3fdcb1b5bda21538c618b91210ae931c3d6d6`
- `native-mods.json` lists all three mods; `left_out` is empty; all three `.hnmod` sources are
  under `mod-source/`.

The downloaded CI artifact was checked with `.agent-work/tests/check_glibc.sh` (exit 0) and
imported with `.agent-work/tests/test_import_built.sh` (exit 0). The imported `horizon-client
--help` exited 0.

Logs: `../logs/issue12-ci-combined.log.gz`, `../logs/issue12-ci-glibc.log`,
`../logs/issue12-ci-import.log`, `../logs/issue12-ci-dispatch.log`; manifest:
`issue12-ci-manifest.json`; hashes: `issue12-ci-sha256.txt`.

## Install the CI package

```bash
horizon-launcher install nightly-2026-11-08-fdc87ae
horizon-launcher prepare --version nightly-2026-11-08-fdc87ae
horizon-launcher import-build <artifact>/builds/enchantmenthints-freecam_plus-mod_menu-native-fdc87ae-54435fc46b4b.zip \
  --version nightly-2026-11-08-fdc87ae --trust-unsigned
horizon-launcher play
```

`Imported ... and selected it. It is prepared already, from another installed version.` means the
import succeeded; it is not an error.

## Tests

```bash
python3 .agent-work/tests/test_build_mods.py
```

Result: 10 tests passed. Log: `../logs/issue12-tests.log`.
