"""Motor de scoring — funciones puras para evaluar textos contra reglas.

Este módulo NO importa nada de infrastructure. Solo conoce ReglaScoring
definido en tipos.py. Los workers son responsables de convertir
PalabraClave → ReglaScoring antes de llamar a estas funciones.
"""

import re
from typing import List, Tuple

from monitor_licitaciones.domain.scoring.tipos import ReglaScoring


def evaluar_titulo(
    texto: str | None,
    reglas: List[ReglaScoring],
) -> Tuple[int, List[str]]:
    """Evalúa el título de una licitación contra una lista de reglas.

    Args:
        texto: Título de la licitación (puede ser None).
        reglas: Lista de reglas de scoring a aplicar.

    Returns:
        Tupla (score_total, lista_motivos).
        Cada motivo tiene formato: "[TÍTULO] 'término' (+peso)".
    """
    if texto is None:
        texto = ""
    texto_lower = texto.lower()
    score = 0
    motivos: List[str] = []

    for regla in reglas:
        pattern = re.compile(rf"\b{re.escape(regla['termino'].lower())}\b")
        if pattern.search(texto_lower):
            peso = regla["peso_titulo"]
            score += peso
            motivos.append(
                f"[TÍTULO] '{regla['termino']}' (+{peso})"
            )

    return (score, motivos)


def evaluar_detalle(
    descripcion: str | None,
    productos: str | None,
    reglas: List[ReglaScoring],
) -> Tuple[int, List[str]]:
    """Evalúa la descripción y productos de una licitación contra reglas.

    Busca coincidencias en descripción (usa peso_descripcion) y en
    productos (usa peso_productos) por separado.

    Args:
        descripcion: Descripción de la licitación (puede ser None).
        productos: Detalle de productos (puede ser None).
        reglas: Lista de reglas de scoring a aplicar.

    Returns:
        Tupla (score_total, lista_motivos).
        Motivos de descripción: "[DESC] 'término' (+peso)".
        Motivos de productos: "[PROD] 'término' (+peso)".
    """
    if descripcion is None:
        descripcion = ""
    if productos is None:
        productos = ""
    desc_lower = descripcion.lower()
    prod_lower = productos.lower()
    score = 0
    motivos: List[str] = []

    for regla in reglas:
        pattern = re.compile(rf"\b{re.escape(regla['termino'].lower())}\b")
        termino = regla["termino"]

        if pattern.search(desc_lower):
            peso = regla["peso_descripcion"]
            score += peso
            motivos.append(f"[DESC] '{termino}' (+{peso})")

        if pattern.search(prod_lower):
            peso = regla["peso_productos"]
            score += peso
            motivos.append(f"[PROD] '{termino}' (+{peso})")

    return (score, motivos)
