"""Configuracion del RAG: conexion a ChromaDB y modelo de embeddings de Gemini."""

import os

CHROMA_HOST = os.environ.get("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.environ.get("CHROMA_PORT", "8001"))
CHROMA_COLLECTION = os.environ.get("CHROMA_COLLECTION", "post_operatorio")

GEMINI_EMBED_MODEL = os.environ.get("GEMINI_EMBED_MODEL", "gemini-embedding-2")

RAG_TOP_K = int(os.environ.get("RAG_TOP_K", "4"))

# Chunking semantico: agrupa oraciones consecutivas mientras su embedding sea
# similar, y corta cuando la diferencia de similitud supera el percentil
# configurado (a mayor percentil, cortes menos frecuentes -> chunks mas grandes).
SEMANTIC_CHUNK_BUFFER_SIZE = int(os.environ.get("SEMANTIC_CHUNK_BUFFER_SIZE", "1"))
SEMANTIC_CHUNK_BREAKPOINT_PERCENTILE = int(
    os.environ.get("SEMANTIC_CHUNK_BREAKPOINT_PERCENTILE", "95")
)
