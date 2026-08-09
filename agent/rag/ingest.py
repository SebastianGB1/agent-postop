"""Alta y baja de documentos del RAG.

El id de cada documento es un uuid generado en cada ingesta; el nombre del
archivo se guarda aparte, en metadata["source"], y se usa para localizar y
reemplazar los fragmentos de una ingesta anterior del mismo archivo. Volver
a ingerir un archivo con el mismo nombre reemplaza sus fragmentos anteriores
en ChromaDB; eliminarlo hace que el agente deje de tener acceso a ese
contenido en la siguiente consulta, sin reiniciar ni redesplegar nada.

Uso:
    python -m agent.rag.ingest add ruta/completa/al/archivo.pdf --categoria "total joint replacement"
    python -m agent.rag.ingest add-dir dataset/textos
    python -m agent.rag.ingest remove doc-id-uuid
    python -m agent.rag.ingest list
"""

import argparse
import logging
import uuid
from pathlib import Path

from dotenv import load_dotenv
from llama_index.core import Document, SimpleDirectoryReader, VectorStoreIndex

from agent.rag.categories import CATEGORIAS
from agent.rag.store import (
    ChromaVectorStore,
    get_embed_model,
    get_semantic_splitter,
    get_vector_store,
)

logger = logging.getLogger(__name__)


def add_document(path: Path, categoria: str | None = None) -> str:
    """Ingesta (o reemplaza, si ya existia) un unico archivo en el indice.

    `categoria` etiqueta el documento con su especialidad clinica (ver
    agent/rag/categories.py) para poder filtrar la busqueda por el
    procedimiento del paciente. Sin categoria, el documento solo aparece en
    busquedas sin filtro.

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
    metadata = {"source": source}
    if categoria:
        metadata["categoria"] = categoria
    document = Document(text=text, doc_id=doc_id, metadata=metadata)

    nodes = get_semantic_splitter().get_nodes_from_documents([document])

    index = VectorStoreIndex.from_vector_store(vector_store, embed_model=get_embed_model())
    index.insert_nodes(nodes)
    logger.info(
        "Documento indexado: %s (doc_id=%s, %d chunks semanticos)",
        source,
        doc_id,
        len(nodes),
    )
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


def list_documents() -> list[tuple[str, str, str]]:
    """Devuelve tuplas (doc_id, source, categoria) actualmente indexadas en ChromaDB."""
    collection = get_vector_store()._collection
    records = collection.get(include=["metadatas"])
    metadatas = records.get("metadatas") or []
    documents = {
        (
            str(metadata["document_id"]),
            str(metadata.get("source", "")),
            str(metadata.get("categoria", "")),
        )
        for metadata in metadatas
        if metadata and metadata.get("document_id")
    }
    return sorted(documents, key=lambda item: item[1])


def add_documents_dir(directory: Path) -> None:
    """Ingesta en bloque un directorio con subcarpetas por categoria, replicando
    la estructura de dataset/textos/<categoria>/*.pdf. El nombre de cada
    subcarpeta se usa tal cual como `categoria`."""
    for categoria_dir in sorted(p for p in directory.iterdir() if p.is_dir()):
        categoria = categoria_dir.name
        if categoria not in CATEGORIAS:
            logger.warning(
                "Carpeta '%s' no coincide con ninguna categoria conocida (%s); se "
                "ingesta igual, pero no podra filtrarse por procedimiento.",
                categoria,
                ", ".join(CATEGORIAS),
            )
        for file_path in sorted(categoria_dir.iterdir()):
            if not file_path.is_file():
                continue
            add_document(file_path, categoria=categoria)


def _main() -> None:
    load_dotenv(override=True)
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="Administra los documentos del RAG.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_parser = subparsers.add_parser("add", help="Ingesta o reemplaza un archivo")
    add_parser.add_argument("path", type=Path)
    add_parser.add_argument("--categoria", choices=CATEGORIAS, default=None)

    add_dir_parser = subparsers.add_parser(
        "add-dir",
        help="Ingesta en bloque un directorio con subcarpetas por categoria (ej. dataset/textos)",
    )
    add_dir_parser.add_argument("directory", type=Path)

    remove_parser = subparsers.add_parser("remove", help="Elimina un documento por doc_id")
    remove_parser.add_argument("doc_id")

    subparsers.add_parser("list", help="Lista los documentos indexados")

    args = parser.parse_args()

    if args.command == "add":
        add_document(args.path, categoria=args.categoria)
    elif args.command == "add-dir":
        add_documents_dir(args.directory)
    elif args.command == "remove":
        remove_document(args.doc_id)
    elif args.command == "list":
        for doc_id, source, categoria in list_documents():
            print(f"{doc_id}\t{source}\t{categoria or '(sin categoria)'}")


if __name__ == "__main__":
    _main()
