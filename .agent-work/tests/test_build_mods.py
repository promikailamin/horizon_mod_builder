#!/usr/bin/env python3
"""Focused tests for archive discovery, packaging and manifest validation."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import build_mods  # noqa: E402
import pack_mods_zip  # noqa: E402


def write_bundle(root: Path, mod_id: str, version: str, native: bool = False) -> Path:
    bundle = root / mod_id
    bundle.mkdir(parents=True, exist_ok=True)
    mixin = f'[mod]\nid = "{mod_id}"\nversion = "{version}"\n'
    if native:
        (bundle / "horizon-native.json").write_text(
            json.dumps({"schema": 1, "id": mod_id, "version": version}), encoding="utf-8"
        )
        (bundle / "mixins" / mod_id).mkdir(parents=True, exist_ok=True)
        (bundle / "mixins" / mod_id / "horizon-mixin.toml").write_text(mixin, encoding="utf-8")
        (bundle / "mixins" / mod_id / "mod.rs").write_text("pub fn x() {}\n", encoding="utf-8")
    else:
        (bundle / "horizon-mixin.toml").write_text(mixin, encoding="utf-8")
        (bundle / "src").mkdir(exist_ok=True)
        (bundle / "src" / "lib.rs").write_text("pub fn x() {}\n", encoding="utf-8")
    return bundle


class IssueSourceTests(unittest.TestCase):
    def test_github_urls_from_issue_text(self) -> None:
        text = """
        Build https://github.com/alice/mod-a/ and
        https://github.com/bob/mod-b.git plus
        https://github.com/carol/mod-c/releases/download/v1/mod_c.hnmod
        https://github.com/horizon-rust/horizon
        https://github.com/alice/mod-a/issues/1
        """
        self.assertEqual(
            build_mods.urls_from_text(text),
            [
                "https://github.com/alice/mod-a/",
                "https://github.com/bob/mod-b.git",
                "https://github.com/carol/mod-c/releases/download/v1/mod_c.hnmod",
            ],
        )

    def test_repository_url_shapes(self) -> None:
        self.assertTrue(build_mods.is_github_repo_url("https://github.com/alice/mod-a"))
        self.assertTrue(build_mods.is_github_repo_url("https://github.com/alice/mod-a/"))
        self.assertTrue(build_mods.is_github_repo_url("https://github.com/alice/mod-a.git"))
        self.assertFalse(
            build_mods.is_github_repo_url("https://github.com/alice/mod-a/issues/1")
        )
        self.assertFalse(
            build_mods.is_github_repo_url(
                "https://github.com/alice/mod-a/releases/download/v1/mod.hnmod"
            )
        )


class ArchiveDiscoveryTests(unittest.TestCase):
    def test_archive_with_wrapper_and_multiple_mods(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive_path = root / "mods.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("wrapper/mod_a/horizon-mixin.toml", '[mod]\nid="mod_a"\nversion="1.0"\n')
                archive.writestr("wrapper/mod_a/src/lib.rs", "pub fn a() {}\n")
                archive.writestr("wrapper/mod_b/horizon-native.json", json.dumps({"id": "mod_b", "version": "2.0"}))
                archive.writestr("wrapper/mod_b/mixins/mod_b/horizon-mixin.toml", '[mod]\nid="mod_b"\nversion="2.0"\n')
                archive.writestr("wrapper/mod_b/mixins/mod_b/mod.rs", "pub fn b() {}\n")

            stage = root / "stage"
            stage.mkdir()
            jobs = build_mods.jobs_from_archive(archive_path, "https://example.test/mods.zip", stage)
            self.assertEqual([job.mod_id for job in jobs], ["mod_a", "mod_b"])
            self.assertEqual([job.mod_version for job in jobs], ["1.0", "2.0"])
            self.assertTrue(all(job.source == "https://example.test/mods.zip" for job in jobs))

    def test_zip_slip_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive_path = root / "bad.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("../escape.txt", "nope")
            with self.assertRaises(build_mods.BuildError):
                build_mods._extract_zip(archive_path, root / "out")

    def test_pack_mods_zip_keeps_bundles_and_hnmods(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = write_bundle(root / "inputs", "alpha", "1.0")
            native = write_bundle(root / "inputs", "beta", "2.0", native=True)
            hnmod = build_mods.write_hnmod(
                build_mods.Job("beta", native, str(native)),
                root,
                root / "beta-2.0.hnmod",
            )
            output = root / "upload.zip"
            items = pack_mods_zip.collect([str(bundle), str(hnmod)])
            self.assertEqual(len(items), 2)
            pack_mods_zip.write_zip(items, output)
            with zipfile.ZipFile(output) as archive:
                names = archive.namelist()
            self.assertIn("alpha/horizon-mixin.toml", names)
            self.assertTrue(any(name.endswith("beta-2.0.hnmod") for name in names))

    def test_validate_hnmod_layout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = write_bundle(root, "gamma", "3.0", native=True)
            path = build_mods.write_hnmod(
                build_mods.Job("gamma", bundle, str(bundle)),
                root,
                root / "gamma.hnmod",
            )
            build_mods.validate_hnmod(path)
            with zipfile.ZipFile(path) as archive:
                self.assertIn("mixins/gamma/horizon-mixin.toml", archive.namelist())


class AirJumpBundleTests(unittest.TestCase):
    """Keep the Fabric AirJump port buildable as a Horizon bundle."""

    bundle = ROOT / "mods" / "airjump"

    def test_bundle_metadata_and_injection(self) -> None:
        mod_id, version, manifest = build_mods.read_manifest(self.bundle)
        self.assertEqual(mod_id, "airjump")
        self.assertEqual(version, "0.0.1-26.1.2")
        self.assertEqual(
            manifest["compatibility"]["horizon_revision"],
            "9f42064c11efe7ef3e5ed2baad7ddc2a3b36eea0",
        )
        injections = manifest["injection"]
        self.assertEqual(
            [injection["target"] for injection in injections],
            [
                "horizon_client::game::native_hooks::Game<'_>::native_client_tick_post"
            ],
        )
        self.assertTrue((self.bundle / "runtime.rs").is_file())
        self.assertTrue((self.bundle / "airjump.rs").is_file())

    def test_packs_a_valid_hnmod(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            build_dir = root / "build"
            build_dir.mkdir()
            (build_dir / "native-mods.json").write_text(
                json.dumps(
                    {
                        "horizon": "9f42064c11efe7ef3e5ed2baad7ddc2a3b36eea0",
                        "horizon_mixins": "5a64af938ec86b00d53d16a408aabc0038fb3e57",
                    }
                ),
                encoding="utf-8",
            )
            path = build_mods.write_hnmod(
                build_mods.Job("airjump", self.bundle, str(self.bundle)),
                build_dir,
                root / "airjump.hnmod",
            )
            build_mods.validate_hnmod(path)
            with zipfile.ZipFile(path) as archive:
                native = json.loads(archive.read("horizon-native.json"))
                self.assertEqual(native["id"], "airjump")
                self.assertEqual(
                    native["horizon"],
                    "9f42064c11efe7ef3e5ed2baad7ddc2a3b36eea0",
                )
                self.assertIn(
                    "mixins/airjump/runtime.rs", archive.namelist()
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
