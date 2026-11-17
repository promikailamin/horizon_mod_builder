# Horizon Mods 0.0.1 for 26.3

A combined Horizon native build containing all five mods from issue #13, built
for Minecraft 26.3 and Horizon Nightly 2026-11-13 (`9f42064`).

## Included mods

| Mod | Version | Notes |
| --- | --- | --- |
| AirJump | 0.0.2-26.3 | AirJump, SuperLaunch and NoFall |
| Enchantment Hints | 0.1.0 | Tooltip enchantment hints |
| Freecam Plus | 1.1.0 | Free camera |
| Horizonmatica | 0.3.3 | **Converted to `9f42064`** (upstream 0.3.3; 0.3.2 used the removed `Game::options_to_game`) |
| Mod Menu | 0.3.6 | **Converted to `9f42064`**; same removed field no longer touched |

## Build

- Built version: `native-9f42064-cd75e4726776`
- Base Horizon: `nightly-2026-11-13-9f42064`
- Horizon revision: `9f42064c11efe7ef3e5ed2baad7ddc2a3b36eea0`
- horizon-mixins: `e59da9094f0c2fdda6c627fe9eff22dec6a906f0`
- Profile: `performance`
- Platform: Linux x86_64, compiled against glibc 2.35 (Ubuntu 22.04/24.04,
  Debian 12 and newer glibc distributions)
- `native-mods.json` lists all five mods; `left_out` is empty.

The package was imported with `horizon-launcher import-build ... --trust-unsigned`
and its `horizon-client --help` exited 0. Every binary requires at most
GLIBC 2.35. The same build also succeeded in GitHub Actions
([run #33](https://github.com/promikailamin/horizon_mod_builder/actions/runs/44020142440),
artifact `horizon-mod-build-33`).

## Install

1. Download and extract
   `airjump-enchantmenthints-freecam_plus-horizonmatica-mod_menu-native-9f42064-cd75e4726776.zip`.
2. Install and prepare the base Horizon version once:

   ```bash
   horizon-launcher install nightly-2026-11-13-9f42064
   horizon-launcher prepare --version nightly-2026-11-13-9f42064
   ```

3. Import the package and trust the unsigned Actions build:

   ```bash
   horizon-launcher import-build airjump-enchantmenthints-freecam_plus-horizonmatica-mod_menu-native-9f42064-cd75e4726776.zip \
     --version nightly-2026-11-13-9f42064 --trust-unsigned
   ```

   `Imported ... and selected it. It is prepared already, from another installed
   version.` means the import succeeded; it is not an error.

4. Play with `horizon-launcher play`.

The `.hnmod` files are the corresponding source bundles for the launcher's Mods
page or for rebuilding. `.hnmod` is a source bundle, not a compiled game.

## SHA-256

See `SHA256SUMS`.
