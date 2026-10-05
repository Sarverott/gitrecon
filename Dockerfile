# syntax=docker/dockerfile:1
# gitrecon CLI in an image. Debian slim, not Alpine: chromadb needs onnxruntime, which has no musl build.
# Usage: see compose.yaml, or
#   docker build -t gitrecon . && docker run --rm -v "$PWD/data:/data" gitrecon stars sarverott

# Build: resolve the locked dependencies into a virtualenv. The hub extra (map push/pull,
# ~20 MB) is on by default; a CLI-only image: --build-arg EXTRAS=""
FROM python:3.12-slim AS build
ARG EXTRAS="--extra hub"
COPY --from=ghcr.io/astral-sh/uv:0.12 /uv /bin/uv
ENV UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-default-groups $EXTRAS --no-install-project
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-default-groups $EXTRAS --no-editable

# Run: only the virtualenv on a bare Python, as a non-root user.
FROM python:3.12-slim
# git: the clone commands, gitgraph and analyze run it
RUN apt-get update && apt-get install -y --no-install-recommends git \
 && rm -rf /var/lib/apt/lists/* \
 && useradd --create-home --uid 1000 gitrecon && mkdir /data /datasets && chown gitrecon: /data /datasets
COPY --from=build /app/.venv /app/.venv
COPY resources /app/resources
ENV PATH=/app/.venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    GITRECON_DATA=/data GITRECON_DATASETS=/datasets GITRECON_RESOURCES=/app/resources GITRECON_NO_GH_CLI=1
USER gitrecon
WORKDIR /data
ENTRYPOINT ["gitrecon"]
CMD ["--help"]
