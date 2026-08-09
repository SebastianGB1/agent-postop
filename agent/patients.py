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
