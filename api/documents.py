"""Endpoints para administrar los documentos indexados en ChromaDB.

Reutiliza las funciones de alta/baja de agent.rag.ingest para mantener una
unica implementacion de la logica de indexado; este modulo solo agrega la
capa HTTP (listar con detalle, ver contenido, subir archivos, eliminar) y la
cola de ingesta (api.jobs) para procesar varios archivos de a uno.
"""

import logging

from chromadb.api.types import GetResult
from fastapi import APIRouter, HTTPException, UploadFile
from pydantic import BaseModel

from agent.rag.ingest import remove_document
from agent.rag.store import get_vector_store
from api.jobs import IngestJob, enqueue, list_jobs

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


class JobStatus(BaseModel):
    job_id: str
    filename: str
    status: str
    doc_id: str | None = None
    error: str | None = None


def _to_job_status(job: IngestJob) -> JobStatus:
    return JobStatus(
        job_id=job.job_id,
        filename=job.filename,
        status=job.status,
        doc_id=job.doc_id,
        error=job.error,
    )


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


@router.post("/uploads", response_model=list[JobStatus], status_code=202)
async def upload_documents(files: list[UploadFile]) -> list[JobStatus]:
    """Encola uno o varios archivos para indexarlos de a uno en segundo plano."""
    if not files:
        raise HTTPException(status_code=400, detail="Debes subir al menos un archivo")

    jobs = []
    for file in files:
        if not file.filename:
            raise HTTPException(status_code=400, detail="Cada archivo debe tener un nombre")
        content = await file.read()
        jobs.append(await enqueue(file.filename, content))

    return [_to_job_status(job) for job in jobs]


@router.get("/uploads", response_model=list[JobStatus])
def get_uploads() -> list[JobStatus]:
    """Estado de la cola de ingesta: pendiente, procesando, listo o error."""
    return [_to_job_status(job) for job in list_jobs()]


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


@router.delete("/{doc_id}", status_code=204)
def delete_document(doc_id: str) -> None:
    remove_document(doc_id)
