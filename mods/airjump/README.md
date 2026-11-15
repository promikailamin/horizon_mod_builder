# AirJump for Horizon

Horizon native port of the Fabric mod
[`promikailamin/AirJump`](https://github.com/promikailamin/AirJump). The original
mod is client-side only; this bundle hooks the same client tick and keeps the
same features and settings.

## Files

| File | Purpose |
| --- | --- |
| `horizon-mixin.toml` | Horizon bundle manifest. Pins Horizon `9f42064` and hooks `native_client_tick_post` at HEAD. |
| `airjump.rs` | Hook helper called by the game tick. |
| `runtime.rs` | Native Rust implementation of AirJump, SuperLaunch, NoFall and the JSON config. |

## Features

- **AirJump** — pressing jump again while airborne performs a jump.
- **SuperLaunch** — right-clicking with the configured launch item while
  looking at no block or mob launches the player along the view direction.
  Holding sneak while trying refuses the launch with a chat message.
- **NoFall** — sends the server a no-fall movement status while falling.
- **Config** — `config/airjump.json` in the game folder:

```json
{
  "multi_jump": true,
  "launch": true,
  "no_fall_damage": true,
  "launchWand": "minecraft:stick",
  "launchVelocity": 5.0
}
```

Horizon native mods do not load Fabric or Mod Menu entry points, so the
original Mod Menu settings screen is not included. Edit the JSON file instead;
missing or invalid values fall back to the defaults above.

## Build

```bash
./build.sh mods/airjump --profile dev --horizon-version nightly-2026-11-13-9f42064
.agent-work/tests/test_import_built.sh dist/builds/airjump-native-*.zip
```

Last verified build:

- Base Horizon: `nightly-2026-11-13-9f42064`
- Horizon revision: `9f42064c11efe7ef3e5ed2baad7ddc2a3b36eea0`
- horizon-mixins: `5a64af938ec86b00d53d16a408aabc0038fb3e57`
- Built version: `native-9f42064-a8abd820b571`
- Release: <https://github.com/promikailamin/horizon_mod_builder/releases/tag/airjump-v0.0.1-26.1.2>

## Install the release

```bash
horizon-launcher install nightly-2026-11-13-9f42064
horizon-launcher prepare --version nightly-2026-11-13-9f42064
horizon-launcher import-build airjump-native-9f42064-a8abd820b571.zip \
  --version nightly-2026-11-13-9f42064 --trust-unsigned
horizon-launcher play
```

The precompiled release zip is Linux x86_64. On other platforms, install
`airjump-0.0.1-26.1.2.hnmod` and run `horizon-launcher native-build
--trust-native-code` to compile it locally.

Native mods are not sandboxed; only install sources you trust.
