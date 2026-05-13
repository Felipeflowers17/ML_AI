"""Tests para GestorReglas — thread-safety y gestión de estado compartido.

Strict TDD: estos tests se escribieron ANTES de la implementación.
Verifican que el gestor maneja correctamente concurrencia lector/escritor
y que las snapshots son copias independientes.
"""

import threading
from monitor_licitaciones.domain.scoring.tipos import ReglaScoring
from monitor_licitaciones.domain.scoring.gestor_reglas import GestorReglas


def _reglas_muestra() -> list[ReglaScoring]:
    return [
        ReglaScoring(termino="silla", peso_titulo=10, peso_descripcion=5, peso_productos=1),
        ReglaScoring(termino="mesa", peso_titulo=20, peso_descripcion=10, peso_productos=2),
    ]


class TestGestorReglas:
    """Tests de thread-safety para GestorReglas."""

    def test_snapshot_es_copia_independiente(self):
        """Modificar el resultado de obtener_snapshot() no altera el estado interno."""
        gestor = GestorReglas()
        reglas = _reglas_muestra()
        gestor.recargar(reglas)

        snapshot = gestor.obtener_snapshot()
        # Modificar la copia externa
        snapshot.append(
            ReglaScoring(termino="escritorio", peso_titulo=5, peso_descripcion=3, peso_productos=1)
        )

        # El snapshot original debe seguir teniendo solo 2 elementos
        assert len(gestor.obtener_snapshot()) == 2

    def test_recargar_actualiza_snapshot(self):
        """Después de recargar, obtener_snapshot() retorna las nuevas reglas."""
        gestor = GestorReglas()
        reglas_iniciales = _reglas_muestra()
        gestor.recargar(reglas_iniciales)

        nuevas_reglas = [
            ReglaScoring(termino="escritorio", peso_titulo=5, peso_descripcion=3, peso_productos=1),
        ]
        gestor.recargar(nuevas_reglas)

        snapshot = gestor.obtener_snapshot()
        assert len(snapshot) == 1
        assert snapshot[0]["termino"] == "escritorio"

    def test_recargar_con_lista_vacia(self):
        """Recargar con lista vacía → obtener_snapshot() retorna []."""
        gestor = GestorReglas()
        gestor.recargar(_reglas_muestra())

        gestor.recargar([])
        snapshot = gestor.obtener_snapshot()
        assert snapshot == []

    def test_concurrencia_lector_escritor(self):
        """1 escritor + 5 lectores concurrentes durante 2s sin excepciones."""
        gestor = GestorReglas()
        gestor.recargar(_reglas_muestra())

        excepciones: list[Exception] = []
        excepciones_lock = threading.Lock()
        stop_event = threading.Event()

        def escritor():
            contador = 0
            while not stop_event.is_set():
                reglas = [
                    ReglaScoring(
                        termino=f"regla_{contador}",
                        peso_titulo=contador,
                        peso_descripcion=contador,
                        peso_productos=contador,
                    )
                ]
                try:
                    gestor.recargar(reglas)
                except Exception as e:
                    with excepciones_lock:
                        excepciones.append(e)
                contador += 1

        def lector():
            while not stop_event.is_set():
                try:
                    snapshot = gestor.obtener_snapshot()
                    # Verificar que el snapshot es una copia válida
                    _ = len(snapshot)
                    if snapshot:
                        _ = snapshot[0]["termino"]
                except Exception as e:
                    with excepciones_lock:
                        excepciones.append(e)

        threads = []
        # 1 escritor
        t_escritor = threading.Thread(target=escritor, daemon=True)
        threads.append(t_escritor)
        # 5 lectores
        for _ in range(5):
            t = threading.Thread(target=lector, daemon=True)
            threads.append(t)

        for t in threads:
            t.start()

        # Dejar correr por 2 segundos
        stop_event.wait(2)
        stop_event.set()

        for t in threads:
            t.join(timeout=2)

        assert len(excepciones) == 0, (
            f"Se produjeron {len(excepciones)} excepciones durante concurrencia: {excepciones}"
        )
