# shellcheck shell=bash
# Shared helpers for the scripts GitHub Actions delegates to. Source it, don't run it.
# Scripts work both in CI and locally: without GitHub's files, outputs and env just print.
set -euo pipefail

# run from the repository root, wherever the script was called from
cd "$(dirname "${BASH_SOURCE[0]}")/../../.."

# step output, read in the workflow as steps.<id>.outputs.<name>
output() {
  echo "$1=$2" >> "${GITHUB_OUTPUT:-/dev/stdout}"
}

# variable for this and all later steps of the job (env.<name> in the workflow)
export_env() {
  export "$1=$2"
  echo "$1=$2" >> "${GITHUB_ENV:-/dev/stdout}"
}
