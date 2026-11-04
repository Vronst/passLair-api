FROM python:3.14.10-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

ENV RUSTUP_HOME=/opt/rustup \
    CARGO_HOME=/opt/cargo
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain stable --no-modify-path
ENV PATH="/opt/cargo/bin:$PATH"

COPY --from=docker.io/astral/uv:latest /uv /uvx /bin/

WORKDIR /app

RUN groupadd --system appgroup && useradd --system --gid appgroup --home-dir /app appuser

COPY pyproject.toml uv.lock ./
COPY . .

RUN chown -R appuser:appgroup /app /opt/rustup /opt/cargo

USER appuser

ENV UV_CACHE_DIR="/app/.uv-cache" \
    HOME="/app"

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8888/').read()" || exit 1

RUN uv sync --frozen --no-dev

CMD ["uv", "run", "gunicorn", "--config", "/app/src/passlair_api/gunicorn_config.py", "passlair_api.app:app"]
