import unittest
from scripts.cleanup_merged_branches import candidates, cleanup


class CleanupTest(unittest.TestCase):
    def test_only_merged_same_repository_pull_requests(self):
        event = {
            "action": "closed",
            "pull_request": {
                "merged": True,
                "head": {
                    "ref": "work",
                    "sha": "a",
                    "repo": {"full_name": "owner/repo"},
                },
            },
        }
        self.assertEqual(
            candidates("pull_request", event, "owner/repo"), [("work", "a")]
        )
        self.assertEqual(candidates("pull_request", event, "other/repo"), [])
        event["pull_request"]["merged"] = False
        self.assertEqual(candidates("pull_request", event, "owner/repo"), [])

    def run_cleanup(
        self,
        protected=False,
        sha="a",
        status="ahead",
        ref="a",
        branch="work",
        default="master",
    ):
        calls = []
        deleted = False

        def api(method, path):
            nonlocal deleted
            calls.append((method, path))
            if method == "DELETE":
                deleted = True
                return None
            if "/branches/master" in path:
                return {"commit": {"sha": "base"}}
            if "/branches/" in path:
                return {"protected": protected, "commit": {"sha": sha}}
            if "/compare/" in path:
                return {"status": status}
            return None if deleted else {"object": {"sha": ref}}

        return cleanup(api, "owner/repo", branch, "a", default), calls

    def test_deletes_only_unchanged_contained_ref(self):
        result, calls = self.run_cleanup()
        self.assertEqual(result, "deleted merged branch")
        self.assertEqual(sum(method == "DELETE" for method, _ in calls), 1)
        self.assertEqual(calls[-1][0], "GET")

    def test_default_protected_new_unmerged_and_changed_refs_survive(self):
        for options in (
            {"branch": "master"},
            {"protected": True},
            {"sha": "new"},
            {"status": "diverged"},
            {"status": "behind"},
            {"ref": "new"},
        ):
            with self.subTest(options=options):
                _, calls = self.run_cleanup(**options)
                self.assertFalse(any(method == "DELETE" for method, _ in calls))

    def test_missing_refs_are_idempotent(self):
        self.assertEqual(
            cleanup(lambda *args: None, "owner/repo", "work", "a", "master"),
            "already absent",
        )

    def test_bootstrap_requires_default_branch_push(self):
        event = {"ref": "refs/heads/master", "repository": {"default_branch": "master"}}
        self.assertEqual(len(candidates("push", event, "owner/repo")), 2)
        event["ref"] = "refs/heads/unmerged"
        self.assertEqual(candidates("push", event, "owner/repo"), [])
