#!/usr/bin/env bash
# Build the Python distributions (wheel + sdist) of the bumped version into dist/.
#
# env TAG_NAME   release tag (from bump.sh)
# outputs        dist_dir
# shellcheck source=scripts/delegated/workflow-gh/_lib.sh
source "$(dirname "$0")/../_lib.sh"

rm -rf dist
uv build --out-dir dist
output dist_dir dist
echo "Built distributions for ${TAG_NAME:-local}:"
ls -l dist
