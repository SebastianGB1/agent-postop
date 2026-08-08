"""Alta y baja de documentos del RAG.

El id de cada documento es un uuid generado en cada ingesta; el nombre del
archivo se guarda aparte, en metadata["source"], y se usa para localizar y
reemplazar los fragmentos de una ingesta anterior del mismo archivo. Volver
a ingerir un archivo con el mismo nombre reemplaza sus fragmentos anteriores
en ChromaDB; eliminarlo hace que el agente deje de tener acceso a ese
contenido en la siguiente consulta, sin reiniciar ni redesplegar nada.

Uso:
    python -m agent.rag.ingest add ruta/completa/al/archivo.pdf
    python -m agent.rag.ingest remove doc-id-uuid
    python -m agent.rag.ingest list
"""

import argparse
import logging
import uuid
from pathlib import Path

from dotenv import load_dotenv
from llama_index.core import Document, SimpleDirectoryReader, VectorStoreIndex

from agent.rag.store import ChromaVectorStore, get_embed_model, get_vector_store

logger = logging.getLogger(__name__)


def add_document(path: Path) -> str:
    """Ingesta (o reemplaza, si ya existia) un unico archivo en el indice.

    Devuelve el doc_id (uuid) asignado a la ingesta.
    """
    source = path.name

    docs = SimpleDirectoryReader(input_files=[str(path)]).load_data()
    if not docs:
        logger.warning("No se pudo leer contenido de %s", path)
        return ""
    text = "\n\n".join(d.text for d in docs)

    vector_store = get_vector_store()
    _delete_by_source(vector_store, source)

    doc_id = str(uuid.uuid4())
    document = Document(text=text, doc_id=doc_id, metadata={"source": source})

    index = VectorStoreIndex.from_vector_store(vector_store, embed_model=get_embed_model())
    index.insert(document)
    logger.info("Documento indexado: %s (doc_id=%s)", source, doc_id)
    return doc_id


def _delete_by_source(vector_store: ChromaVectorStore, source: str) -> None:
    """Elimina los fragmentos de cualquier ingesta previa del mismo archivo."""
    collection = vector_store._collection
    records = collection.get(where={"source": source}, include=["metadatas"])
    doc_ids = {
        str(metadata["document_id"])
        for metadata in records.get("metadatas") or []
        if metadata and metadata.get("document_id")
    }
    for doc_id in doc_ids:
        vector_store.delete(ref_doc_id=doc_id)


def remove_document(doc_id: str) -> None:
    """Elimina todos los fragmentos de un documento del indice, por su doc_id."""
    get_vector_store().delete(ref_doc_id=doc_id)
    logger.info("Documento eliminado del indice: %s", doc_id)


def list_documents() -> list[tuple[str, str]]:
    """Devuelve pares (doc_id, source) actualmente indexados en ChromaDB."""
    collection = get_vector_store()._collection
    records = collection.get(include=["metadatas"])
    metadatas = records.get("metadatas") or []
    documents = {
        (str(metadata["document_id"]), str(metadata.get("source", "")))
        for metadata in metadatas
        if metadata and metadata.get("document_id")
    }
    return sorted(documents, key=lambda item: item[1])


def _main() -> None:
    load_dotenv(override=True)
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="Administra los documentos del RAG.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_parser = subparsers.add_parser("add", help="Ingesta o reemplaza un archivo")
    add_parser.add_argument("path", type=Path)

    remove_parser = subparsers.add_parser("remove", help="Elimina un documento por doc_id")
    remove_parser.add_argument("doc_id")

    subparsers.add_parser("list", help="Lista los documentos indexados")

    args = parser.parse_args()

    if args.command == "add":
        add_document(args.path)
    elif args.command == "remove":
        remove_document(args.doc_id)
    elif args.command == "list":
        for doc_id, source in list_documents():
            print(f"{doc_id}\t{source}")


if __name__ == "__main__":
    _main()
