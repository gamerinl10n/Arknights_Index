"""Exercise PR-policy fallback without contacting GitHub."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/open_dataset_pr.sh'


class DatasetPRTest(unittest.TestCase):
    def run_pr(self, error, status):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            gh = root / 'gh'
            gh.write_text('#!/bin/sh\nprintf "%s" "$FAKE_ERROR" >&2\nexit "$FAKE_STATUS"\n')
            gh.chmod(0o755)
            body = root / 'body.txt'
            body.write_text('Validated counts; no automatic merge.\n')
            summary = root / 'summary.md'
            env = dict(os.environ, PATH=f'{root}:' + os.environ['PATH'],
                       FAKE_ERROR=error, FAKE_STATUS=str(status),
                       GITHUB_REPOSITORY='example/repo', CANDIDATE_REVISION='a' * 40,
                       GITHUB_STEP_SUMMARY=str(summary))
            result = subprocess.run(['bash', str(SCRIPT), 'automation/dataset-' + 'a' * 40,
                                     str(body)], env=env, text=True, capture_output=True)
            return result, summary.read_text() if summary.exists() else ''

    def test_success_does_not_request_manual_pr(self):
        result, summary = self.run_pr('', 0)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(summary, '')

    def test_only_policy_denial_becomes_manual_handoff(self):
        result, summary = self.run_pr(
            'GraphQL: GitHub Actions is not permitted to create or approve pull requests (createPullRequest)', 1)
        self.assertEqual(result.returncode, 0)
        self.assertIn('::warning::', result.stdout)
        self.assertIn('manual PR required', summary)
        self.assertIn('compare/master...automation/dataset-' + 'a' * 40, summary)
        self.assertIn('Validated counts', summary)

    def test_other_errors_still_fail(self):
        for error in ['HTTP 401: Bad credentials', 'HTTP 502: Bad Gateway']:
            with self.subTest(error=error):
                result, summary = self.run_pr(error, 7)
                self.assertEqual(result.returncode, 7)
                self.assertEqual(summary, '')
