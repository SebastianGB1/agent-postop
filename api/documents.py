"""Endpoints para administrar los documentos indexados en ChromaDB.

Reutiliza las funciones de alta/baja de agent.rag.ingest para mantener una
unica implementacion de la logica de indexado; este modulo solo agrega la
capa HTTP (listar con detalle, ver contenido, subir archivo, eliminar).
"""

import logging
import tempfile
from pathlib import Path

from chromadb.api.types import GetResult
from fastapi import APIRouter, HTTPException, UploadFile
from google.genai.errors import ClientError
from pydantic import BaseModel

from agent.rag.ingest import add_document, remove_document
from agent.rag.store import get_vector_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/documents", tags=["documents"])


class Chunk(BaseModel):
    node_id: str
    text: str


class DocumentSummary(BaseModel):
    doc_id: str
    filename: str
    chunk_count: int


class DocumentDetail(BaseModel):
    doc_id: str
    filename: str
    chunks: list[Chunk]


def _collection_records() -> GetResult:
    collection = get_vector_store()._collection
    return collection.get(include=["metadatas", "documents"])


@router.get("", response_model=list[DocumentSummary])
def list_documents() -> list[DocumentSummary]:
    records = _collection_records()
    metadatas = records.get("metadatas") or []

    counts: dict[str, int] = {}
    filenames: dict[str, str] = {}
    for metadata in metadatas:
        doc_id = metadata.get("document_id") if metadata else None
        if not doc_id:
            continue
        doc_id = str(doc_id)
        counts[doc_id] = counts.get(doc_id, 0) + 1
        filenames.setdefault(doc_id, str(metadata.get("source", "")))

    return [
        DocumentSummary(doc_id=doc_id, filename=filenames[doc_id], chunk_count=count)
        for doc_id, count in sorted(counts.items(), key=lambda item: filenames[item[0]])
    ]


@router.get("/{doc_id}", response_model=DocumentDetail)
def get_document(doc_id: str) -> DocumentDetail:
    records = _collection_records()
    ids = records.get("ids") or []
    metadatas = records.get("metadatas") or []
    texts = records.get("documents") or []

    chunks: list[Chunk] = []
    filename = ""
    for node_id, metadata, text in zip(ids, metadatas, texts):
        if metadata and metadata.get("document_id") == doc_id:
            chunks.append(Chunk(node_id=node_id, text=text or ""))
            filename = str(metadata.get("source", filename))

    if not chunks:
        raise HTTPException(status_code=404, detail=f"Documento '{doc_id}' no encontrado")

    return DocumentDetail(doc_id=doc_id, filename=filename, chunks=chunks)


@router.post("", response_model=DocumentSummary, status_code=201)
async def upload_document(file: UploadFile) -> DocumentSummary:
    if not file.filename:
        raise HTTPException(status_code=400, detail="El archivo debe tener un nombre")

    filename = file.filename
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir) / filename
        tmp_path.write_bytes(await file.read())
        try:
            doc_id = add_document(tmp_path)
        except ClientError as exc:
            if exc.code == 429:
                logger.warning("Cuota de embeddings de Gemini agotada al indexar %s", filename)
                raise HTTPException(
                    status_code=429,
                    detail=(
                        "Se agoto la cuota de la API de embeddings de Gemini "
                        "(aiplatform.googleapis.com). Intenta de nuevo mas tarde o "
                        "solicita un aumento de cuota en Google Cloud."
                    ),
                ) from exc
            raise HTTPException(status_code=502, detail=f"Error del proveedor de embeddings: {exc.message}") from exc

    records = _collection_records()
    metadatas = records.get("metadatas") or []
    chunk_count = sum(
        1 for metadata in metadatas if metadata and metadata.get("document_id") == doc_id
    )
    return DocumentSummary(doc_id=doc_id, filename=filename, chunk_count=chunk_count)


@router.delete("/{doc_id}", status_code=204)
def delete_document(doc_id: str) -> None:
    remove_document(doc_id)
