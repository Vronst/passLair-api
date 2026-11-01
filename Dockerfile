FROM python:3.14.10-slim-bookworm

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY --from=docker.io/astral/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml ./

COPY uv.lock ./

ENV SECRET_KEY="YouToughtIWouldPushItXD?" DATABASE="sqlite" DEK=""

COPY . .

RUN uv sync --frozen --no-dev

CMD ["uv", "run", "gunicorn", "--config", "/app/src/passlair_api/gunicorn_config.py", "passlair_api.app:app"]
