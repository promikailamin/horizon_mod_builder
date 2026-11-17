# Horizonmatica 0.3.3 for Horizon 9f42064

This is the upstream **Horizonmatica 0.3.3** native bundle, which is the
maintainer's conversion of the issue #13 `horizonmatica 0.3.2` bundle to Horizon
Nightly 2026-11-13 (`9f42064`).

Issue #13 shipped `0.3.2`, pinned to the older `fdc87ae` Nightly. It cannot build
on `9f42064` because Horizon removed `Game::options_to_game`, which the menu
library set when opening the mod's page. Version `0.3.3` drops that field and
further makes `Esc` on the fallback Options > Mods page return to the pause menu.
It pins `horizon = 9f42064c11efe7ef3e5ed2baad7ddc2a3b36eea0`.

- Upstream: <https://github.com/keksi2k/horizonmatica>
- Release asset: `horizonmatica-0.3.3.hnmod` from
  <https://github.com/keksi2k/horizonmatica/releases/tag/v0.3.3>
- SHA-256 of the upstream asset:
  `b689878c7cddbb021e914d5094233e49352ba4f0676cf30cca3c45873074fbdc`
- License: MIT (see `LICENSE`)

## Build

```bash
./build.sh --portable mods/horizonmatica \
  --horizon-version nightly-2026-11-13-9f42064 --ignore-pins
```
