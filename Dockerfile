# ─── local-commit — Docker image ──────────────────────────────────────────
# Usage:
#   docker build -t local-commit .
#
#   # Download model (one-time, persists in volume)
#   docker run --rm -v local-commit-model:/root/.local-commit \
#     local-commit --setup
#
#   # Run in current directory
#   docker run --rm -v local-commit-model:/root/.local-commit \
#     -v "$(pwd):/repo" -w /repo local-commit
#
#   # Alias for daily use:
#   alias lc='docker run --rm -v local-commit-model:/root/.local-commit \
#     -v "$(pwd):/repo" -w /repo local-commit'
# ────────────────────────────────────────────────────────────────────────────

FROM python:3.11-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY . /build
WORKDIR /build
RUN pip install --no-cache-dir build && python -m build --wheel

# ─── Runtime ────────────────────────────────────────────────────────────────
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /build/dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl && rm /tmp/*.whl

# Pre-built CPU wheel for llama-cpp-python (no compilation at install time)
RUN pip install --no-cache-dir \
    --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu \
    "llama-cpp-python>=0.2.0"

ENTRYPOINT ["local-commit"]
CMD ["--help"]
