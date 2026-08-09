"""Endpoint de solo lectura para los resumenes de llamada que escribe el agente.

El agente (agent/decision.py) inserta en resumenes_llamada directamente por
Postgres durante la llamada; este router solo lee esa misma tabla para la
consola de administracion, sin ningun acoplamiento HTTP entre los dos
procesos (bot en :7860, API admin en :8000).
"""

import logging
from datetime import datetime

import psycopg
from fastapi import APIRouter
from pydantic import BaseModel

from api.db.connection import get_dsn

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/summaries", tags=["summaries"])


class CallSummary(BaseModel):
    resumen_id: str
    paciente_id: str | None
    nombre_paciente: str | None
    procedimiento: str | None
    clasificacion: str
    escalado: bool
    sintomas_reportados: str | None
    justificacion: str | None
    siguientes_pasos: str | None
    referencias_usadas: list[dict]
    creado_ts: datetime


@router.get("", response_model=list[CallSummary])
def list_summaries() -> list[CallSummary]:
    with psycopg.connect(get_dsn()) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT resumen_id, paciente_id, nombre_paciente, procedimiento,
                   clasificacion, escalado, sintomas_reportados, justificacion,
                   siguientes_pasos, referencias_usadas, creado_ts
            FROM resumenes_llamada
            ORDER BY creado_ts DESC
            """
        )
        columns = [desc.name for desc in cur.description]
        return [CallSummary(**dict(zip(columns, row))) for row in cur.fetchall()]
