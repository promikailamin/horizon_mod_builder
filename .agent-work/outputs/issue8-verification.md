# Issue #8 verification: complete issues #6 and #7

Date: 2026-11-15 (GitHub Actions runner)

This report records the work that was resumed after issue #6's action was cancelled.

## What was already implemented

- Combined builds are the default: multiple mods go into one importable package.
- The test mods (`enchantmenthints` + `mod_menu`) build together.
- `import-build` is tested, and the "prepared already" message is documented as success.
- `README.md` includes local installation instructions.
- `upload.sh` packs local mods, uploads a temporary release asset, and dispatches the build
  workflow.

## Rate-limit failure found in the cancelled logs

The first workflow-dispatch test failed before compiling:

```text
error: Can't tell which of the mods' horizon-mixins revisions is newest:
GitHub's rate limit was reached for your network
```

Commit `3f70350` passes `GH_TOKEN`/`GITHUB_TOKEN` to the launcher as `HORIZON_GITHUB_TOKEN`.
The launcher binary honours that variable for its GitHub API requests.

## GitHub Actions build (verification of the fix)

- Run: https://github.com/promikailamin/horizon_mod_builder/actions/runs/43683190389
- Result: **success** (all build steps, summary and artifact upload)
- Artifact: `horizon-mod-build-17`
- Base Horizon: `nightly-2026-11-13-9f42064`
- Built version: `native-fdc87ae-a9845d89dc7b`
- Horizon revision: `fdc87aecdbd116bf1e08adcd062fcbaea8c2e2ca`
- horizon-mixins: `5a64af938ec86b00d53d16a408aabc0038fb3e57`
- Profile: `dev`
- Package: `builds/enchantmenthints-mod_menu-native-fdc87ae-a9845d89dc7b.zip`
- SHA-256: `183925ccf444f49c2f8ef4c120eb0f061ddca84059966566bc43320d1a4d95a5`
- `native-mods.json` lists both `enchantmenthints 0.1.0` and `mod_menu 0.3.5`; `left_out` is empty.

The downloaded CI artifact was imported with:

```bash
.agent-work/tests/test_import_built.sh .agent-work/tmp/ci-artifact-17/builds/*.zip
```

Exit 0:

```text
Imported imported-2026-11-15-7cb7c1e and selected it. It is prepared already, from another installed version.
Imported and smoke-tested: .../versions/imported-2026-11-15-7cb7c1e
```

The imported `horizon-client --help` also exits 0.

## Local build and import

```bash
./build.sh --test-mods --profile dev
.agent-work/tests/test_import_built.sh dist/builds/*.zip
```

Both exited 0 and produced/imported `native-fdc87ae-a9845d89dc7b`. Full output is compressed in
`.agent-work/logs/issue8-build.log.gz`; import output is in `.agent-work/logs/issue8-import.log`.

## `upload.sh` path

`./upload.sh --dry-run --mode combined --profile dev ...` exited 0 and packaged both mod sources.
The resulting upload zip (`.agent-work/tmp/horizon-mods-20261115-063628.zip`) was then passed to
`./build.sh ... --profile dev`, which rebuilt and validated the same combined package. Logs:
`issue8-upload-dry-run.log` and `issue8-upload-zip-build.log`.

## Tests

```bash
python3 .agent-work/tests/test_build_mods.py
```

6 tests passed, including new coverage for GitHub URL extraction (repository roots with a trailing
slash or `.git`, release assets, and ignored engine/deep-link URLs). Log: `tests-latest.log`.

## Stored artifacts

- `.agent-work/outputs/issue8-ci-manifest.json` - downloaded CI run manifest
- `.agent-work/outputs/issue8-local-manifest.json` - local build manifest
- `.agent-work/outputs/issue8-ci-sha256.txt` - CI package and `.hnmod` hashes
- `.agent-work/logs/issue8-ci-combined.log.gz` - full CI combined build log
- `.agent-work/logs/issue8-ci-launcher.log` - CI launcher log
