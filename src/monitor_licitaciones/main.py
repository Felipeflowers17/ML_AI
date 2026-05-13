"""Entry point principal de la aplicación.

Validación fail-fast de variables de entorno antes de levantar la UI.
Configura Loguru con sink a archivo rotativo y consola.
Realiza el wiring de dependencias para MainWindow.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def validar_entorno() -> bool:
    """Valida que DATABASE_URL y TICKET_MERCADO_PUBLICO estén configuradas.

    Returns:
        True si ambas variables existen, False en caso contrario.
    """
    load_dotenv()

    # ── Fail-fast: validar entorno antes de cualquier import pesado ──
    errores: list[str] = []
    if not os.getenv("DATABASE_URL"):
        errores.append("DATABASE_URL")
    if not os.getenv("TICKET_MERCADO_PUBLICO"):
        errores.append("TICKET_MERCADO_PUBLICO")

    if errores:
        print("ERROR: Faltan variables de entorno requeridas:")
        for e in errores:
            print(f"  - {e}: no configurada en .env")
        print(f"\nEdite: {Path('.env').resolve()}")
        return False

    return True


def main() -> None:
    """Punto de entrada de la aplicación.

    1. Carga variables de entorno desde ``.env``.
    2. Verifica que ``DATABASE_URL`` y ``TICKET_MERCADO_PUBLICO`` existan.
    3. Si falta alguna, imprime error y sale con código 1.
    4. Configura Loguru (archivo rotativo + consola).
    5. Inicializa la base de datos y crea las dependencias.
    6. Levanta la UI con PySide6.
    """
    if not validar_entorno():
        sys.exit(1)

    # ── Logging ──────────────────────────────────────────────────────
    Path("logs").mkdir(exist_ok=True)
    logger.add(
        "logs/monitor_{time:YYYY-MM-DD}.log",
        rotation="1 day",
        retention="30 days",
        level="DEBUG",
        encoding="utf-8",
    )
    logger.add(sys.stdout, level="INFO")

    logger.info("Iniciando Monitor de Licitaciones…")

    # ── Imports de infraestructura y dominio ─────────────────────────
    from monitor_licitaciones.infrastructure.database.models import Base
    from monitor_licitaciones.infrastructure.database.repositorio_configuracion import (
        RepositorioConfiguracion,
    )
    from monitor_licitaciones.infrastructure.database.repositorio_licitaciones import (
        RepositorioLicitaciones,
    )
    from monitor_licitaciones.infrastructure.database.repositorio_reglas import (
        RepositorioReglas,
    )
    from monitor_licitaciones.domain.scoring.gestor_reglas import GestorReglas
    from monitor_licitaciones.domain.pipeline.gestor_pipeline import GestorPipeline
    from monitor_licitaciones.infrastructure.api.cliente_mp import ClienteAPI
    from monitor_licitaciones.workers.extraccion_worker import ExtraccionWorker
    from monitor_licitaciones.workers.scoring_worker import ScoringWorker
    from monitor_licitaciones.workers.piloto_worker import PilotoWorker
    from monitor_licitaciones.workers import mapear_reglas

    # ── Inicializar BD ───────────────────────────────────────────────
    db_url = os.getenv("DATABASE_URL")
    engine = create_engine(db_url, pool_pre_ping=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    session = SessionLocal()

    # ── Repositorios ─────────────────────────────────────────────────
    repo_licitaciones = RepositorioLicitaciones(session)
    repo_reglas = RepositorioReglas(session)
    repo_config = RepositorioConfiguracion(session)

    # ── Dominio ──────────────────────────────────────────────────────
    gestor_reglas = GestorReglas()
    gestor_pipeline = GestorPipeline()

    # Recargar reglas desde BD
    palabras = repo_reglas.obtener_palabras_clave()
    reglas = mapear_reglas(palabras)
    gestor_reglas.recargar(reglas)

    # ── Cliente API ──────────────────────────────────────────────────
    ticket = os.getenv("TICKET_MERCADO_PUBLICO", "")
    cliente_mp = ClienteAPI(ticket)

    # ── Workers ──────────────────────────────────────────────────────
    # ExtraccionWorker se crea bajo demanda vía factory
    def crear_extraccion_worker(
        fecha_inicio: str, fecha_fin: str
    ) -> ExtraccionWorker:
        return ExtraccionWorker(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            cliente_mp=cliente_mp,
            repo_licitaciones=repo_licitaciones,
            repo_reglas=repo_reglas,
            gestor_reglas=gestor_reglas,
        )

    extraccion_worker = crear_extraccion_worker("", "")

    scoring_worker = ScoringWorker(
        repo_licitaciones=repo_licitaciones,
        repo_reglas=repo_reglas,
        gestor_reglas=gestor_reglas,
    )

    piloto_worker = PilotoWorker(
        repo_config=repo_config,
        cliente_mp=cliente_mp,
        repo_licitaciones=repo_licitaciones,
        repo_reglas=repo_reglas,
        gestor_reglas=gestor_reglas,
    )

    # ── UI ───────────────────────────────────────────────────────────
    from PySide6.QtWidgets import QApplication

    from monitor_licitaciones.ui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    ventana = MainWindow(
        repo_licitaciones=repo_licitaciones,
        repo_reglas=repo_reglas,
        repo_config=repo_config,
        gestor_reglas=gestor_reglas,
        gestor_pipeline=gestor_pipeline,
        extraccion_worker=extraccion_worker,
        scoring_worker=scoring_worker,
        exportacion_worker_factory=crear_extraccion_worker,
        piloto_worker=piloto_worker,
    )
    ventana.show()
    sys.exit(app.exec())