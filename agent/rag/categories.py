"""Categorias clinicas del corpus del RAG.

Las cinco categorias corresponden 1:1 a las carpetas de dataset/textos/ (el
corpus de guias clinicas) y a los cinco procedimientos de
perfiles_clinicos_pacientes_silver_contest.xlsx. Se usan para etiquetar cada
documento al ingestarlo y para filtrar la busqueda por la especialidad del
paciente -sin este filtro, una guia de apendicitis puede aparecer en la
llamada de un paciente de reemplazo de cadera/rodilla solo porque el
embedding de la pregunta se parece un poco al de esa guia.
"""

import unicodedata

CATEGORIAS = (
    "Appendicitis",
    "breast_cancer",
    "cholecystitis",
    "colorectal cancer",
    "total joint replacement",
)

PROCEDIMIENTO_A_CATEGORIA = {
    "Apendicectomia": "Appendicitis",
    "Colecistectomia": "cholecystitis",
    "Colectomia": "colorectal cancer",
    "Reemplazo de cadera/rodilla": "total joint replacement",
    "Mastectomia": "breast_cancer",
}


def _normalizar(texto: str) -> str:
    sin_tildes = "".join(
        c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
    )
    return sin_tildes.strip().lower()


_PROCEDIMIENTOS_NORMALIZADOS = {_normalizar(proc): categoria for proc, categoria in PROCEDIMIENTO_A_CATEGORIA.items()}


def categoria_por_procedimiento(procedimiento: str | None) -> str | None:
    """Devuelve la categoria del corpus para el procedimiento del paciente, o None
    si no hay procedimiento o no coincide con ninguno conocido (tildes/mayusculas
    no importan)."""
    if not procedimiento:
        return None
    return _PROCEDIMIENTOS_NORMALIZADOS.get(_normalizar(procedimiento))
