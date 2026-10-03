#!/usr/bin/env bash
# Bump the version for this loop (policy in .github/bos.config.json "versioning"):
# commitizen updates metadata.json, manifests, lockfiles and CHANGELOG.md,
# then commits "bump: ..." and tags vX.Y.Z.
#
# exports   VERSION (X.Y.Z), TAG_NAME (vX.Y.Z)
# shellcheck source=scripts/delegated/workflow-gh/_lib.sh
source "$(dirname "$0")/../_lib.sh"

# the bump commit is made by the CI bot
git config user.name "github-actions[bot]"
git config user.email "github-actions[bot]@users.noreply.github.com"

# only the delivery tools (commitizen, task, tomlkit), not the heavy dev group
uv sync --frozen --no-default-groups --group delivery
export UV_NO_SYNC=1
python3 .github/bos/flow.py bump

VERSION=$(node -p "require('./package.json').version")
export_env VERSION "$VERSION"
export_env TAG_NAME "v$VERSION"
echo "Release version: $VERSION"
