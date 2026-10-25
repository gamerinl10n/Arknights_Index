"""Bundle integrity must be checked before generated data can be reused."""

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from dataset import INPUTS, fingerprint, pack, restore


class DatasetTest(unittest.TestCase):
    def test_reuse_integrity_and_transform_invalidation(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in INPUTS:
                (root / name).write_text("synthetic input", encoding="utf8")
            for name in (
                "generated/search.sqlite.gz",
                "characters.json",
                "characters.source.json",
                "generated/portraits/index.json",
            ):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"synthetic bundle member")
            bundle = root / "bundle.zip"
            pack(root, bundle)
            data = root / "generated/search.sqlite.gz"
            data.write_bytes(b"old")
            restore(bundle, root)
            self.assertEqual(data.read_bytes(), b"synthetic bundle member")
            before = fingerprint(root)
            (root / "core.py").write_text("changed parser")
            self.assertNotEqual(fingerprint(root), before)
            data.write_bytes(b"preserve")
            with self.assertRaisesRegex(ValueError, "fingerprint"):
                restore(bundle, root)
            self.assertEqual(data.read_bytes(), b"preserve")

    def test_corrupt_or_unexpected_bundle_never_replaces_output(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in INPUTS:
                (root / name).write_text("fixture")
            data = root / "generated/search.sqlite.gz"
            data.parent.mkdir()
            data.write_bytes(b"preserve")
            names = [
                "generated/search.sqlite.gz",
                "characters.json",
                "characters.source.json",
                "generated/portraits/index.json",
            ]
            for extra, bad_hash in [(True, False), (False, True)]:
                files = {name: hashlib.sha256(b"new").hexdigest() for name in names}
                if extra:
                    files["../escape"] = hashlib.sha256(b"new").hexdigest()
                if bad_hash:
                    files[names[-1]] = "invalid"
                bundle = root / "invalid.zip"
                with zipfile.ZipFile(bundle, "w") as archive:
                    archive.writestr(
                        "manifest.json",
                        json.dumps({"fingerprint": fingerprint(root), "files": files}),
                    )
                    for name in files:
                        archive.writestr(name, b"new")
                with self.assertRaises(ValueError):
                    restore(bundle, root)
                self.assertEqual(data.read_bytes(), b"preserve")

    def test_runtime_service_changes_preserve_fingerprint(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in INPUTS:
                (root / name).write_text("synthetic build input", encoding="utf8")
            for name in (
                "generated/search.sqlite.gz",
                "characters.json",
                "characters.source.json",
                "generated/portraits/index.json",
            ):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"synthetic bundle member")
            bundle = root / "bundle.zip"
            pack(root, bundle)
            before = fingerprint(root)
            service = root / "search_service.py"
            service.write_text("synthetic runtime service", encoding="utf8")
            self.assertEqual(fingerprint(root), before)
            service.write_text("changed runtime service", encoding="utf8")
            self.assertEqual(fingerprint(root), before)
            data = root / "generated/search.sqlite.gz"
            data.write_bytes(b"old")
            restore(bundle, root)
            self.assertEqual(data.read_bytes(), b"synthetic bundle member")

    def test_snapshot_build_inputs_still_invalidate_fingerprint(self):
        build_inputs = (
            "dataset-source.json",
            "core.py",
            "catalog.py",
            "character_catalog.py",
            "build.py",
            "build_portraits.py",
            "dataset.py",
            "portraits.source.json",
            "requirements.txt",
            "search_queries.py",
            "translation_alignment.py",
        )
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in build_inputs:
                (root / name).write_text("synthetic build input", encoding="utf8")
            before = fingerprint(root)
            for name in build_inputs:
                with self.subTest(input=name):
                    path = root / name
                    path.write_text("changed build input", encoding="utf8")
                    self.assertNotEqual(fingerprint(root), before)
                    path.write_text("synthetic build input", encoding="utf8")
                    self.assertEqual(fingerprint(root), before)
