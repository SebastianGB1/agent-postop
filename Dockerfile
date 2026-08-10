# Imagen unica para las dos superficies (consola API y agente de voz): comparten
# el mismo entorno de dependencias, solo cambia el comando (ver docker-compose.yml).
FROM python:3.13-slim

# libgomp1: requerido en runtime por onnxruntime (kokoro-onnx, silero VAD).
# curl: usado por los healthchecks de docker-compose.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

# Capa de dependencias separada del codigo para aprovechar la cache de docker.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-install-project

COPY . .
RUN uv sync --locked

ENV PATH="/app/.venv/bin:$PATH"
