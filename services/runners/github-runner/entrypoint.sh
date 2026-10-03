#!/usr/bin/env bash
# Register an ephemeral runner, run exactly one job as the `runner` user, then deregister.
# The container restarts (compose restart policy) and registers a fresh runner for the next job.
#
# env REPOSITORY      owner/repo the runner serves, e.g. Sarverott/gitrecon
# env ACCESS_TOKEN    token allowed to manage the repo's runners (Administration: write);
#                     only this root process sees it, jobs never do
# env RUNNER_LABELS   extra labels, comma separated (self-hosted, Linux, X64 are added by GitHub)
# env RUNNER_PREFIX   runner name prefix (the container hostname is appended)
set -euo pipefail

: "${REPOSITORY:?REPOSITORY (owner/repo) is required}"
: "${ACCESS_TOKEN:?ACCESS_TOKEN is required (task services:up -- github-runner fills it from gh auth token)}"
API="https://api.github.com/repos/${REPOSITORY}/actions/runners"
NAME="${RUNNER_PREFIX:-gitrecon}-$(hostname)"

runner_token() {  # registration | remove
  curl -fsSL -X POST \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -H "Accept: application/vnd.github+json" \
    "${API}/$1-token" | jq -r .token
}

# run as the unprivileged user, with a clean environment that does not contain ACCESS_TOKEN
as_runner() {
  env -i HOME=/home/runner USER=runner LANG="$LANG" PATH="$PATH" \
    RUNNER_TOOL_CACHE="$RUNNER_TOOL_CACHE" \
    setpriv --reuid=runner --regid=runner --init-groups "$@"
}

cd "$RUNNER_HOME"

# a restarted container still has the previous registration and workspace
rm -f .runner .credentials .credentials_rsaparams
rm -rf _work

as_runner ./config.sh --unattended --ephemeral --replace --disableupdate \
  --url "https://github.com/${REPOSITORY}" \
  --token "$(runner_token registration)" \
  --name "$NAME" \
  --labels "${RUNNER_LABELS:-gitrecon}" \
  --work _work

deregister() {
  echo "Stopping: deregistering ${NAME}"
  kill -TERM "$RUNNER_PID" 2>/dev/null || true
  wait "$RUNNER_PID" 2>/dev/null || true
  as_runner ./config.sh remove --token "$(runner_token remove)" || true
}
trap 'deregister; exit 143' TERM INT

as_runner ./run.sh &
RUNNER_PID=$!
wait "$RUNNER_PID"
