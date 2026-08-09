"""Conexion a Postgres (servicio "postgres" en docker-compose.yml)."""

import os


def get_dsn() -> str:
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    dbname = os.getenv("POSTGRES_DB", "agent-larry")
    user = os.getenv("POSTGRES_USER", "agent")
    password = os.getenv("POSTGRES_PASSWORD", "devpassword123")
    return f"host={host} port={port} dbname={dbname} user={user} password={password}"
