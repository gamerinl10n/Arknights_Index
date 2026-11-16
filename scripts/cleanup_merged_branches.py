"""Remove only unchanged work refs already contained in the default branch."""

import json
import os
import subprocess
from urllib.parse import quote

# One-time bootstrap for the explicitly requested, now-merged feature work.
BOOTSTRAP = (
    ("feat/third-party-mentions", "3dd7dcb35a19a52445b1b0d1782af5d347237813"),
    ("docs/character-research-development", "039a71350a1c8f8b2c67d5e21164c16a4bcef962"),
)


def candidates(event_name, event, repository):
    if event_name == "push":
        default = event["repository"]["default_branch"]
        return list(BOOTSTRAP) if event.get("ref") == "refs/heads/" + default else []
    pr = event.get("pull_request", {})
    head = pr.get("head", {})
    if (
        event_name == "pull_request"
        and event.get("action") == "closed"
        and pr.get("merged")
        and head.get("repo", {}).get("full_name") == repository
    ):
        return [(head["ref"], head["sha"])]
    return []


def cleanup(api, repository, branch, expected, default):
    if branch == default:
        return "default branch preserved"
    prefix = "repos/" + repository
    info = api("GET", prefix + "/branches/" + quote(branch, safe=""))
    if info is None:
        return "already absent"
    if info.get("protected"):
        return "protected branch preserved"
    if info["commit"]["sha"] != expected:
        return "new commits preserved"
    base = api("GET", prefix + "/branches/" + quote(default, safe=""))
    comparison = api(
        "GET", prefix + "/compare/" + expected + "..." + base["commit"]["sha"]
    )
    if comparison["status"] not in ("ahead", "identical"):
        return "unmerged commits preserved"
    ref_path = prefix + "/git/refs/heads/" + quote(branch, safe="")
    current = api("GET", ref_path)
    if current is None:
        return "already absent"
    if current["object"]["sha"] != expected:
        return "changed ref preserved"
    api("DELETE", ref_path)
    if api("GET", ref_path) is not None:
        raise RuntimeError("Branch deletion could not be verified")
    return "deleted merged branch"


def github_api(method, path):
    result = subprocess.run(
        ["gh", "api", "--method", method, path], capture_output=True, text=True
    )
    if result.returncode:
        if method == "GET" and "(HTTP 404)" in result.stderr:
            return None
        raise RuntimeError("GitHub API operation failed: " + method + " " + path)
    return json.loads(result.stdout) if result.stdout.strip() else None


def main():
    repository = os.environ["GITHUB_REPOSITORY"]
    with open(os.environ["GITHUB_EVENT_PATH"], encoding="utf-8") as stream:
        event = json.load(stream)
    default = github_api("GET", "repos/" + repository)["default_branch"]
    for branch, expected in candidates(
        os.environ["GITHUB_EVENT_NAME"], event, repository
    ):
        result = cleanup(github_api, repository, branch, expected, default)
        print(branch + ": " + result)


if __name__ == "__main__":
    main()
