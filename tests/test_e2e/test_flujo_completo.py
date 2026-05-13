"""Test del flujo E2E completo: extracción → scoring → persistencia.

Escenario Gherkin:
  Dado:
    - 2 reglas configuradas: "silla" (peso_titulo=10) y "mesa" (peso_titulo=20)
    - Mock de API que retorna 3 licitaciones:
        L1: "Compra de silla de oficina" (coincide con 'silla')
        L2: "Servicio de aseo"          (sin coincidencias)
        L3: "Adquisición de mesa de comedor" (coincide con 'mesa')
    - Mock de detalle sin coincidencias adicionales
  Cuando: se ejecuta ExtraccionWorker completo
  Entonces:
    - L1 en BD con score_resumen=10, etapa='candidata'
    - L3 en BD con score_resumen=20, etapa='candidata'
    - L2 en BD con score_resumen=0, etapa='ignorada'
    - obtener_detalle llamado exactamente 2 veces (L1 y L3)
    - obtener_detalle NO llamado para L2

TDD Cycle:
  RED: Escenario traducido a test primero.
  GREEN: Worker y motor ya implementados, test pasa inmediatamente.
  TRIANGULATE: Cobertura de flujo completo (no aplica múltiples casos aquí).
  REFACTOR: Sin cambios en producción.
"""

from unittest.mock import MagicMock

from PySide6.QtTest import QSignalSpy


