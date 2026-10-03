#!/usr/bin/env bash
# Decide whether master's current commit still needs a release.
# A tagged commit is already released (for example our own bump commit).
#
# outputs   release=true|false
# shellcheck source=scripts/delegated/workflow-gh/_lib.sh
source "$(dirname "$0")/../_lib.sh"

if TAG=$(git describe --exact-match --tags HEAD 2>/dev/null); then
  echo "HEAD is already released as $TAG, nothing to do."
  output release false
else
  output release true
fi
