-- Resumen estructurado de cada llamada de seguimiento postoperatorio: la
-- clasificacion de criticidad que decide el agente (verde/amarillo/rojo) y lo
-- que sustenta esa decision. Lo puebla agent/decision.py durante la llamada,
-- no api/db/seed_dataset.py -- no es parte del dataset del reto.
CREATE TABLE IF NOT EXISTS resumenes_llamada (
    resumen_id TEXT PRIMARY KEY,
    paciente_id TEXT REFERENCES pacientes_demografia (paciente_id) ON DELETE SET NULL,
    nombre_paciente TEXT,
    procedimiento TEXT,
    clasificacion TEXT NOT NULL CHECK (clasificacion IN ('verde', 'amarillo', 'rojo', 'sin_clasificar')),
    escalado BOOLEAN NOT NULL DEFAULT FALSE,
    sintomas_reportados TEXT,
    justificacion TEXT,
    siguientes_pasos TEXT,
    referencias_usadas JSONB,
    creado_ts TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_resumenes_paciente_id ON resumenes_llamada (paciente_id);
CREATE INDEX IF NOT EXISTS idx_resumenes_clasificacion ON resumenes_llamada (clasificacion);
