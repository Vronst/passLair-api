FROM python:3.14.10-slim-bookworm

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY --from=docker.io/astral/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml ./

COPY uv.lock ./

ENV SECRET_KEY="YouToughtIWouldPushItXD?" DATABASE="sqlite" DEK="" REDIS_HOST="redis"

COPY . .

RUN uv sync --frozen --no-dev

RUN groupadd -r appuser && useradd -r -g appuser appuser \
    && chown -R appuser:appuser /app

# 2. Switch to the non-root user
USER appuser

# 3. Add a healthcheck instruction (CKV_DOCKER_2)
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8888/').read()" || exit 1

CMD ["uv", "run", "gunicorn", "--config", "/app/src/passlair_api/gunicorn_config.py", "passlair_api.app:app"]
