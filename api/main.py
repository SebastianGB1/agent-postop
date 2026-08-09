"""API FastAPI para administrar y visualizar los documentos indexados en ChromaDB.

Uso:
    uv run uvicorn api.main:app --reload
    # abre http://localhost:8000
"""

import logging
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from api.documents import router as documents_router
from api.summaries import router as summaries_router

load_dotenv(override=True)
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Larry RAG - Documentos", version="0.1.0")
app.include_router(documents_router)
app.include_router(summaries_router)

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
