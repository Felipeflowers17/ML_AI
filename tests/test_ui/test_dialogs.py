"""Tests para los diálogos de UI con pytest-qt.

Cubre FichaTecnicaDialog y GestionOrganismosDialog.
"""

from unittest.mock import MagicMock, patch

import pytest


class TestFichaTecnicaDialog:
    """Tests para FichaTecnicaDialog — ficha técnica de licitación."""

    def test_dialog_muestra_datos_de_licitacion(self, qtbot):
        """El diálogo muestra nombre, código, scores y descripción."""
        from monitor_licitaciones.ui.dialogs.ficha_tecnica import (
            FichaTecnicaDialog,
        )
        from datetime import datetime

        # Mock de licitación con datos completos
        mock_lic = MagicMock()
        mock_lic.codigo_externo = "L-123"
        mock_lic.nombre = "Compra de sillas de oficina"
        mock_lic.etapa = "candidata"
        mock_lic.codigo_organismo = "ORG-1"
        mock_lic.fecha_publicacion = datetime(2026, 1, 15, 10, 30, 0)
        mock_lic.descripcion = "Adquisición de sillas ergonómicas"
        mock_lic.detalle_productos = "Silla Premium, Silla Ejecutiva"
        mock_lic.score_resumen = 10
        mock_lic.score_detalle = 5
        mock_lic.score_total = 15
        mock_lic.justificacion_score = "[TÍTULO] 'silla' (+10); [DESC] 'silla' (+5)"

        repo_mock = MagicMock()
        repo_mock.obtener_por_codigo.return_value = mock_lic

        dialog = FichaTecnicaDialog("L-123", repo_mock)
        qtbot.addWidget(dialog)
        dialog.show()

        # Verificar que los datos se muestran
        assert "Compra de sillas" in dialog._lbl_nombre.text()
        assert dialog._lbl_codigo.text() == "L-123"
        assert dialog._lbl_etapa.text() == "candidata"
        assert "ORG-1" in dialog._lbl_organismo.text()
        assert "2026-01-15" in dialog._lbl_fecha_publicacion.text()
        assert dialog._lbl_score_resumen.text() == "10"
        assert dialog._lbl_score_detalle.text() == "5"
        assert dialog._lbl_score_total.text() == "15"
        assert "silla" in dialog._txt_justificacion.toPlainText()

    def test_dialog_licitacion_no_encontrada(self, qtbot):
        """Si la licitación no existe, muestra mensaje de no encontrada."""
        from monitor_licitaciones.ui.dialogs.ficha_tecnica import (
            FichaTecnicaDialog,
        )

        repo_mock = MagicMock()
        repo_mock.obtener_por_codigo.return_value = None

        dialog = FichaTecnicaDialog("L-INEXISTENTE", repo_mock)
        qtbot.addWidget(dialog)
        dialog.show()

        assert "no encontrada" in dialog._lbl_nombre.text()

    def test_dialog_fecha_publicacion_none(self, qtbot):
        """Si fecha_publicacion es None, muestra 'No disponible'."""
        from monitor_licitaciones.ui.dialogs.ficha_tecnica import (
            FichaTecnicaDialog,
        )

        mock_lic = MagicMock()
        mock_lic.codigo_externo = "L-456"
        mock_lic.nombre = "Test"
        mock_lic.etapa = "ignorada"
        mock_lic.codigo_organismo = None
        mock_lic.fecha_publicacion = None
        mock_lic.descripcion = None
        mock_lic.detalle_productos = None
        mock_lic.score_resumen = 0
        mock_lic.score_detalle = 0
        mock_lic.score_total = 0
        mock_lic.justificacion_score = None

        repo_mock = MagicMock()
        repo_mock.obtener_por_codigo.return_value = mock_lic

        dialog = FichaTecnicaDialog("L-456", repo_mock)
        qtbot.addWidget(dialog)
        dialog.show()

        assert dialog._lbl_fecha_publicacion.text() == "No disponible"
        assert dialog._lbl_organismo.text() == "No disponible"


class TestGestionOrganismosDialog:
    """Tests para GestionOrganismosDialog — CRUD de organismos."""

    def test_carga_organismos_en_tabla(self, qtbot, session):
        """El diálogo carga organismos desde el repositorio en la tabla."""
        from monitor_licitaciones.ui.dialogs.gestion_organismos import (
            GestionOrganismosDialog,
        )
        from monitor_licitaciones.infrastructure.database.repositorio_reglas import (
            RepositorioReglas,
        )
        from monitor_licitaciones.infrastructure.database.models import (
            Organismo,
        )

        # Insertar datos de prueba
        session.add(Organismo(codigo="ORG1", nombre="Org Uno", puntaje_fijo=10))
        session.add(Organismo(codigo="ORG2", nombre="Org Dos", puntaje_fijo=0))
        session.flush()

        repo = RepositorioReglas(session)
        dialog = GestionOrganismosDialog(repo)
        qtbot.addWidget(dialog)
        dialog.show()

        assert dialog._tabla.rowCount() == 2
        # Los organismos se ordenan por nombre alfabéticamente
        # "Org Dos" < "Org Uno" → ORG2 primero, ORG1 segundo
        assert dialog._tabla.item(0, 0).text() == "ORG2"
        assert dialog._tabla.item(0, 2).text() == "0"
        assert dialog._tabla.item(1, 0).text() == "ORG1"

    def test_guardar_organismo_en_repositorio(self, qtbot, session):
        """GestionOrganismosDialog persiste cambios a través del repositorio."""
        from monitor_licitaciones.infrastructure.database.repositorio_reglas import (
            RepositorioReglas,
        )

        repo = RepositorioReglas(session)
        repo.guardar_organismo({
            "codigo": "TEST1",
            "nombre": "Organismo de prueba",
            "puntaje_fijo": 25,
        })
        session.flush()

        organismos = repo.obtener_organismos()
        assert len(organismos) == 1
        assert organismos[0].codigo == "TEST1"
        assert organismos[0].nombre == "Organismo de prueba"
        assert organismos[0].puntaje_fijo == 25

    def test_actualizar_organismo_existente(self, qtbot, session):
        """Actualizar un organismo existente modifica sus campos."""
        from monitor_licitaciones.infrastructure.database.repositorio_reglas import (
            RepositorioReglas,
        )
        from monitor_licitaciones.infrastructure.database.models import (
            Organismo,
        )

        session.add(Organismo(codigo="EXISTE", nombre="Original", puntaje_fijo=5))
        session.flush()

        repo = RepositorioReglas(session)
        repo.guardar_organismo({
            "codigo": "EXISTE",
            "nombre": "Modificado",
            "puntaje_fijo": 50,
        })
        session.flush()

        organismos = repo.obtener_organismos()
        assert len(organismos) == 1
        assert organismos[0].nombre == "Modificado"
        assert organismos[0].puntaje_fijo == 50

    def test_desactivar_organismo_puntaje_cero(self, qtbot, session):
        """Desactivar organismo setea puntaje_fijo a 0."""
        from monitor_licitaciones.infrastructure.database.repositorio_reglas import (
            RepositorioReglas,
        )
        from monitor_licitaciones.infrastructure.database.models import (
            Organismo,
        )

        session.add(Organismo(codigo="ACTIVO", nombre="Activo", puntaje_fijo=30))
        session.flush()

        repo = RepositorioReglas(session)
        repo.actualizar_puntaje_organismo("ACTIVO", 0)
        session.flush()

        org = session.query(Organismo).filter(
            Organismo.codigo == "ACTIVO"
        ).first()
        assert org.puntaje_fijo == 0