class TestFlujoCompleto:
    """Flujo E2E que verifica extracción → scoring → persistencia en BD."""

    def test_flujo_completo(self, qtbot, session):
        """Ejecuta ExtraccionWorker y verifica BD y llamadas a API."""
        # ── Imports lazy (pueden no existir al momento de definir la clase) ──
        from monitor_licitaciones.domain.scoring.gestor_reglas import GestorReglas
        from monitor_licitaciones.infrastructure.database.models import Licitacion
        from monitor_licitaciones.infrastructure.database.repositorio_licitaciones import (
            RepositorioLicitaciones,
        )
        from monitor_licitaciones.infrastructure.database.repositorio_reglas import (
            RepositorioReglas,
        )
        from monitor_licitaciones.workers import mapear_reglas
        from monitor_licitaciones.workers.extraccion_worker import (
            ExtraccionWorker,
        )

        # ═══════════════════════════════════════════════════════════════════
        # SETUP: Reglas en BD
        # ═══════════════════════════════════════════════════════════════════
        repo_reglas = RepositorioReglas(session)
        repo_reglas.guardar_palabra_clave({
            "termino": "silla",
            "peso_titulo": 10,
            "peso_descripcion": 0,
            "peso_productos": 0,
            "categoria": "muebles",
            "activa": True,
        })
        repo_reglas.guardar_palabra_clave({
            "termino": "mesa",
            "peso_titulo": 20,
            "peso_descripcion": 0,
            "peso_productos": 0,
            "categoria": "muebles",
            "activa": True,
        })

        # ═══════════════════════════════════════════════════════════════════
        # SETUP: GestorReglas con reglas cargadas
        # ═══════════════════════════════════════════════════════════════════
        gestor = GestorReglas()
        palabras = repo_reglas.obtener_palabras_clave()
        reglas = mapear_reglas(palabras)
        gestor.recargar(reglas)

        # ═══════════════════════════════════════════════════════════════════
        # SETUP: Mock de ClienteAPI
        # ═══════════════════════════════════════════════════════════════════
        mock_cliente = MagicMock()
        mock_cliente.obtener_licitaciones_dia.return_value = [
            {"CodigoExterno": "L1", "Nombre": "Compra de silla de oficina"},
            {"CodigoExterno": "L2", "Nombre": "Servicio de aseo"},
            {"CodigoExterno": "L3", "Nombre": "Adquisición de mesa de comedor"},
        ]

        def detalle_side_effect(codigo):
            """Retorna detalle solo para L1 y L3 (L2 nunca se pide)."""
            detalles = {
                "L1": {
                    "CodigoExterno": "L1",
                    "Descripcion": "sin coincidencias adicionales",
                    "Comprador": {
                        "CodigoOrganismo": "ORG1",
                        "NombreOrganismo": "Organismo Uno",
                    },
                },
                "L3": {
                    "CodigoExterno": "L3",
                    "Descripcion": "sin coincidencias adicionales",
                    "Comprador": {
                        "CodigoOrganismo": "ORG2",
                        "NombreOrganismo": "Organismo Dos",
                    },
                },
            }
            return detalles.get(codigo)

        mock_cliente.obtener_detalle.side_effect = detalle_side_effect

        # Mock de repo_reglas para el worker (organismos vacío)
        mock_repo_reglas = MagicMock()
        mock_repo_reglas.obtener_organismos.return_value = []

        # ═══════════════════════════════════════════════════════════════════
        # SETUP: Repositorio real y worker
        # ═══════════════════════════════════════════════════════════════════
        repo_lic = RepositorioLicitaciones(session)

        worker = ExtraccionWorker(
            fecha_inicio="2026-01-01",
            fecha_fin="2026-01-01",
            cliente_mp=mock_cliente,
            repo_licitaciones=repo_lic,
            repo_reglas=mock_repo_reglas,
            gestor_reglas=gestor,
        )

        # ═══════════════════════════════════════════════════════════════════
        # EJECUCIÓN
        # ═══════════════════════════════════════════════════════════════════
        spy_error = QSignalSpy(worker.error)

        with qtbot.waitSignal(worker.finalizado, timeout=5000):
            worker.start()

        # Verificar que no hubo errores
        assert spy_error.count() == 0, (
            f"Worker emitió error(es): "
            f"{[spy_error[i][0] for i in range(spy_error.count())]}"
        )
        worker.wait(1000)

        # ═══════════════════════════════════════════════════════════════════
        # VERIFICACIONES EN BD
        # ═══════════════════════════════════════════════════════════════════

        # L1: coincide con 'silla' (peso_titulo=10)
        l1 = session.query(Licitacion).filter(
            Licitacion.codigo_externo == "L1"
        ).first()
        assert l1 is not None, "L1 no encontrada en BD"
        assert l1.score_resumen == 10, (
            f"L1 score_resumen esperado=10, obtenido={l1.score_resumen}"
        )
        assert l1.etapa == "candidata", (
            f"L1 etapa esperada='candidata', obtenida='{l1.etapa}'"
        )

        # L3: coincide con 'mesa' (peso_titulo=20)
        l3 = session.query(Licitacion).filter(
            Licitacion.codigo_externo == "L3"
        ).first()
        assert l3 is not None, "L3 no encontrada en BD"
        assert l3.score_resumen == 20, (
            f"L3 score_resumen esperado=20, obtenido={l3.score_resumen}"
        )
        assert l3.etapa == "candidata", (
            f"L3 etapa esperada='candidata', obtenida='{l3.etapa}'"
        )

        # L2: sin coincidencia → score 0, ignorada
        l2 = session.query(Licitacion).filter(
            Licitacion.codigo_externo == "L2"
        ).first()
        assert l2 is not None, "L2 no encontrada en BD"
        assert l2.score_resumen == 0, (
            f"L2 score_resumen esperado=0, obtenido={l2.score_resumen}"
        )
        assert l2.etapa == "ignorada", (
            f"L2 etapa esperada='ignorada', obtenida='{l2.etapa}'"
        )

        # ═══════════════════════════════════════════════════════════════════
        # VERIFICACIONES DE LLAMADAS A API
        # ═══════════════════════════════════════════════════════════════════
        assert mock_cliente.obtener_detalle.call_count == 2, (
            f"obtener_detalle debe llamarse 2 veces, "
            f"llamado {mock_cliente.obtener_detalle.call_count}"
        )

        # Verificar que L1 y L3 fueron solicitadas
        mock_cliente.obtener_detalle.assert_any_call("L1")
        mock_cliente.obtener_detalle.assert_any_call("L3")

        # Verificar que L2 NO fue solicitada
        for call in mock_cliente.obtener_detalle.call_args_list:
            assert (
                call.args[0] != "L2"
            ), f"obtener_detalle NO debe llamarse para L2, llamado con args={call.args}"
