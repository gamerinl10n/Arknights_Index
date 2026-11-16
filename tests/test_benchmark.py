from contextlib import closing
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from core import connect, ingest
from scripts.benchmark import benchmark, profile_allocations


class BenchmarkTest(unittest.TestCase):
    def test_report_is_readonly_and_contains_no_dialogue(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for folder in ("kr", "cn", "jp", "en"):
                source = root / folder / "gamedata/story/synthetic.txt"
                source.parent.mkdir(parents=True)
                source.write_text(
                    '[name="Mon3tr"]the 안녕 你好 PRIVATE_SYNTHETIC_SENTENCE',
                    encoding="utf-8",
                )
            path = root / "fixture.sqlite"
            with closing(connect(path)) as db:
                ingest(db, root, "synthetic", "synthetic")
            before = hashlib.sha256(path.read_bytes()).hexdigest()
            report = benchmark(
                path, rounds=2, unified=True, profile_memory=True, mentions=True
            )
            self.assertEqual(before, hashlib.sha256(path.read_bytes()).hexdigest())
            self.assertNotIn("PRIVATE_SYNTHETIC_SENTENCE", json.dumps(report))
            self.assertEqual(report["unified_common"]["total"], 4)
            self.assertGreater(report["unified_common"]["python_peak_bytes"], 0)
            self.assertEqual(len(report["unified_common"]["response_sha256"]), 64)
            self.assertIn("excludes SQLite", report["measurement"]["memory"])
            self.assertEqual(len(report["third_party_ko_light"]["response_sha256"]), 64)
            self.assertIn(
                "python_peak_bytes", report["third_party_surrounding_ko_light"]
            )

    def test_profile_cleanup_on_error_and_round_validation(self):
        import tracemalloc

        def fail():
            raise ValueError("fixture")

        with self.assertRaises(ValueError):
            profile_allocations(fail)
        self.assertFalse(tracemalloc.is_tracing())
        with self.assertRaises(ValueError):
            benchmark("unused", rounds=1)
