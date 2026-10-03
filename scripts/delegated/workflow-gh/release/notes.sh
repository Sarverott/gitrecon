#!/usr/bin/env bash
# Write release_notes.md: this release's section of CHANGELOG.md
# (commitizen writes it as "## vX.Y.Z (date)" ... up to the next "## ").
#
# env TAG_NAME   release tag (from bump.sh)
# shellcheck source=scripts/delegated/workflow-gh/_lib.sh
source "$(dirname "$0")/../_lib.sh"

: > release_notes.md
if [ -f CHANGELOG.md ]; then
  awk -v tag="$TAG_NAME" '
    /^## / { if (found) exit; if ($2 == tag) found = 1 }
    found
  ' CHANGELOG.md > release_notes.md
fi
if [ ! -s release_notes.md ]; then
  echo "Release $TAG_NAME" > release_notes.md
fi
cat release_notes.md
