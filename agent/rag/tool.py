"""Function tool que expone el RAG al LLM de la conversacion.

El LLM decide cuando llamar a esta funcion durante la charla con el
paciente; el handler recupera los fragmentos mas relevantes de ChromaDB
(embeddings de Gemini) y se los devuelve como texto para que el LLM
elabore la respuesta hablada.
"""

import logging

from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.services.llm_service import FunctionCallParams

from agent.rag.settings import RAG_TOP_K
from agent.rag.store import get_index

logger = logging.getLogger(__name__)


def build_knowledge_base_tool(referencias_usadas: list[dict]) -> FunctionSchema:
    """Crea el tool de RAG para una llamada especifica.

    `referencias_usadas` se llena con cada fuente recuperada durante la
    llamada, para que el resumen final (agent/decision.py) pueda adjuntar
    referencias verificables en vez de depender de que el LLM las recuerde.
    """

    async def _buscar_en_base_de_conocimiento(params: FunctionCallParams) -> None:
        consulta = params.arguments.get("consulta", "")

        retriever = get_index().as_retriever(similarity_top_k=RAG_TOP_K)
        nodes = await retriever.aretrieve(consulta)

        if not nodes:
            await params.result_callback(
                "No se encontro informacion relevante en la base de conocimiento."
            )
            return

        fragmentos = []
        fuentes_vistas = {r["fuente"] for r in referencias_usadas}
        for node in nodes:
            fuente = node.metadata.get("source", node.node_id)
            fragmentos.append(f"[{fuente}] {node.get_content()}")
            if fuente not in fuentes_vistas:
                fuentes_vistas.add(fuente)
                referencias_usadas.append({"fuente": fuente, "consulta": consulta})

        await params.result_callback("\n\n".join(fragmentos))

    return FunctionSchema(
        name="buscar_en_base_de_conocimiento",
        description=(
            "Busca informacion en la base de conocimiento post operatoria (guias, "
            "indicaciones y documentos cargados por el equipo clinico). Usala antes "
            "de responder preguntas sobre cuidados, sintomas o instrucciones que no "
            "esten ya presentes en la conversacion."
        ),
        properties={
            "consulta": {
                "type": "string",
                "description": "Pregunta o tema a buscar, en espanol, tal como lo pregunta el usuario.",
            }
        },
        required=["consulta"],
        handler=_buscar_en_base_de_conocimiento,
    )
