"""Cola de ingesta en memoria.

Los archivos subidos no se indexan en la misma request: se guardan en disco
y se encolan para que un unico worker los procese de a uno. Esto evita
disparar varias llamadas concurrentes a la API de embeddings de Gemini (que
tiene cuota limitada) y le da a la interfaz un estado por archivo para
mostrar mientras la ingesta esta en curso.

Estado en memoria: se pierde si el proceso se reinicia (aceptable, es una
cola de trabajo, no un registro persistente).
"""

import asyncio
import logging
import tempfile
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from google.genai.errors import ClientError

from agent.rag.ingest import add_document

logger = logging.getLogger(__name__)

JobStatus = Literal["pending", "processing", "done", "error"]


@dataclass
class IngestJob:
    job_id: str
    filename: str
    tmp_path: Path
    categoria: str | None = None
    status: JobStatus = "pending"
    doc_id: str | None = None
    error: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


_jobs: dict[str, IngestJob] = {}
_queue: asyncio.Queue[str] = asyncio.Queue()
_worker_task: asyncio.Task | None = None


def _uploads_dir() -> Path:
    path = Path(tempfile.gettempdir()) / "larry-rag-uploads"
    path.mkdir(exist_ok=True)
    return path


async def enqueue(filename: str, content: bytes, categoria: str | None = None) -> IngestJob:
    job_id = str(uuid.uuid4())
    job_dir = _uploads_dir() / job_id
    job_dir.mkdir()
    tmp_path = job_dir / filename
    tmp_path.write_bytes(content)

    job = IngestJob(job_id=job_id, filename=filename, tmp_path=tmp_path, categoria=categoria)
    _jobs[job_id] = job
    await _queue.put(job_id)
    _ensure_worker_started()
    return job


def list_jobs() -> list[IngestJob]:
    return sorted(_jobs.values(), key=lambda job: job.created_at)


def _ensure_worker_started() -> None:
    global _worker_task
    if _worker_task is None or _worker_task.done():
        _worker_task = asyncio.create_task(_worker())


async def _worker() -> None:
    while True:
        job_id = await _queue.get()
        job = _jobs.get(job_id)
        if job is None:
            _queue.task_done()
            continue

        job.status = "processing"
        job.updated_at = datetime.now(UTC)
        try:
            job.doc_id = await asyncio.to_thread(add_document, job.tmp_path, job.categoria)
            job.status = "done"
        except ClientError as exc:
            job.status = "error"
            job.error = (
                "Se agoto la cuota de la API de embeddings de Gemini. Intenta de nuevo mas tarde."
                if exc.code == 429
                else f"Error del proveedor de embeddings: {exc.message}"
            )
            logger.warning("Fallo la ingesta de %s: %s", job.filename, job.error)
        except Exception as exc:
            job.status = "error"
            job.error = str(exc)
            logger.exception("Fallo la ingesta de %s", job.filename)
        finally:
            job.updated_at = datetime.now(UTC)
            job.tmp_path.unlink(missing_ok=True)
            job.tmp_path.parent.rmdir()
            _queue.task_done()
