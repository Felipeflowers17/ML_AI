from typing import TypedDict


class ReglaScoring(TypedDict):
    """
    Representación de una regla de scoring en la capa de dominio.
    El motor de scoring solo conoce este tipo, nunca PalabraClave.
    Los workers son responsables de mapear PalabraClave → ReglaScoring.
    """

    termino: str
    peso_titulo: int
    peso_descripcion: int
    peso_productos: int
