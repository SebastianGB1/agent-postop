"""Clasificacion de criticidad y resumen estructurado de la llamada.

El LLM decide durante la conversacion cuando tiene informacion suficiente
para clasificar al paciente (verde/amarillo/rojo) y llama a
`registrar_resumen_llamada`. El handler persiste el resumen en Postgres
-mismo patron de acceso directo que agent/patients.py- adjuntando las
referencias del RAG acumuladas durante la llamada (agent/rag/tool.py), para
que el registro no dependa de que el LLM las recuerde bien.
"""

import logging

import psycopg
from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.services.llm_service import FunctionCallParams
from psycopg.types.json import Json

from api.db.connection import get_dsn

logger = logging.getLogger(__name__)

CLASIFICACIONES = ("verde", "amarillo", "rojo", "sin_clasificar")


def save_call_summary(
    *,
    resumen_id: str,
    paciente_id: str | None,
    nombre_paciente: str | None,
    procedimiento: str | None,
    clasificacion: str,
    sintomas_reportados: str | None,
    justificacion: str | None,
    siguientes_pasos: str | None,
    referencias_usadas: list[dict],
) -> None:
    with psycopg.connect(get_dsn()) as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO resumenes_llamada (
                resumen_id, paciente_id, nombre_paciente, procedimiento,
                clasificacion, escalado, sintomas_reportados, justificacion,
                siguientes_pasos, referencias_usadas
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (resumen_id) DO UPDATE SET
                clasificacion = EXCLUDED.clasificacion,
                escalado = EXCLUDED.escalado,
                sintomas_reportados = EXCLUDED.sintomas_reportados,
                justificacion = EXCLUDED.justificacion,
                siguientes_pasos = EXCLUDED.siguientes_pasos,
                referencias_usadas = EXCLUDED.referencias_usadas
            """,
            (
                resumen_id,
                paciente_id,
                nombre_paciente,
                procedimiento,
                clasificacion,
                clasificacion == "rojo",
                sintomas_reportados,
                justificacion,
                siguientes_pasos,
                Json(referencias_usadas),
            ),
        )
        conn.commit()


def build_registrar_resumen_tool(
    *,
    paciente_id: str | None,
    patient: dict | None,
    resumen_id: str,
    referencias_usadas: list[dict],
    call_state: dict,
) -> FunctionSchema:
    async def _registrar_resumen_llamada(params: FunctionCallParams) -> None:
        clasificacion = params.arguments.get("clasificacion", "")
        if clasificacion not in CLASIFICACIONES:
            await params.result_callback(
                f"Clasificacion invalida '{clasificacion}'. Debe ser una de: "
                f"{', '.join(CLASIFICACIONES)}."
            )
            return

        sintomas_reportados = params.arguments.get("sintomas_reportados", "")
        justificacion = params.arguments.get("justificacion", "")
        siguientes_pasos = params.arguments.get("siguientes_pasos", "")

        save_call_summary(
            resumen_id=resumen_id,
            paciente_id=paciente_id if patient else None,
            nombre_paciente=patient["nombre_completo"] if patient else None,
            procedimiento=patient["procedimiento"] if patient else None,
            clasificacion=clasificacion,
            sintomas_reportados=sintomas_reportados,
            justificacion=justificacion,
            siguientes_pasos=siguientes_pasos,
            referencias_usadas=referencias_usadas,
        )
        call_state["registrado"] = True
        logger.info(
            "Resumen de llamada registrado: resumen_id=%s clasificacion=%s", resumen_id, clasificacion
        )

        if clasificacion == "rojo":
            await params.result_callback(
                "Resumen guardado y escalado. Ahora dile con calma y claridad al paciente "
                "que, por los sintomas reportados, personal medico se va a poner en "
                "contacto con el de forma prioritaria. No minimices el sintoma ni lo "
                "tranquilices de mas."
            )
        elif clasificacion == "sin_clasificar":
            await params.result_callback(
                "Resumen guardado sin clasificar por falta de fuentes que respalden una "
                "decision. Dile al paciente con honestidad que no tienes informacion "
                "suficiente para evaluar bien su caso, y recomiendale contactar "
                "directamente a su equipo medico si el sintoma le preocupa."
            )
        else:
            await params.result_callback("Resumen guardado. Puedes continuar o cerrar la llamada.")

    return FunctionSchema(
        name="registrar_resumen_llamada",
        description=(
            "Registra la clasificacion de criticidad del paciente al cierre de la "
            "llamada de seguimiento postoperatorio. Llamala exactamente una vez, "
            "cuando ya tengas informacion suficiente sobre los sintomas del paciente "
            "-normalmente cerca del cierre de la conversacion- y antes de despedirte."
        ),
        properties={
            "clasificacion": {
                "type": "string",
                "enum": list(CLASIFICACIONES),
                "description": (
                    "verde: sin senales de alarma, recuperacion normal. amarillo: "
                    "sintomas que ameritan vigilancia pero no son de emergencia. rojo: "
                    "senales de alarma que requieren atencion medica urgente. Ante "
                    "ambigüedad o duda entre dos niveles, elige el mas alto. "
                    "sin_clasificar: usala unicamente cuando buscaste en la base de "
                    "conocimiento y no encontraste fuentes que respalden ninguna de las "
                    "tres clasificaciones anteriores para los sintomas reportados -nunca "
                    "elijas verde, amarillo o rojo sin una fuente que lo sustente."
                ),
            },
            "sintomas_reportados": {
                "type": "string",
                "description": "Resumen breve, en espanol, de los sintomas que reporto el paciente.",
            },
            "justificacion": {
                "type": "string",
                "description": (
                    "Por que se eligio esa clasificacion, en 1-2 frases, citando la guia "
                    "clinica consultada. Si es sin_clasificar, explica que no se encontro "
                    "informacion en la base de conocimiento para respaldar una decision."
                ),
            },
            "siguientes_pasos": {
                "type": "string",
                "description": "Que se le comunico al paciente que va a pasar despues de la llamada.",
            },
        },
        required=["clasificacion", "sintomas_reportados", "justificacion", "siguientes_pasos"],
        handler=_registrar_resumen_llamada,
    )
