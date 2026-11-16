import subprocess
import unittest
from scripts.ci_scope import changed_paths, needs_browser


class ScopeTest(unittest.TestCase):
    def test_only_documentation_and_known_branch_maintenance_skip(self):
        self.assertFalse(needs_browser(["docs/development.md", "README.md"]))
        self.assertFalse(
            needs_browser(
                [
                    "scripts/cleanup_merged_branches.py",
                    ".github/workflows/cleanup-merged-branches.yml",
                ]
            )
        )
        for path in [
            "web/app.js",
            "core.py",
            "languages.py",
            "catalog.py",
            "dataset-source.json",
            "search_relations.py",
            "tests/browser/mentions.spec.cjs",
            "scripts/ci_scope.py",
            ".github/workflows/test.yml",
            ".github/workflows/dataset.yml",
            "new/unknown",
        ]:
            self.assertTrue(needs_browser([path]), path)
        self.assertTrue(needs_browser([]))
        self.assertTrue(needs_browser(["docs/old.md", "web/new.md"]))

    def test_diff_uses_merge_result_and_keeps_deleted_or_renamed_paths(self):
        before, head = "a" * 40, "b" * 40

        def run(args):
            self.assertIn("--no-renames", args)
            self.assertEqual(args[-3:], [before, head, "--"])
            return b"web/old.js\0docs/new.md\0"

        self.assertEqual(
            changed_paths(
                "pull_request", {"pull_request": {"base": {"sha": before}}}, head, run
            ),
            ["web/old.js", "docs/new.md"],
        )
        self.assertIsNone(changed_paths("push", {"before": "0" * 40}, head))

        def fail(args):
            raise subprocess.CalledProcessError(1, args)

        self.assertIsNone(changed_paths("push", {"before": before}, head, fail))
