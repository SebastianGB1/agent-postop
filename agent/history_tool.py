"""Function tool que expone el historial medico del paciente al LLM.

Solo trae el perfil clinico basal (procedimiento, comorbilidades,
complicaciones registradas) y el resultado de sus llamadas de seguimiento
previas (agent/patients.py). Nunca expone trayectorias_postop: ese es el
cuadro clinico que el paciente esta viviendo en la llamada actual, y el
agente solo puede averiguarlo conversando, no leyendolo de la base de datos.
"""

import logging

from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.services.llm_service import FunctionCallParams

from agent.patients import get_medical_history

logger = logging.getLogger(__name__)


def _formatear_historial(historial: dict) -> str:
    partes = [
        f"Procedimiento: {historial['procedimiento']} (cirugia: {historial['fecha_cirugia']}).",
        f"Edad: {historial['edad']}. Genero: {historial['genero']}.",
    ]

    comorbilidades = historial["comorbilidades"]
    if comorbilidades:
        partes.append(f"Comorbilidades: {', '.join(comorbilidades)}.")
    else:
        partes.append("Sin comorbilidades registradas.")

    if historial["complicacion_encounter"]:
        partes.append("Tiene una complicacion registrada en su atencion medica.")

    llamadas_previas = historial["llamadas_previas"]
    if llamadas_previas:
        partes.append("Llamadas de seguimiento previas (mas reciente primero):")
        for llamada in llamadas_previas:
            partes.append(
                f"- {llamada['creado_ts']}: clasificacion {llamada['clasificacion']}. "
                f"Sintomas: {llamada['sintomas_reportados'] or '—'}. "
                f"Justificacion: {llamada['justificacion'] or '—'}."
            )
    else:
        partes.append("No hay llamadas de seguimiento previas registradas.")

    return "\n".join(partes)


def build_historial_medico_tool(paciente_id: str | None) -> FunctionSchema:
    """Crea el tool de historial medico para una llamada especifica.

    `paciente_id` se resuelve una vez al iniciar la llamada (agent/agent.py);
    la tool no recibe argumentos porque siempre consulta al paciente actual.
    """

    async def _consultar_historial_medico(params: FunctionCallParams) -> None:
        if not paciente_id:
            await params.result_callback(
                "No hay un paciente identificado en esta llamada, asi que no hay "
                "historial medico para consultar."
            )
            return

        historial = get_medical_history(paciente_id)
        if not historial:
            await params.result_callback(
                "No se encontro historial medico registrado para este paciente."
            )
            return

        await params.result_callback(_formatear_historial(historial))

    return FunctionSchema(
        name="consultar_historial_medico",
        description=(
            "Consulta el perfil clinico basal del paciente actual (procedimiento, "
            "comorbilidades, complicaciones registradas) y el resultado de sus "
            "llamadas de seguimiento previas. Usala al inicio de la llamada o "
            "cuando necesites contexto sobre su condicion de base antes de "
            "evaluar los sintomas nuevos que reporte -por ejemplo, para saber si "
            "una comorbilidad o una clasificacion previa cambia como interpretas "
            "lo que dice ahora."
        ),
        properties={},
        required=[],
        handler=_consultar_historial_medico,
    )
