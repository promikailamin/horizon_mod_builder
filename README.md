# Horizon Mod Builder

A GitHub Actions-powered builder for [Horizon](https://github.com/horizon-client/horizon) native mods.

## What this is

This repository contains the **Horizon Launcher**, Horizon Rust source, Minecraft configs, and a GitHub Actions workflow that:

1. Receives a mod source (from a GitHub Issue comment `/build <repo-url>` or manual dispatch).
2. Installs the native build dependencies (`build-essential`, `pkg-config`, `libasound2-dev`, `libudev-dev`).
3. Runs `horizon_launcher native-build --trust-native-code` to compile the mod.
4. Uploads the resulting `.hnmod` file as a GitHub Actions artifact you can download.

**No `.hnmod` files are stored in this repository** — they are produced by the build and delivered as workflow artifacts.

## Repository layout

```
horizon_mod_builder/
├── horizon_launcher                 # Horizon Launcher executable (build tool)
├── build.sh                         # Local build script
├── rust/horizon-prepare/            # Horizon Rust source crate
├── configs/minecraft/
│   ├── minecraft.zip                # Minecraft game zip (tracked with Git LFS)
│   └── .minecraft/                  # Minecraft launcher config (libs, versions)
│                                       (secrets & usercache excluded)
├── mods/                            # Mod source goes here (no .hnmod committed)
├── .github/workflows/build.yml      # GitHub Actions build workflow
├── .gitignore                       # Excludes .hnmod, secrets, caches
└── .gitattributes                   # Git LFS tracking for large files
```

## Quick start (local)

```bash
cd horizon_mod_builder
chmod +x build.sh horizon_launcher

# Build the default horizon-prepare crate
./build.sh

# Build a specific mod (local folder or git repo)
./build.sh /path/to/mod/source
./build.sh https://github.com/user/some-mod.git
```

## GitHub Actions setup

1. **Push this repository to GitHub** (see "Pushing to GitHub" below).

2. **Add repository secrets** (never put these in code):
   - Go to your repo → **Settings** → **Secrets and variables** → **Actions**.
   - Add `MINECRAFT_EMAIL` and `MINECRAFT_PASSWORD` (or leave empty — the launcher handles auth itself).
   - **Do NOT commit `launcher_msa_credentials.bin`, `launcher_accounts.json`, or `usercache.json`** — they are already gitignored.

3. **Trigger a build**:
   - **Manual:** Actions → "Build Horizon Mod" → Run workflow (enter a mod repo URL).
   - **From an issue:** Create an issue, add the label `build-mod`, or comment `/build <repo-url>`.

4. **Download the artifact:**
   - After the run finishes, go to the Actions run page → **Artifacts** → download `horizon-mod-build.zip`.
   - Extract it to get your `.hnmod` file.

## Pushing to GitHub

This replaces your existing `horizon_mod_builder` repo:

```bash
cd horizon_mod_builder
git init
git add .
git commit -m "Initial commit: Horizon mod builder"

# Point at your GitHub repo (replace USERNAME with your GitHub user)
git remote add origin https://github.com/USERNAME/horizon_mod_builder.git
git branch -M main
git push -u origin main --force
```

> ⚠️ `--force` overwrites the existing repo. Make sure you have saved anything you need from it first.

### Large files (Git LFS)

`configs/minecraft/minecraft.zip` is 205 MB, which exceeds GitHub's 100 MB file limit. It is tracked with **Git LFS**. Before pushing, install Git LFS:

```bash
sudo apt install git-lfs   # or brew install git-lfs
git lfs install
git lfs track "configs/minecraft/minecraft.zip"
git add .gitattributes configs/minecraft/minecraft.zip
git commit -m "Track minecraft.zip with Git LFS"
git push
```

If you don't want to use LFS, remove `minecraft.zip` from the repo — the Horizon Launcher downloads Minecraft game data automatically during the build.

## Security

- `.hnmod` files are **never committed** — they are build outputs only.
- Minecraft/Microsoft account files (`launcher_msa_credentials.bin`, `launcher_accounts.json`, `usercache.json`, etc.) are **excluded via `.gitignore`**.
- Provide any account credentials via **GitHub Secrets**, not in the repository.
