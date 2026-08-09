"""Carga los cuatro archivos de dataset/ en Postgres.

Aplica las migraciones (api/db/migrations/*.sql, en orden) y luego puebla las
tablas en orden de dependencia: pacientes_demografia -> perfiles_clinicos ->
trayectorias_postop -> conversaciones_turnos. Es idempotente: trunca las
tablas antes de insertar, asi que se puede correr varias veces.

Uso:
    uv run python -m api.db.seed_dataset
"""

import json
import logging
import math
from pathlib import Path

import pandas as pd
import psycopg
from dotenv import load_dotenv
from psycopg.types.json import Json

from api.db.connection import get_dsn

logger = logging.getLogger(__name__)

DATASET_DIR = Path(__file__).resolve().parents[2] / "dataset"
MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


def _clean(value):
    """Convierte valores de pandas (NaN/NaT/numpy) a tipos nativos de Python."""
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if pd.isna(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    if hasattr(value, "item"):  # numpy int64/float64/bool_
        return value.item()
    return value


def _json_field(value):
    value = _clean(value)
    if value is None:
        return None
    return Json(json.loads(value))


def _read_sheet(filename: str) -> pd.DataFrame:
    return pd.read_excel(DATASET_DIR / filename, sheet_name="result")


def _apply_migrations(cur: psycopg.Cursor) -> None:
    for migration in sorted(MIGRATIONS_DIR.glob("*.sql")):
        cur.execute(migration.read_text(encoding="utf-8"))


def _load_pacientes_demografia(cur: psycopg.Cursor) -> int:
    df = _read_sheet("perfiles_pacientes_co.xlsx")
    rows = [
        (
            r.paciente_id,
            r.nombre_completo,
            r.direccion,
            r.ciudad,
            r.departamento,
            _clean(r.documento_cc),
            r.eps,
            r.source_country,
            r.adapted_country,
            _json_field(r.adaptation_fields),
            _clean(r.adaptation_ts),
        )
        for r in df.itertuples(index=False)
    ]
    cur.executemany(
        """
        INSERT INTO pacientes_demografia (
            paciente_id, nombre_completo, direccion, ciudad, departamento,
            documento_cc, eps, source_country, adapted_country,
            adaptation_fields, adaptation_ts
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        rows,
    )
    return len(rows)


def _load_perfiles_clinicos(cur: psycopg.Cursor) -> int:
    df = _read_sheet("perfiles_clinicos_pacientes_silver_contest.xlsx")
    rows = [
        (
            r.paciente_id,
            r.bundle_id,
            r.synthea_runtime,
            r.modulo_synthea,
            r.procedimiento,
            _clean(r.fecha_cirugia).date() if _clean(r.fecha_cirugia) else None,
            _clean(r.edad),
            r.genero,
            _json_field(r.comorbilidades),
            _clean(r.complicacion_encounter),
            _clean(r.generado_ts),
        )
        for r in df.itertuples(index=False)
    ]
    cur.executemany(
        """
        INSERT INTO perfiles_clinicos (
            paciente_id, bundle_id, synthea_runtime, modulo_synthea,
            procedimiento, fecha_cirugia, edad, genero, comorbilidades,
            complicacion_encounter, generado_ts
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        rows,
    )
    return len(rows)


def _load_trayectorias(cur: psycopg.Cursor) -> int:
    df = _read_sheet("trayectorias_postop_silver.xlsx")
    rows = [
        (
            r.trayectoria_id,
            r.paciente_id,
            _clean(r.dia_postop),
            r.arquetipo_trayectoria,
            _clean(r.dolor_nrs),
            _clean(r.fiebre_c),
            r.movilidad,
            r.herida,
            r.apetito,
            r.sueno,
            _clean(r.seed),
            _clean(r.generado_ts),
        )
        for r in df.itertuples(index=False)
    ]
    cur.executemany(
        """
        INSERT INTO trayectorias_postop (
            trayectoria_id, paciente_id, dia_postop, arquetipo_trayectoria,
            dolor_nrs, fiebre_c, movilidad, herida, apetito, sueno, seed,
            generado_ts
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        rows,
    )
    return len(rows)


def _load_conversaciones(cur: psycopg.Cursor) -> int:
    df = _read_sheet("dataset_final.xlsx")
    rows = [
        (
            r.dialogo_id,
            r.caso_id,
            r.caso_id.removeprefix("caso_"),
            r.paciente_id,
            _clean(r.dia_postop),
            _clean(r.turno_idx),
            r.hablante,
            r.texto,
            r.label_ground_truth,
            r.estilo_paciente,
            r.modelo_paciente,
            r.modelo_agente,
            r.capa,
            _clean(r.generado_ts),
        )
        for r in df.itertuples(index=False)
    ]
    cur.executemany(
        """
        INSERT INTO conversaciones_turnos (
            dialogo_id, caso_id, trayectoria_id, paciente_id, dia_postop,
            turno_idx, hablante, texto, label_ground_truth, estilo_paciente,
            modelo_paciente, modelo_agente, capa, generado_ts
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        rows,
    )
    return len(rows)


def main() -> None:
    load_dotenv(override=True)
    logging.basicConfig(level=logging.INFO)

    with psycopg.connect(get_dsn(), autocommit=False) as conn:
        with conn.cursor() as cur:
            _apply_migrations(cur)
            cur.execute(
                "TRUNCATE conversaciones_turnos, trayectorias_postop, "
                "perfiles_clinicos, pacientes_demografia RESTART IDENTITY CASCADE"
            )

            n_pacientes = _load_pacientes_demografia(cur)
            n_clinicos = _load_perfiles_clinicos(cur)
            n_trayectorias = _load_trayectorias(cur)
            n_conversaciones = _load_conversaciones(cur)

        conn.commit()

    logger.info("pacientes_demografia: %d filas", n_pacientes)
    logger.info("perfiles_clinicos: %d filas", n_clinicos)
    logger.info("trayectorias_postop: %d filas", n_trayectorias)
    logger.info("conversaciones_turnos: %d filas", n_conversaciones)


if __name__ == "__main__":
    main()
