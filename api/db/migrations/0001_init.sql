CREATE TABLE IF NOT EXISTS pacientes_demografia (
    paciente_id TEXT PRIMARY KEY,
    nombre_completo TEXT,
    direccion TEXT,
    ciudad TEXT,
    departamento TEXT,
    documento_cc BIGINT,
    eps TEXT,
    source_country TEXT,
    adapted_country TEXT,
    adaptation_fields JSONB,
    adaptation_ts TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS perfiles_clinicos (
    paciente_id TEXT PRIMARY KEY REFERENCES pacientes_demografia (paciente_id) ON DELETE CASCADE,
    bundle_id TEXT,
    synthea_runtime TEXT,
    modulo_synthea TEXT,
    procedimiento TEXT,
    fecha_cirugia DATE,
    edad INTEGER,
    genero TEXT,
    comorbilidades JSONB,
    complicacion_encounter BOOLEAN,
    generado_ts TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS trayectorias_postop (
    trayectoria_id TEXT PRIMARY KEY,
    paciente_id TEXT NOT NULL REFERENCES pacientes_demografia (paciente_id) ON DELETE CASCADE,
    dia_postop INTEGER NOT NULL,
    arquetipo_trayectoria TEXT,
    dolor_nrs INTEGER,
    fiebre_c NUMERIC,
    movilidad TEXT,
    herida TEXT,
    apetito TEXT,
    sueno TEXT,
    seed INTEGER,
    generado_ts TIMESTAMPTZ
);

-- Una fila = un turno de conversación (ver README, sección "Los datos").
-- caso_id = "caso_" + trayectoria_id, de ahí la columna derivada trayectoria_id.
CREATE TABLE IF NOT EXISTS conversaciones_turnos (
    dialogo_id TEXT PRIMARY KEY,
    caso_id TEXT NOT NULL,
    trayectoria_id TEXT NOT NULL REFERENCES trayectorias_postop (trayectoria_id) ON DELETE CASCADE,
    paciente_id TEXT NOT NULL REFERENCES pacientes_demografia (paciente_id) ON DELETE CASCADE,
    dia_postop INTEGER NOT NULL,
    turno_idx INTEGER NOT NULL,
    hablante TEXT,
    texto TEXT,
    label_ground_truth TEXT,
    estilo_paciente TEXT,
    modelo_paciente TEXT,
    modelo_agente TEXT,
    capa TEXT NOT NULL,
    generado_ts TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_conversaciones_caso_id ON conversaciones_turnos (caso_id);
CREATE INDEX IF NOT EXISTS idx_conversaciones_capa ON conversaciones_turnos (capa);
CREATE INDEX IF NOT EXISTS idx_trayectorias_paciente_id ON trayectorias_postop (paciente_id);
