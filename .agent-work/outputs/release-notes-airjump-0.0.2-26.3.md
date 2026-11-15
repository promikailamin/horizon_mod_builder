# AirJump 0.0.2-26.3 for Horizon

This release contains the Horizon native port of the Fabric mod
[`promikailamin/AirJump`](https://github.com/promikailamin/AirJump), updated
for **Minecraft 26.3** and the latest Horizon Nightly. The precompiled Linux
package is now built against **glibc 2.35**, so it no longer requires the
GitHub runner's GLIBC 2.43 and runs on Ubuntu 22.04/24.04 and Debian 12.

## Downloads

| Asset | What it is |
| --- | --- |
| `airjump-0.0.2-26.3.hnmod` | Horizon native mod source bundle. Import it with the launcher and build it locally. |
| `airjump-native-9f42064-7d0d9e4b6ceb.zip` | Precompiled Horizon client with AirJump compiled in, built against glibc 2.35. Import this zip to play immediately. |

## Features

- **AirJump**: jump again while airborne.
- **SuperLaunch**: right-click while holding the configured launch item
  (`minecraft:stick` by default) to launch in the direction you are looking.
- **NoFall**: sends the no-fall movement flag while falling.
- Settings are stored in `config/airjump.json` in the game folder:
  `multi_jump`, `launch`, `no_fall_damage`, `launchWand`, `launchVelocity`.

The Fabric Mod Menu settings screen is not part of the native port because
Horizon native mods do not load Fabric/Mod Menu screens; edit
`config/airjump.json` instead.

## Build details

- Base Horizon: `nightly-2026-11-13-9f42064` (latest Nightly)
- Horizon revision: `9f42064c11efe7ef3e5ed2baad7ddc2a3b36eea0`
- horizon-mixins: `5a64af938ec86b00d53d16a408aabc0038fb3e57`
- Minecraft: `26.3`
- Native profile: `dev`
- Built version: `native-9f42064-7d0d9e4b6ceb`
- Platform: Linux x86_64, maximum required symbol version `GLIBC_2.35`
- Artifact SHA-256: `a61f29cd32f8cb7ccd4abec9a3f97488474ef2a263ecdd184ef10a91f6209f02`
- `.hnmod` SHA-256: `4010803b48eaba30992896844c3094af8352365f484b7713a9bad4461e108d52`

## Install

```bash
horizon-launcher install nightly-2026-11-13-9f42064
horizon-launcher prepare --version nightly-2026-11-13-9f42064
horizon-launcher import-build airjump-native-9f42064-7d0d9e4b6ceb.zip \
  --version nightly-2026-11-13-9f42064 --trust-unsigned
horizon-launcher play
```

If that base version is already installed and prepared:

```bash
horizon-launcher import-build airjump-native-9f42064-7d0d9e4b6ceb.zip --trust-unsigned
horizon-launcher play
```

`It is prepared already, from another installed version.` is a successful
import, not an error.

To build the `.hnmod` yourself for your own platform:

```bash
horizon-launcher mods add airjump-0.0.2-26.3.hnmod --trust-native-code
horizon-launcher native-build --trust-native-code
horizon-launcher play
```

The precompiled zip is a Linux x86_64 build compiled against glibc 2.35.
Windows and macOS players should build the `.hnmod` locally.

Native mods are not sandboxed. Only install sources you trust.
