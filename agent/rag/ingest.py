"""Alta y baja de documentos del RAG.

El id de cada documento es el nombre de su archivo. Volver a ingerir un
archivo con el mismo nombre reemplaza sus fragmentos anteriores en ChromaDB;
eliminarlo hace que el agente deje de tener acceso a ese contenido en la
siguiente consulta, sin reiniciar ni redesplegar nada.

Uso:
    python -m agent.rag.ingest add ruta/completa/al/archivo.pdf
    python -m agent.rag.ingest remove nombre-del-archivo.pdf
    python -m agent.rag.ingest list
"""

import argparse
import logging
from pathlib import Path

from dotenv import load_dotenv
from llama_index.core import Document, SimpleDirectoryReader, VectorStoreIndex

from agent.rag.store import get_embed_model, get_vector_store

logger = logging.getLogger(__name__)


def add_document(path: Path) -> None:
    """Ingesta (o reemplaza, si ya existia) un unico archivo en el indice."""
    doc_id = path.name

    docs = SimpleDirectoryReader(input_files=[str(path)]).load_data()
    if not docs:
        logger.warning("No se pudo leer contenido de %s", path)
        return
    text = "\n\n".join(d.text for d in docs)
    document = Document(text=text, doc_id=doc_id, metadata={"source": doc_id})

    vector_store = get_vector_store()
    vector_store.delete(ref_doc_id=doc_id)

    index = VectorStoreIndex.from_vector_store(vector_store, embed_model=get_embed_model())
    index.insert(document)
    logger.info("Documento indexado: %s", doc_id)


def remove_document(doc_id: str) -> None:
    """Elimina todos los fragmentos de un documento del indice."""
    get_vector_store().delete(ref_doc_id=doc_id)
    logger.info("Documento eliminado del indice: %s", doc_id)


def list_documents() -> list[str]:
    """Devuelve los doc_id actualmente indexados en ChromaDB."""
    collection = get_vector_store()._collection
    records = collection.get(include=["metadatas"])
    metadatas = records.get("metadatas") or []
    doc_ids = {
        str(metadata["document_id"]) for metadata in metadatas if metadata and metadata.get("document_id")
    }
    return sorted(doc_ids)


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
        for doc_id in list_documents():
            print(doc_id)


if __name__ == "__main__":
    _main()
