"""Configuracion del RAG: conexion a ChromaDB y modelo de embeddings de Gemini."""

import os

CHROMA_HOST = os.environ.get("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.environ.get("CHROMA_PORT", "8001"))
CHROMA_COLLECTION = os.environ.get("CHROMA_COLLECTION", "post_operatorio")

GEMINI_EMBED_MODEL = os.environ.get("GEMINI_EMBED_MODEL", "gemini-embedding-2-preview")

RAG_TOP_K = int(os.environ.get("RAG_TOP_K", "4"))
