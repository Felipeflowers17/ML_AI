"""Entry point principal de la aplicación.

Validación fail-fast de variables de entorno antes de levantar la UI.
Configura Loguru con sink a archivo rotativo y consola.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger


def main() -> None:
    """Punto de entrada de la aplicación.

    1. Carga variables de entorno desde ``.env``.
    2. Verifica que ``DATABASE_URL`` y ``TICKET_MERCADO_PUBLICO`` existan.
    3. Si falta alguna, imprime error y sale con código 1.
    4. Configura Loguru (archivo rotativo + consola).
    5. Levanta la UI con PySide6.
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

    # ── UI ────────────────────────────────────────────────────────────
    from PySide6.QtWidgets import QApplication

    from monitor_licitaciones.ui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    ventana = MainWindow()
    ventana.show()
    sys.exit(app.exec())
