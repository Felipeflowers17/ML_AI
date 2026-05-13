"""Script para cargar el catálogo inicial de organismos.

Estrategia con fallback:
1. Intentar desde endpoint ``BuscarComprador`` de la API.
2. Si falla, intentar desde ``organismos.csv`` en la raíz del proyecto.
3. Si ninguno está disponible, imprimir instrucciones y salir con error.

Cada organismo se inserta solo si no existe (no sobreescribe ``puntaje_fijo``).
"""

import csv
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import text

from monitor_licitaciones.infrastructure.database.connection import get_session


def _desde_api() -> list[dict] | None:
    """Intenta obtener organismos desde la API de Mercado Público."""
    ticket = os.getenv("TICKET_MERCADO_PUBLICO")
    if not ticket:
        return None

    from monitor_licitaciones.infrastructure.api.cliente_mp import ClienteAPI

    cliente = ClienteAPI(ticket)
    try:
        datos = cliente.obtener_organismos()
        if datos:
            return datos
    except Exception:
        return None
    return None


def _desde_csv() -> list[dict] | None:
    """Intenta leer organismos desde ``organismos.csv`` en la raíz.

    El archivo debe tener las columnas ``codigo`` y ``nombre``.
    Opcionalmente puede incluir ``puntaje_fijo``.
    """
    ruta = Path("organismos.csv")
    if not ruta.exists():
        return None

    datos: list[dict] = []
    with ruta.open(encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if "codigo" in row and "nombre" in row:
                entry = {
                    "codigo": row["codigo"].strip(),
                    "nombre": row["nombre"].strip(),
                }
                if "puntaje_fijo" in row and row["puntaje_fijo"].strip():
                    entry["puntaje_fijo"] = int(row["puntaje_fijo"].strip())
                datos.append(entry)
    return datos if datos else None


def _insertar_organismo(session, codigo: str, nombre: str) -> bool:
    """Inserta un organismo si no existe.

    Args:
        session: Sesión de base de datos activa.
        codigo: Código del organismo.
        nombre: Nombre del organismo.

    Returns:
        ``True`` si se insertó, ``False`` si ya existía.
    """
    existe = session.execute(
        text("SELECT 1 FROM organismos WHERE codigo = :codigo"),
        {"codigo": codigo},
    ).scalar()

    if existe:
        return False

    session.execute(
        text(
            "INSERT INTO organismos (codigo, nombre, puntaje_fijo) "
            "VALUES (:codigo, :nombre, 0)"
        ),
        {"codigo": codigo, "nombre": nombre},
    )
    return True


def main() -> None:
    """Punto de entrada para ``poetry run seed``.

    1. Carga ``.env``.
    2. Intenta obtener organismos desde la API.
    3. Si falla, intenta desde ``organismos.csv``.
    4. Si ambos fallan, imprime instrucciones y sale con código 1.
    5. Para cada organismo: inserta si no existe.
    """
    load_dotenv()

    # ── 1. Intentar desde API ────────────────────────────────────────
    organismos = _desde_api()
    fuente = "API Mercado Público"

    # ── 2. Fallback: CSV ──────────────────────────────────────────────
    if not organismos:
        organismos = _desde_csv()
        fuente = "organismos.csv"

    # ── 3. Sin datos ─────────────────────────────────────────────────
    if not organismos:
        print("ERROR: No se pudieron cargar organismos.")
        print("Opciones:")
        print("  1. Configurar TICKET_MERCADO_PUBLICO en .env y reintentar.")
        print("  2. Crear organismos.csv en la raíz con columnas: codigo,nombre")
        print()
        print("Ejemplo de organismos.csv:")
        print("  codigo,nombre")
        print("  CH-123,Municipalidad de Santiago")
        sys.exit(1)

    # ── 4. Insertar organismos en BD ─────────────────────────────────
    insertados = 0
    existentes = 0

    try:
        with get_session() as session:
            for org in organismos:
                if _insertar_organismo(
                    session,
                    codigo=org.get("CodigoOrganismo", org.get("codigo", "")),
                    nombre=org.get("NombreOrganismo", org.get("nombre", "")),
                ):
                    insertados += 1
                else:
                    existentes += 1
    except Exception as e:
        print(f"ERROR: No se pudo conectar a la base de datos: {e}")
        print("Verifique que DATABASE_URL en .env sea correcto y que PostgreSQL esté accesible.")
        sys.exit(1)

    print(f"Organismos cargados desde {fuente}:")
    print(f"  Insertados: {insertados}")
    print(f"  Ya existentes (omitidos): {existentes}")
    print("Seed completado correctamente.")
