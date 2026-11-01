#!/usr/bin/env bash
# Called only after dataset validation and guarded branch publication succeed.
set -euo pipefail
branch=$1
body=$2
error_file=$(mktemp)
trap 'rm -f "$error_file"' EXIT
if gh pr create --base master --head "$branch" --title "Update game data source" --body-file "$body" 2>"$error_file"; then
  exit 0
else
  status=$?
fi
cat "$error_file" >&2
if ! grep -Fq 'GitHub Actions is not permitted to create or approve pull requests' "$error_file"; then
  exit "$status"
fi
# Keep repository policy intact. A maintainer/connected client opens the PR.
url="https://github.com/${GITHUB_REPOSITORY}/compare/master...${branch}?expand=1"
echo '::warning::Dataset validation passed; repository policy requires manual PR creation.'
{
  echo '## Dataset validated — manual PR required'
  echo
  echo "Source revision: ${CANDIDATE_REVISION}"
  echo
  echo "[Open the validated update PR]($url). Use update-pr-body.txt from the validation artifact."
  echo
  echo 'GitHub Actions PR creation is disabled by repository policy. Permissions were not changed. No merge was performed.'
  echo
  cat "$body"
} >> "$GITHUB_STEP_SUMMARY"
