# Self-hosted GitHub Actions runner for gitrecon (ported from shakespeare-mobile's gh-runners).
# What our workflows expect from GitHub's ubuntu-latest: git, curl, jq and Python.
# uv and Node.js come from the setup-* actions, cached in the toolcache volume.
FROM ubuntu:24.04

# pinned and verified; update both together (task services:runner:versions prints the current ones)
ARG RUNNER_VERSION=2.337.0
ARG RUNNER_SHA256=70920811a4f8ad4328818682bca5c6469c1c942fab52448868071d0063816613

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    RUNNER_HOME=/opt/actions-runner \
    RUNNER_TOOL_CACHE=/opt/hostedtoolcache

# apt packages follow the base image's security updates rather than exact pins
# hadolint ignore=DL3008
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      ca-certificates curl git jq unzip zip xz-utils python3 \
 && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 1001 runner \
 && mkdir -p "$RUNNER_TOOL_CACHE" \
 && chown -R runner:runner "$RUNNER_TOOL_CACHE" /home/runner

WORKDIR $RUNNER_HOME
RUN curl -fsSL -o runner.tar.gz "https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz" \
 && echo "${RUNNER_SHA256}  runner.tar.gz" | sha256sum -c - \
 && tar xzf runner.tar.gz && rm runner.tar.gz \
 && ./bin/installdependencies.sh \
 && rm -rf /var/lib/apt/lists/* \
 && chown -R runner:runner "$RUNNER_HOME"

COPY --chmod=755 entrypoint.sh /entrypoint.sh

# stays root: only the entrypoint holds ACCESS_TOKEN, the runner and its jobs run as `runner`
ENTRYPOINT ["/entrypoint.sh"]
