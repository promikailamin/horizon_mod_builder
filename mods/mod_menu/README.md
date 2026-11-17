# Mod Menu 0.3.6 for Horizon 9f42064

This is the Mod Menu bundle from issue #13 (`mod_menu 0.3.5`), converted to build on
Horizon Nightly 2026-11-13 (`9f42064`).

## Conversion

Horizon removed the `Game::options_to_game` field between `fdc87ae` and `9f42064`.
`mixins/mod_menu/ui.rs` read and restored that field when opening a mod's settings
page from the Mod Menu. The converted `mixins/mod_menu/ui.rs` no longer touches it:

```rust
let from_title = game.options_from_title;
game.open_options_at(from_title, Page::NativeMod(index));
```

`horizon-native.json`, `horizon-mixin.toml` and the runtime version constant now say
`0.3.6` and pin Horizon `9f42064c11efe7ef3e5ed2baad7ddc2a3b36eea0`.

Upstream: <https://github.com/tariksabanuz/ModMenuHorizon> (MIT).

## Build

```bash
./build.sh --portable mods/mod_menu \
  --horizon-version nightly-2026-11-13-9f42064 --ignore-pins
```
