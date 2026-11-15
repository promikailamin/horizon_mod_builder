# Final build and import test

Date: 2026-11-15 (GitHub Actions runner)

## Integration build

Command:

```bash
HORIZON_BUILDER_SKIP_DEPS=1 ./build.sh --test-mods --profile dev
```

Result: exit 0.

- Base Horizon: `nightly-2026-11-13-9f42064`
- Built Horizon revision: `fdc87aecdbd116bf1e08adcd062fcbaea8c2e2ca`
- horizon-mixins: `5a64af938ec86b00d53d16a408aabc0038fb3e57`
- Package: `dist/builds/enchantmenthints-mod_menu-native-fdc87ae-a9845d89dc7b.zip`
- Built version: `native-fdc87ae-a9845d89dc7b`
- Mods in package: `enchantmenthints 0.1.0`, `mod_menu 0.3.5`
- Package size: about 54 MiB

The package contains `BUILD-INFO.txt`, `INSTALL.txt`, the compiled `horizon-client`,
`native-mods.json`, and both `.hnmod` sources under `mod-source/`.

A second run used a local zip served over HTTP:

```bash
./build.sh http://127.0.0.1:8765/local-mods.zip --profile dev --horizon-version latest
```

That verified remote-zip upload support and the new combined-by-default behaviour.

## Import test

Command:

```bash
horizon-launcher import-build dist/builds/*.zip --trust-unsigned
```

Output (exit 0):

```text
Imported imported-2026-11-15-354dfdb and selected it. It is prepared already, from another installed version.
```

This message is success, not an error. The imported build was selected automatically.
The imported `horizon-client --help` also ran successfully with exit 0.

Reusable script: `.agent-work/tests/test_import_built.sh`.

## Unit tests

Command:

```bash
python3 .agent-work/tests/test_build_mods.py
```

Result: 4 tests passed (archive discovery with wrapper/multiple mods, zip-slip rejection,
local packing, .hnmod layout validation).

## upload.sh test

Command:

```bash
./upload.sh --dry-run --mode combined --profile performance --horizon-version latest \
  .work/staging/d3grando-enchantmenthints \
  .work/staging/archives/local-mods/mod_menu-0.3.5.hnmod
```

Result: exit 0. The script packed two mod sources and printed the release-create and
`gh workflow run build.yml` commands without uploading.
