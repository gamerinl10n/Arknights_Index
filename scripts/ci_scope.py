"""Fail-closed scope for expensive browser/data CI; unit checks always run."""

import json
import os
from pathlib import Path
import re
import subprocess

MAINTENANCE = {
    ".github/workflows/cleanup-merged-branches.yml",
    "scripts/cleanup_merged_branches.py",
    "tests/test_branch_cleanup.py",
}
DOCUMENTS = {"README.md", "AGENTS.md", "CONTRIBUTING.md", "LICENSE", "NOTICE"}


def needs_browser(paths):
    # Empty/unknown scope must not silently remove a release check.
    return not paths or any(
        not (path in DOCUMENTS or path in MAINTENANCE or path.startswith("docs/"))
        for path in paths
    )


def changed_paths(event_name, event, head, run=subprocess.check_output):
    base = (
        event.get("pull_request", {}).get("base", {}).get("sha")
        if event_name == "pull_request"
        else event.get("before")
    )
    if not all(
        value and re.fullmatch(r"[0-9a-f]{40}", value) and value != "0" * 40
        for value in (base, head)
    ):
        return None
    try:
        # Rename sources and destinations both matter; no rename folding.
        raw = run(
            ["git", "diff", "--name-only", "--no-renames", "-z", base, head, "--"]
        )
    except (subprocess.CalledProcessError, OSError):
        return None
    return raw.decode("utf-8").rstrip("\0").split("\0") if raw else []


def main():
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
    paths = changed_paths(
        os.environ["GITHUB_EVENT_NAME"], event, os.environ["GITHUB_SHA"]
    )
    required = paths is None or needs_browser(paths)
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as stream:
        stream.write("browser=" + str(required).lower() + "\n")
    print("Browser/data validation required:", required)


if __name__ == "__main__":
    main()
