"""Acceso al vector store (ChromaDB) y al modelo de embeddings de Gemini.

El vector store es la unica fuente de verdad del indice: no se persiste nada
en disco local, asi que agregar o eliminar documentos en ChromaDB se refleja
de inmediato en las consultas del agente.
"""

import os

from llama_index.core import VectorStoreIndex
from llama_index.core.node_parser import SemanticSplitterNodeParser
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore

from agent.rag.settings import (
    CHROMA_COLLECTION,
    CHROMA_HOST,
    CHROMA_PORT,
    GEMINI_EMBED_MODEL,
    SEMANTIC_CHUNK_BREAKPOINT_PERCENTILE,
    SEMANTIC_CHUNK_BUFFER_SIZE,
)

_embed_model: GoogleGenAIEmbedding | None = None
_vector_store: ChromaVectorStore | None = None
_semantic_splitter: SemanticSplitterNodeParser | None = None


def get_embed_model() -> GoogleGenAIEmbedding:
    global _embed_model
    if _embed_model is None:
        _embed_model = GoogleGenAIEmbedding(
            model_name=GEMINI_EMBED_MODEL,
            api_key=os.environ["GOOGLE_API_KEY"],
        )
    return _embed_model


def get_semantic_splitter() -> SemanticSplitterNodeParser:
    """Splitter que agrupa oraciones por similitud semantica en vez de por
    tamano fijo, para que cada chunk conserve una idea completa y las
    consultas del RAG recuperen fragmentos mas relevantes."""
    global _semantic_splitter
    if _semantic_splitter is None:
        _semantic_splitter = SemanticSplitterNodeParser(
            embed_model=get_embed_model(),
            buffer_size=SEMANTIC_CHUNK_BUFFER_SIZE,
            breakpoint_percentile_threshold=SEMANTIC_CHUNK_BREAKPOINT_PERCENTILE,
        )
    return _semantic_splitter


def get_vector_store() -> ChromaVectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = ChromaVectorStore(
            collection_name=CHROMA_COLLECTION,
            host=CHROMA_HOST,
            port=CHROMA_PORT,
        )
    return _vector_store


def get_index() -> VectorStoreIndex:
    return VectorStoreIndex.from_vector_store(
        get_vector_store(),
        embed_model=get_embed_model(),
    )
