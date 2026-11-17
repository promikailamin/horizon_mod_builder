# Issue #13 verification: build the five provided mods on the latest Horizon

Date: 2026-11-17 (GitHub Actions runner, Ubuntu, glibc 2.43 host; game compiled
against glibc 2.35 in the portable container)

Issue #13 attached `mods.zip` and asked to build the provided mods, converting
Horizonmatica, which is not for the latest Horizon version, and to create a release.

## Provided mods

The input archive is preserved as `issue13-mods.zip` (SHA-256
`edf82e732a9065a7310d4b66687434712f8c9b82f5c936b24a6c768733379975`). It holds:

| Mod | Version | Pinned Horizon |
| --- | --- | --- |
| `airjump` | 0.0.2-26.3 | `9f42064` (latest) |
| `enchantmenthints` | 0.1.0 | `142388e` |
| `freecam_plus` | 1.1.0 | `9f42064` (latest) |
| `horizonmatica` | 0.3.2 | `fdc87ae` |
| `mod_menu` | 0.3.5 | `fdc87ae` |

## Conversions for Horizon 9f42064

### Horizonmatica 0.3.2 -> 0.3.3

Horizon removed `Game::options_to_game` between `fdc87ae` and `9f42064`.
Horizonmatica 0.3.2 set it when opening the mod's page, so it cannot build on the
latest Nightly.

The upstream maintainer released **0.3.3** as exactly this conversion
(<https://github.com/keksi2k/horizonmatica/releases/tag/v0.3.3>). It drops that
field, pins `horizon = 9f42064c11efe7ef3e5ed2baad7ddc2a3b36eea0`, and makes `Esc`
on the fallback Options > Mods page return to the pause menu. The release
`.hnmod` (SHA-256 `b689878c7cddbb021e914d5094233e49352ba4f0676cf30cca3c45873074fbdc`)
is vendored as source in [`mods/horizonmatica`](../../mods/horizonmatica).

### Mod Menu 0.3.5 -> 0.3.6

`mod_menu 0.3.5` also used `Game::options_to_game`, so a combined build on the
latest Nightly failed with:

```text
error[E0609]: no field `options_to_game` on type `&mut game::Game<'_>`
```

`mods/mod_menu/mixins/mod_menu/ui.rs` now reads only `options_from_title` before
opening the settings page:

```rust
let from_title = game.options_from_title;
game.open_options_at(from_title, Page::NativeMod(index));
```

The bundle version was bumped to `0.3.6` and pins Horizon `9f42064`. Its
`horizon-mixin.toml`, `horizon-native.json` and runtime `VERSION` agree.

The combined build input with all five ready bundles is preserved in
`.agent-work/outputs/issue13-converted-mods.zip` (SHA-256
`fcb283f9a6ef6097113c97d6bfce85bd64b50f3759f91470ca1b0b51b9dedf42`).

## Build

```bash
./build.sh --portable .agent-work/outputs/issue13-converted-mods.zip \
  --horizon-version nightly-2026-11-13-9f42064 --ignore-pins \
  --profile performance
```

`--ignore-pins` pins every mod to the same base revision `9f42064`, which the
two converted mods now target and the other three compile on.

Result: exit 0 in 5 min 29 s (incremental performance build).

- Base Horizon: `nightly-2026-11-13-9f42064`
- Horizon revision: `9f42064c11efe7ef3e5ed2baad7ddc2a3b36eea0`
- horizon-mixins: `e59da9094f0c2fdda6c627fe9eff22dec6a906f0`
- Built version: `native-9f42064-cd75e4726776`
- Package:
  `builds/airjump-enchantmenthints-freecam_plus-horizonmatica-mod_menu-native-9f42064-cd75e4726776.zip`
- Package SHA-256: `816417c20d28479700700133c69776cd7dcafdc1b7cf758f3b541c03e6b0ae23`
- Size: 54,454,535 bytes (51 MiB)
- `native-mods.json` lists all five mods and `left_out` is empty.

Source bundles produced under `hnmod/`:

| Bundle | SHA-256 |
| --- | --- |
| `airjump-0.0.2-26.3.hnmod` | `4010803b48eaba30992896844c3094af8352365f484b7713a9bad4461e108d52` |
| `enchantmenthints-0.1.0.hnmod` | `6f1b80a7c22e02b086d5eea2ed6f7c5481b3e40d6a974bf9e382a3df4a2de9df` |
| `freecam_plus-1.1.0.hnmod` | `07deac7e39768a1750a0e42b377ed79561ee1dce4d4fac7bdd542c2da5c7e7c3` |
| `horizonmatica-0.3.3.hnmod` | `c67fe23b3f906885b9d123d1feb16073d06ef0677ec8070af457bc16a32c8ac8` |
| `mod_menu-0.3.6.hnmod` | `bc357e1cb142cbde905e76e7eadea44b18cb3615012abd3ffffd21421f9678be` |

## Verification

- `.agent-work/tests/check_glibc.sh <package>`: OK. `horizon-client` needs at
  most GLIBC 2.35; the other binaries need 2.34.
- `.agent-work/tests/test_import_built.sh <package>`: OK.
  `imported-2026-11-17-d9a2497` was imported with
  `horizon-launcher import-build ... --trust-unsigned`, selected, and its
  `horizon-client --help` exited 0.
- `python3 .agent-work/tests/test_build_mods.py`: 10 tests passed.

Logs: `../logs/issue13-combined-build.log`, `../logs/issue13-modmenu-build.log.gz`,
`../logs/issue13-glibc.log`, `../logs/issue13-import.log`;
manifest: `issue13-manifest.json`; hashes: `issue13-sha256.txt`.

## GitHub Actions verification

The same input archive was built by the **Build Horizon Mod** workflow with
`mod_source=.agent-work/outputs/issue13-converted-mods.zip`,
`horizon_version=nightly-2026-11-13-9f42064`, `native_profile=performance`,
`mode=combined` and `ignore_pins=true`:

<https://github.com/promikailamin/horizon_mod_builder/actions/runs/44020142440>

Result: success in 10m59s. Artifact `horizon-mod-build-33`:

- Built version: `native-9f42064-cd75e4726776` (same build)
- Package SHA-256: `a14e607ccc01554dbd726dc20d8a061b3f3c3286bdaee7702a7dc3744b69bc7f`
  (the zip hash differs from the local run because the launcher writes the build
  time; the built version and mod contents are the same)
- All five mods and `.hnmod` sources are present; `left_out` is empty.
- The downloaded CI package passed `check_glibc.sh` and
  `test_import_built.sh` (`imported-2026-11-17-81cd511`).

CI logs: `../logs/issue13-ci-glibc.log`, `../logs/issue13-ci-import.log`,
`../logs/issue13-ci-dispatch.log`; manifest: `issue13-ci-manifest.json`;
hashes: `issue13-ci-sha256.txt`.

## Release

<https://github.com/promikailamin/horizon_mod_builder/releases/tag/mods-v0.0.1-26.3>

Assets: the combined package, the five `.hnmod` source bundles, `SHA256SUMS` and
`manifest.json`.

## Install the release package

```bash
horizon-launcher install nightly-2026-11-13-9f42064
horizon-launcher prepare --version nightly-2026-11-13-9f42064
horizon-launcher import-build <release>/airjump-enchantmenthints-freecam_plus-horizonmatica-mod_menu-native-9f42064-cd75e4726776.zip \
  --version nightly-2026-11-13-9f42064 --trust-unsigned
horizon-launcher play
```

`Imported ... and selected it. It is prepared already, from another installed
version.` means the import succeeded; it is not an error.
