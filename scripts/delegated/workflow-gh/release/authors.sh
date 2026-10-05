#!/usr/bin/env bash
# Refresh AUTHORS from the git history, in the middle of a release: after testing was merged
# into releasing, before the pull request from releasing to master is opened.
# Identities of resources/ignorelist.txt (bots) are left out. Commits and pushes only when the
# file changed; a refused push is reported and does not stop the loop.
#
# needs     the whole history checked out (fetch-depth: 0) and contents: write
# shellcheck source=scripts/delegated/workflow-gh/_lib.sh
source "$(dirname "$0")/../_lib.sh"

BRANCH="${1:?usage: authors.sh BRANCH}"

# only gitrecon itself and its core dependencies
uv sync --frozen --no-default-groups
uv run --no-sync gitrecon contributors . --ignorelist --format authors > AUTHORS

if git diff --quiet -- AUTHORS && git ls-files --error-unmatch AUTHORS > /dev/null 2>&1; then
  echo "AUTHORS is up to date."
  exit 0
fi

git config user.name "github-actions[bot]"
git config user.email "github-actions[bot]@users.noreply.github.com"
git add AUTHORS
git commit --quiet --no-verify -m "docs(authors): refresh AUTHORS from the git history"
if git push origin "HEAD:$BRANCH"; then
  echo "AUTHORS refreshed on $BRANCH."
else
  echo "::warning::AUTHORS was refreshed but could not be pushed to $BRANCH (a branch rule?). The release goes on without it."
  git reset --quiet --hard "origin/$BRANCH"
fi
