import json
import sqlite3
import unittest
from scripts.audit_search_coverage import audit


class CoverageTest(unittest.TestCase):
    def archive(self):
        db = sqlite3.connect(":memory:")
        self.addCleanup(db.close)
        db.executescript(
            "CREATE TABLE stories(id TEXT, lang TEXT, raw TEXT, revision TEXT); CREATE TABLE lines(story TEXT);"
        )
        return db

    def test_counts_unsupported_and_malformed_without_leaking_text(self):
        db = self.archive()
        raw = '[name="synthetic"]must-not-appear\n[FutureText(content="must-not-appear")]\n[name broken\nplain must-not-appear\n// comment\n[Delay(time=1)]'
        db.execute(
            "INSERT INTO stories VALUES(?,?,?,?)",
            ("example", "ko_KR", raw, "synthetic-revision"),
        )
        db.execute("INSERT INTO lines VALUES(?)", ("example",))
        report = audit(db)
        stat = report["languages"]["ko_KR"]
        self.assertEqual(stat["parsed_rows"], 1)
        self.assertEqual(stat["indexed_rows"], 1)
        self.assertEqual(stat["unsupported_text_commands"], {"futuretext": 1})
        self.assertEqual(stat["malformed_command_lines"], 1)
        self.assertEqual(stat["unparsed_noncommand_lines"], 1)
        self.assertEqual(report["issues"], {})
        self.assertNotIn("must-not-appear", json.dumps(report))
        self.assertNotIn("example", json.dumps(report))

    def test_index_loss_and_orphans_are_blocking_issues(self):
        db = self.archive()
        db.execute(
            "INSERT INTO stories VALUES(?,?,?,?)",
            ("example", "en_US", '[name="synthetic"]dialogue', "revision"),
        )
        db.execute("INSERT INTO lines VALUES(?)", ("orphan",))
        self.assertEqual(
            audit(db)["issues"],
            {"parser_index_count_mismatch_files": 1, "orphan_indexed_stories": 1},
        )

    def test_empty_archive_is_not_reported_as_success(self):
        self.assertEqual(audit(self.archive())["issues"], {"empty_archive": 1})
