"""Acceso de solo lectura a los pacientes cargados en Postgres.

Los datos los puebla api/db/seed_dataset.py a partir de dataset/. Este modulo
los expone para la consola de llamada: la lista para el selector de paciente
y el contexto clinico basico que el agente usa para personalizar el saludo.
"""

import psycopg

from api.db.connection import get_dsn


def list_patients() -> list[dict]:
    with psycopg.connect(get_dsn()) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT paciente_id, nombre_completo FROM pacientes_demografia "
            "ORDER BY nombre_completo"
        )
        return [{"paciente_id": row[0], "nombre_completo": row[1]} for row in cur.fetchall()]


def get_patient_context(paciente_id: str) -> dict | None:
    with psycopg.connect(get_dsn()) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT d.nombre_completo, c.procedimiento, c.edad
            FROM pacientes_demografia d
            JOIN perfiles_clinicos c USING (paciente_id)
            WHERE d.paciente_id = %s
            """,
            (paciente_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        nombre_completo, procedimiento, edad = row
        return {"nombre_completo": nombre_completo, "procedimiento": procedimiento, "edad": edad}


def get_medical_history(paciente_id: str) -> dict | None:
    """Perfil clinico basal del paciente mas sus llamadas de seguimiento previas.

    No incluye trayectorias_postop: esos datos son el cuadro clinico que el
    paciente esta viviendo en esta llamada, y el agente solo puede averiguarlo
    conversando, no leyendolo de la base de datos.
    """
    with psycopg.connect(get_dsn()) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT procedimiento, fecha_cirugia, edad, genero, comorbilidades,
                   complicacion_encounter
            FROM perfiles_clinicos
            WHERE paciente_id = %s
            """,
            (paciente_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        procedimiento, fecha_cirugia, edad, genero, comorbilidades, complicacion_encounter = row

        cur.execute(
            """
            SELECT clasificacion, sintomas_reportados, justificacion, siguientes_pasos, creado_ts
            FROM resumenes_llamada
            WHERE paciente_id = %s
            ORDER BY creado_ts DESC
            LIMIT 5
            """,
            (paciente_id,),
        )
        llamadas_previas = [
            {
                "clasificacion": clasificacion,
                "sintomas_reportados": sintomas_reportados,
                "justificacion": justificacion,
                "siguientes_pasos": siguientes_pasos,
                "creado_ts": creado_ts,
            }
            for clasificacion, sintomas_reportados, justificacion, siguientes_pasos, creado_ts in cur.fetchall()
        ]

        return {
            "procedimiento": procedimiento,
            "fecha_cirugia": fecha_cirugia,
            "edad": edad,
            "genero": genero,
            "comorbilidades": comorbilidades or [],
            "complicacion_encounter": bool(complicacion_encounter),
            "llamadas_previas": llamadas_previas,
        }
