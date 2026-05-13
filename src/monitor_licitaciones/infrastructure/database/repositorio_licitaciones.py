"""Repositorio de licitaciones — operaciones CRUD y consultas.

Siete métodos que cubren inserción, actualización, búsqueda paginada,
conteo por etapa y actualización de score y etapa.
"""

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from monitor_licitaciones.config import ETAPAS_ACTIVAS
from monitor_licitaciones.infrastructure.database.models import Licitacion


class RepositorioLicitaciones:
    """Repositorio para la entidad Licitacion."""

    def obtener_por_codigo(
        self, codigo_externo: str
    ) -> Licitacion | None:
        """Busca una licitación por su código externo.

        Args:
            codigo_externo: Código único de la licitación.

        Returns:
            Instancia de Licitacion o ``None`` si no existe.
        """
        return (
            self._session.query(Licitacion)
            .filter(Licitacion.codigo_externo == codigo_externo)
            .first()
        )

    def __init__(self, session: Session):
        self._session = session

    def obtener_por_etapa(
        self, etapa: str, pagina: int = 0, por_pagina: int = 50
    ) -> list[Licitacion]:
        """Filtra por etapa, ordena por score_total DESC, pagina."""
        return (
            self._session.query(Licitacion)
            .filter(Licitacion.etapa == etapa)
            .order_by(Licitacion.score_total.desc())
            .offset(pagina * por_pagina)
            .limit(por_pagina)
            .all()
        )

    def obtener_activas_en_pipeline(
        self, etapas: list[str], codigo_estado_activo: int
    ) -> list[Licitacion]:
        """Licitaciones en pipeline activo: etapa IN y estado = activo."""
        return (
            self._session.query(Licitacion)
            .filter(Licitacion.etapa.in_(etapas))
            .filter(Licitacion.codigo_estado == codigo_estado_activo)
            .all()
        )

    def buscar_por_texto(
        self,
        texto: str,
        etapa: str,
        pagina: int = 0,
        por_pagina: int = 50,
    ) -> list[Licitacion]:
        """ILIKE en nombre OR descripcion, filtrado por etapa y paginado."""
        patron = f"%{texto}%"
        return (
            self._session.query(Licitacion)
            .filter(Licitacion.etapa == etapa)
            .filter(
                or_(
                    Licitacion.nombre.ilike(patron),
                    Licitacion.descripcion.ilike(patron),
                )
            )
            .order_by(Licitacion.score_total.desc())
            .offset(pagina * por_pagina)
            .limit(por_pagina)
            .all()
        )

    def contar_por_etapa(self) -> dict[str, int]:
        """Conteo de licitaciones agrupado por etapa activa.

        Retorna dict con las tres etapas activas incluso si alguna tiene 0.
        """
        resultado = (
            self._session.query(
                Licitacion.etapa, func.count(Licitacion.id)
            )
            .filter(Licitacion.etapa.in_(ETAPAS_ACTIVAS))
            .group_by(Licitacion.etapa)
            .all()
        )
        conteos: dict[str, int] = {e: 0 for e in ETAPAS_ACTIVAS}
        for etapa, count in resultado:
            conteos[etapa] = count
        return conteos

    def upsert(self, datos: dict) -> Licitacion:
        """Inserta o actualiza una licitación según su ``codigo_externo``.

        Reglas:
        - Actualiza campos básicos siempre.
        - Actualiza campos de detalle solo si ``tiene_detalle=True``.
        - Ascenso de etapa: solo si la actual es ``"ignorada"`` y
          la nueva es ``"candidata"``. Nunca retrocede.
        """
        codigo = datos["codigo_externo"]
        instancia: Licitacion | None = (
            self._session.query(Licitacion)
            .filter(Licitacion.codigo_externo == codigo)
            .first()
        )

        if instancia is None:
            # Insertar nueva
            instancia = Licitacion(**datos)
            self._session.add(instancia)
        else:
            # Actualizar campos básicos siempre
            for campo in [
                "nombre",
                "descripcion",
                "fecha_publicacion",
                "fecha_cierre",
                "fecha_inicio",
                "fecha_adjudicacion",
                "codigo_organismo",
                "codigo_estado",
            ]:
                if campo in datos:
                    setattr(instancia, campo, datos[campo])

            # Campos de detalle solo si tiene_detalle=True
            if datos.get("tiene_detalle"):
                for campo in ["detalle_productos", "justificacion_score"]:
                    if campo in datos:
                        setattr(instancia, campo, datos[campo])

            # Regla de ascenso de etapa
            if "etapa" in datos:
                etapa_actual = instancia.etapa
                nueva_etapa = datos["etapa"]
                if etapa_actual == "ignorada" and nueva_etapa == "candidata":
                    instancia.etapa = nueva_etapa

        return instancia

    def actualizar_etapa(
        self, codigo_externo: str, etapa: str
    ) -> bool:
        """Actualiza la etapa de una licitación. Retorna True si existía."""
        instancia: Licitacion | None = (
            self._session.query(Licitacion)
            .filter(Licitacion.codigo_externo == codigo_externo)
            .first()
        )
        if instancia is None:
            return False
        instancia.etapa = etapa
        return True

    def actualizar_score(
        self,
        codigo_externo: str,
        score_resumen: int,
        score_detalle: int,
        score_total: int,
        justificacion: str,
    ) -> bool:
        """Actualiza los campos de score de una licitación."""
        instancia: Licitacion | None = (
            self._session.query(Licitacion)
            .filter(Licitacion.codigo_externo == codigo_externo)
            .first()
        )
        if instancia is None:
            return False
        instancia.score_resumen = score_resumen
        instancia.score_detalle = score_detalle
        instancia.score_total = score_total
        instancia.justificacion_score = justificacion
        return True
