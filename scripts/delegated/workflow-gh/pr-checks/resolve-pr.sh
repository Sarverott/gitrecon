#!/usr/bin/env bash
# Look up the pull request the checks run for, so every job checks the same commits.
#
# arg 1     pull request number
# outputs   number, base_sha, head_sha
# shellcheck source=scripts/delegated/workflow-gh/_lib.sh
source "$(dirname "$0")/../_lib.sh"

gh pr view "$1" --json number,baseRefOid,headRefOid,baseRefName,headRefName \
  --jq '"number=\(.number)\nbase_sha=\(.baseRefOid)\nhead_sha=\(.headRefOid)\nbranches=\(.headRefName) → \(.baseRefName)"' \
  | tee -a "${GITHUB_OUTPUT:-/dev/null}"
