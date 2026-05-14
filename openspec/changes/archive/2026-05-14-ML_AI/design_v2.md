# Design: ML_AI - Monitor de Licitaciones

*Documento de fase DESIGN — SDD*
*Proyecto: ML_AI*
*Fecha: Mayo 2026*

---

## Enfoque Técnico

Sistema de monitoreo de licitaciones de Mercado Público Chile con extracción
automatizada vía API, scoring configurable basado en reglas y pipeline operativo
de tres etapas. La arquitectura sigue un patrón por capas que separa
estrictamente la UI (PySide6) de la lógica de negocio (domain) y el acceso a
datos (infrastructure).

La concurrencia se maneja mediante QThread workers con señales nativas de
PySide6. El scoring es recargable en caliente usando snapshots de reglas con
locks. Las reglas se inyectan como parámetro al motor de scoring (función pura),
lo que hace el dominio 100% testeable sin mocks ni BD.

---

## Decisiones de Arquitectura

### Decisión 1: Estructura de Proyecto

**Elección**: Estructura por capas con subdirectorios por tipo de componente.

```
src/monitor_licitaciones/
├── ui/
│   ├── main_window.py
│   ├── widgets/
│   │   ├── tabla_licitaciones.py
│   │   ├── filtro_busqueda.py
│   │   └── indicadores_pipeline.py
│   └── dialogs/
│       ├── config_palabras_clave.py
│       ├── config_extraccion.py
│       ├── config_exportacion.py
│       └── config_piloto.py
├── workers/
│   ├── extraccion_worker.py
│   ├── scoring_worker.py
│   ├── exportacion_worker.py
│   └── piloto_worker.py
├── domain/
│   ├── scoring/
│   │   ├── motor_scoring.py
│   │   └── gestor_reglas.py
│   └── pipeline/
│       └── gestor_pipeline.py
├── infrastructure/
│   ├── database/
│   │   ├── models.py
│   │   ├── connection.py
│   │   ├── repositorio_licitaciones.py
│   │   ├── repositorio_reglas.py
│   │   └── repositorio_configuracion.py
│   └── api/
│       └── cliente_mp.py
└── cli/
    ├── migrate.py
    ├── init_db.py
    └── seed.py
```

**Alternativas descartadas**: Estructura flat (todos los módulos en `src/`),
estructura monolito (single package sin separación de capas).

**Rationale**: El PRD establece "Separación estricta entre UI y lógica de
negocio" como principio no negociable. La estructura por capas hace enforce esta
separación a nivel de sistema de archivos: la capa `domain` no tiene ninguna
dependencia hacia afuera, lo que garantiza que los tests de lógica de negocio
corran sin BD, sin API y sin UI.

---

### Decisión 2: Motor de Scoring como Función Pura

**Elección**: El motor de scoring recibe las reglas como parámetro en cada
llamada. El gestor de reglas administra el estado compartido de forma
thread-safe.

```python
# GestorReglas: administra el estado compartido (thread-safe)
class GestorReglas:
    def __init__(self):
        self._lock = threading.Lock()
        self._reglas: list[PalabraClave] = []

    def recargar(self, reglas: list[PalabraClave]) -> None:
        with self._lock:
            self._reglas = list(reglas)  # copia defensiva

    def obtener_snapshot(self) -> list[PalabraClave]:
        with self._lock:
            return list(self._reglas)    # snapshot para el llamador

# MotorScoring: función pura, sin estado, sin locks
class MotorScoring:
    def evaluar_titulo(
        self, texto: str, reglas: list[PalabraClave]
    ) -> tuple[int, list[str]]:
        ...

    def evaluar_detalle(
        self, descripcion: str, productos: str, reglas: list[PalabraClave]
    ) -> tuple[int, list[str]]:
        ...

# Uso en workers:
snapshot = gestor.obtener_snapshot()          # lock solo aquí (nanosegundos)
score, motivos = motor.evaluar_titulo(texto, snapshot)  # sin lock, puro CPU
```

**Alternativas descartadas**: Reglas como estado interno del motor (requiere
mocks de BD para testear el scoring), singleton global con lock durante todo el
cálculo (bloquea threads innecesariamente durante la evaluación léxica).

**Rationale**: El PRD exige "scoring recargable en caliente sin corromper
evaluaciones en curso". Al separar el gestor (estado) del motor (cálculo), el
lock solo existe durante la copia de la referencia, nunca durante la evaluación.
Además, el motor como función pura es 100% determinístico: el mismo input
siempre produce el mismo output, lo que hace los tests trivialmente simples sin
ninguna dependencia externa.

---

### Decisión 3: Patrón de Comunicación UI ↔ Workers

**Elección**: Signals/slots de PySide6 (nativos) con contrato predefinido por
worker.

```python
class ExtraccionWorker(QThread):
    progreso   = Signal(str)       # mensaje de estado para el log visual
    avance     = Signal(int, int)  # actual, total — para barra de progreso
    finalizado = Signal()          # extracción completada con éxito
    error      = Signal(str)       # fallo con mensaje descriptivo

class ScoringWorker(QThread):
    progreso   = Signal(str)
    avance     = Signal(int, int)
    finalizado = Signal()          # UI recarga las 3 pestañas al recibir esto
    error      = Signal(str)

class ExportacionWorker(QThread):
    avance     = Signal(int, int)
    finalizado = Signal(str)       # str = ruta del archivo generado
    error      = Signal(str)

class PilotoWorker(QThread):
    estado_cambiado      = Signal(str)  # texto descriptivo para label de estado
    extraccion_iniciada  = Signal()
    extraccion_completada = Signal()
    error_ocurrido       = Signal(str)
```

**Alternativas descartadas**: Queue de mensajes personalizada, callbacks con
wrapper thread-safe.

**Rationale**: PySide6 tiene soporte nativo cross-thread para signals/slots.
Definir el contrato de signals en el design (y no dejarlo al criterio del
implementador) garantiza que la UI y los workers se integren sin ambigüedad.

---

### Decisión 4: Estructura de Repositorios

**Elección**: Tres repositorios separados, uno por grupo de responsabilidad.

```
repositorio_licitaciones.py  → entidad operativa principal
repositorio_reglas.py        → configuración del scoring (palabras clave + organismos)
repositorio_configuracion.py → configuración de la app (piloto automático)
```

**Alternativas descartadas**: Repositorio único para todas las entidades (un
solo archivo acumula demasiadas responsabilidades conforme crece el proyecto),
un repositorio por cada tabla individual (overkill para este tamaño).

**Rationale**: `RepositorioReglas` agrupa organismos y palabras clave porque
ambos son configuración del motor de scoring, no entidades operativas. Tenerlos
juntos facilita que el `ScoringWorker` cargue toda la configuración en una sola
llamada. `RepositorioConfiguracion` es independiente porque su propósito es
persistir estado de la aplicación, no datos de negocio.

---

### Decisión 5: Persistencia de Configuración del Piloto Automático

**Elección**: Tabla `configuracion` en PostgreSQL con claves predefinidas.

```python
# Claves usadas por el sistema:
PILOTO_ACTIVO           = "piloto_activo"           # "true" | "false"
PILOTO_HORA             = "piloto_hora"              # "22:30"
PILOTO_ULTIMA_EJECUCION = "piloto_ultima_ejecucion"  # "2026-05-10"
PILOTO_ULTIMO_ERROR     = "piloto_ultimo_error"      # texto libre | ""

# Modelo:
class Configuracion(Base):
    __tablename__ = "configuracion"
    clave               = Column(String(50), primary_key=True)
    valor               = Column(Text)
    fecha_actualizacion = Column(DateTime, default=func.now(), onupdate=func.now())
```

**Hora por defecto**: **22:30** — alineada con la recomendación oficial de
ChileCompra de ejecutar procesos de alta demanda entre las 22:00 y las 07:00.
La UI debe mostrar esta recomendación al usuario como texto informativo junto al
selector de hora.

**Alternativas descartadas**: Archivo JSON en filesystem, QSettings de Qt,
variables en `.env`.

**Rationale**: El SPEC establece explícitamente la tabla `configuracion` para
persistir el estado del piloto entre reinicios. Centralizar la persistencia en
BD evita múltiples puntos de falla (archivos que pueden no existir, permisos de
escritura, rutas dependientes del OS).

---

### Decisión 6: Contrato del PilotoWorker

**Problema a resolver**: El piloto automático necesita sobrevivir reinicios de
la app y ejecutarse de forma confiable a una hora configurada, con reintentos
ante fallos, sin bloquear la UI.

**Elección**: `PilotoWorker(QThread)` con ciclo de vida propio que persiste su
estado en BD y se comunica con la UI exclusivamente mediante signals.

```python
class PilotoWorker(QThread):
    """
    Ciclo de vida:
    1. Al iniciar: lee configuracion desde BD
    2. Entra en loop: duerme 60 segundos, despierta, evalúa condición
    3. Si es hora Y no ejecutó hoy: lanza extracción del día anterior
    4. Si éxito: persiste fecha en BD, emite extraccion_completada
    5. Si falla: reintenta x3 con backoff 5/10/20 minutos
    6. Si agota reintentos: persiste error en BD, emite error_ocurrido
    """

    estado_cambiado      = Signal(str)
    extraccion_iniciada  = Signal()
    extraccion_completada = Signal()
    error_ocurrido       = Signal(str)

    def run(self):
        while self._ejecutando:
            activo = self._repo_config.obtener(PILOTO_ACTIVO) == "true"
            hora   = self._repo_config.obtener(PILOTO_HORA) or "22:30"
            ultima = self._repo_config.obtener(PILOTO_ULTIMA_EJECUCION)
            ahora  = datetime.now()

            if activo and self._es_hora(ahora, hora):
                if str(ahora.date()) != ultima:
                    self._ejecutar_con_reintentos(ahora)

            self._sleep_interrumpible(60)

    def _sleep_interrumpible(self, segundos: int):
        """Permite que detener() interrumpa el sleep sin esperar el ciclo completo."""
        for _ in range(segundos):
            if not self._ejecutando:
                break
            time.sleep(1)

    def detener(self):
        self._ejecutando = False
```

**Interacción con UI**: La UI solo escucha signals y llama a `detener()`. La
configuración (hora, activar/desactivar) se persiste en BD directamente desde
la UI. El worker la lee en cada ciclo, por lo que los cambios del usuario se
reflejan sin necesidad de reiniciar el worker.

---

### Decisión 7: Validación de Credenciales al Inicio

**Elección**: Validación fail-fast al inicio de `main()` antes de levantar la UI.

```python
def main():
    config = cargar_configuracion()  # carga .env con python-dotenv

    errores = []
    if not config.get('DATABASE_URL'):
        errores.append("DATABASE_URL")
    if not config.get('TICKET_MERCADO_PUBLICO'):
        errores.append("TICKET_MERCADO_PUBLICO")

    if errores:
        mensaje = "\n".join([
            "FALTA CONFIGURACIÓN REQUERIDA:",
            *[f"  - {e}: no encontrada en .env" for e in errores],
            f"\nEdite el archivo: {Path('.env').resolve()}"
        ])
        sys.exit(mensaje)

    iniciar_app()
```

**Alternativas descartadas**: Validación lazy al primer uso, validación async en
background con notificación en UI.

**Rationale**: El PRD establece "Fail-fast en configuración". El usuario debe
saber exactamente qué falta y dónde configurarlo antes de que la app levante
cualquier ventana. Un error silencioso durante la primera extracción es mucho
más confuso.

---

## Features Obligatorios del PRD

### Feature A: Búsqueda y Filtro de Texto en Listados

El PRD establece: *"Las vistas de listado deben tener búsqueda o filtro de
texto."*

**Implementación en repositorio**:
```python
# repositorio_licitaciones.py
def buscar_por_texto(
    self,
    texto: str,
    etapa: str,
    pagina: int = 0,
    por_pagina: int = 50
) -> list[Licitacion]:
    """
    Busca en campos nombre y descripcion usando ILIKE (case-insensitive).
    Combina con filtro de etapa y soporta paginación.
    """
    patron = f"%{texto}%"
    return (
        sesion.query(Licitacion)
        .filter(Licitacion.etapa == etapa)
        .filter(
            or_(
                Licitacion.nombre.ilike(patron),
                Licitacion.descripcion.ilike(patron)
            )
        )
        .order_by(Licitacion.score_total.desc())
        .offset(pagina * por_pagina)
        .limit(por_pagina)
        .all()
    )
```

**Implementación en UI** (`filtro_busqueda.py`):
- `QLineEdit` con placeholder *"Filtrar por nombre o descripción..."*
- Dispara búsqueda con debounce de 300ms usando `QTimer.singleShot` para no
  consultar en cada tecla
- Si el campo está vacío, llama a `obtener_por_etapa()` normal
- La paginación se resetea a página 0 cada vez que cambia el texto del filtro

---

### Feature B: Indicadores de Cantidad por Etapa

El PRD establece: *"Debe existir un indicador visible de cuántas licitaciones
hay en cada etapa del pipeline."*

**Implementación en repositorio**:
```python
# repositorio_licitaciones.py
def contar_por_etapa(self) -> dict[str, int]:
    """
    Retorna conteo de licitaciones por etapa activa.
    Solo cuenta etapas operativas (no 'ignorada').
    """
    etapas_activas = ['candidata', 'seguimiento', 'ofertada']
    resultado = (
        sesion.query(Licitacion.etapa, func.count(Licitacion.id))
        .filter(Licitacion.etapa.in_(etapas_activas))
        .group_by(Licitacion.etapa)
        .all()
    )
    conteos = {etapa: 0 for etapa in etapas_activas}
    for etapa, count in resultado:
        conteos[etapa] = count
    return conteos
```

**Implementación en UI** (`indicadores_pipeline.py`):
- Tres `QLabel` en el menú lateral, uno por etapa
- Formato: `"Candidatas (47)"`, `"Seguimiento (12)"`, `"Ofertadas (3)"`
- Se actualiza en tres momentos: al iniciar la app, cuando cualquier worker
  emite `finalizado`, y cuando el usuario mueve una licitación entre etapas
- `contar_por_etapa()` es una operación rápida (COUNT agrupado) que puede
  ejecutarse en el hilo principal sin bloquear la UI

---

## Data Flow

### Flujo 1: Extracción de Licitaciones

```
┌──────────────────────────────────────────────────────────────┐
│                      UI (Main Thread)                        │
│  ┌────────────┐    ┌──────────────────┐    ┌─────────────┐  │
│  │  Dialogo   │───→│ ExtraccionWorker │───→│ Actualizar  │  │
│  │  Extracc.  │    │   (QThread)      │    │ Vistas +    │  │
│  └────────────┘    └────────┬─────────┘    │ Indicadores │  │
└────────────────────────────┼──────────────└─────────────┘  ┘
                              │ signals (progreso, avance, error, finalizado)
          ┌───────────────────┴──────────────────┐
          ▼                                       ▼
┌──────────────────────┐           ┌──────────────────────────┐
│  API Mercado Público │           │    PostgreSQL Database   │
│                      │           │                          │
│ 1. listado_dia()     │           │ UPSERT licitacion        │
│ 2. detalle()         │           │ score_resumen            │
│    (si score > 0)    │           │ score_detalle            │
└──────────────────────┘           │ score_total              │
                                   └──────────────────────────┘
```

### Flujo 2: Scoring Recargable en Caliente

```
┌──────────────────────────────────────────────────────────────┐
│                      UI (Main Thread)                        │
│  ┌──────────────────┐    ┌─────────────────────────────┐    │
│  │ Guardar palabras │───→│ Signal: reglas_cambiadas     │    │
│  │ clave            │    └──────────────┬──────────────┘    │
└──────────────────────────────────────────┼───────────────────┘
                                           │
              ┌────────────────────────────┴────────────────────────┐
              ▼                                                      ▼
  ┌─────────────────────┐              ┌──────────────────────────────┐
  │   ScoringWorker     │              │   Domain (puro, sin deps)    │
  │   (QThread)         │              │                              │
  │                     │              │ snapshot = gestor.obtener()  │
  │ 1. Cargar reglas BD │─────────────→│ motor.evaluar_titulo(        │
  │ 2. Recargar gestor  │              │   texto, snapshot)           │
  │ 3. Query: etapas    │              │ motor.evaluar_detalle(        │
  │    activas +        │              │   desc, prods, snapshot)     │
  │    estado Publicada │              │ → (score, justificacion)     │
  │ 4. Evaluar por lotes│              └──────────────────────────────┘
  │ 5. Signal finalizado│
  │    → UI recarga     │
  │    las 3 pestañas   │
  └─────────────────────┘
```

### Flujo 3: Piloto Automático

```
App inicia
     │
     ▼
PilotoWorker.start()
     │
     ├── Lee configuracion desde BD
     │     ├── piloto_activo          = "true"/"false"
     │     ├── piloto_hora            = "22:30"
     │     └── piloto_ultima_ejecucion = "2026-05-10"
     │
     └── Loop cada 60s:
           │
           ├── Si activo Y es la hora Y no ejecutó hoy:
           │     ├── emite extraccion_iniciada
           │     ├── Lanza extracción (día anterior)
           │     ├── Si éxito: persiste fecha en BD
           │     │             emite extraccion_completada
           │     └── Si falla: reintento x3 (backoff 5/10/20 min)
           │           └── Si agota reintentos:
           │                 persiste error en BD
           │                 emite error_ocurrido
           │
           └── Si no activo: espera, no hace nada
```

---

## Archivos del Proyecto

| Archivo | Descripción |
|---------|-------------|
| `pyproject.toml` | Config Poetry + dependencias |
| `.env.example` | Template de variables de entorno |
| `src/monitor_licitaciones/__init__.py` | Package init |
| `src/monitor_licitaciones/main.py` | Entry point + fail-fast validation |
| `src/monitor_licitaciones/config.py` | Carga .env + constantes globales |
| `src/monitor_licitaciones/ui/__init__.py` | UI layer init |
| `src/monitor_licitaciones/ui/main_window.py` | Main window con pestañas e indicadores |
| `src/monitor_licitaciones/ui/widgets/__init__.py` | Widgets init |
| `src/monitor_licitaciones/ui/widgets/tabla_licitaciones.py` | Tabla con paginación y menú contextual |
| `src/monitor_licitaciones/ui/widgets/filtro_busqueda.py` | Input de filtro con debounce 300ms |
| `src/monitor_licitaciones/ui/widgets/indicadores_pipeline.py` | Contadores por etapa en menú lateral |
| `src/monitor_licitaciones/ui/dialogs/__init__.py` | Dialogs init |
| `src/monitor_licitaciones/ui/dialogs/config_palabras_clave.py` | Diálogo de palabras clave |
| `src/monitor_licitaciones/ui/dialogs/config_extraccion.py` | Diálogo de extracción |
| `src/monitor_licitaciones/ui/dialogs/config_exportacion.py` | Diálogo de exportación |
| `src/monitor_licitaciones/ui/dialogs/config_piloto.py` | Diálogo piloto (muestra nota ChileCompra) |
| `src/monitor_licitaciones/workers/__init__.py` | Workers init |
| `src/monitor_licitaciones/workers/extraccion_worker.py` | Extracción API (listado + detalle) |
| `src/monitor_licitaciones/workers/scoring_worker.py` | Recálculo de scores por lotes |
| `src/monitor_licitaciones/workers/exportacion_worker.py` | Export Excel/CSV con lotes |
| `src/monitor_licitaciones/workers/piloto_worker.py` | Ejecución automática programada |
| `src/monitor_licitaciones/domain/__init__.py` | Domain init |
| `src/monitor_licitaciones/domain/scoring/__init__.py` | Scoring init |
| `src/monitor_licitaciones/domain/scoring/motor_scoring.py` | Motor puro (recibe reglas como parámetro) |
| `src/monitor_licitaciones/domain/scoring/gestor_reglas.py` | Gestor thread-safe de reglas |
| `src/monitor_licitaciones/domain/pipeline/__init__.py` | Pipeline init |
| `src/monitor_licitaciones/domain/pipeline/gestor_pipeline.py` | Lógica de etapas y transiciones |
| `src/monitor_licitaciones/infrastructure/__init__.py` | Infra init |
| `src/monitor_licitaciones/infrastructure/database/__init__.py` | Database init |
| `src/monitor_licitaciones/infrastructure/database/models.py` | Modelos SQLAlchemy ORM |
| `src/monitor_licitaciones/infrastructure/database/connection.py` | Session manager (session-per-request) |
| `src/monitor_licitaciones/infrastructure/database/repositorio_licitaciones.py` | Repositorio de licitaciones |
| `src/monitor_licitaciones/infrastructure/database/repositorio_reglas.py` | Repositorio de palabras clave y organismos |
| `src/monitor_licitaciones/infrastructure/database/repositorio_configuracion.py` | Repositorio de configuración de app |
| `src/monitor_licitaciones/infrastructure/api/__init__.py` | API init |
| `src/monitor_licitaciones/infrastructure/api/cliente_mp.py` | Cliente HTTP Mercado Público |
| `src/monitor_licitaciones/cli/__init__.py` | CLI init |
| `src/monitor_licitaciones/cli/migrate.py` | Script migrate |
| `src/monitor_licitaciones/cli/init_db.py` | Script init-db |
| `src/monitor_licitaciones/cli/seed.py` | Script seed organismos |
| `alembic.ini` | Config Alembic |
| `alembic/env.py` | Entorno Alembic |
| `alembic/versions/001_initial.py` | Migración inicial (todas las tablas) |
| `tests/conftest.py` | Fixtures pytest |
| `tests/__init__.py` | Tests init |
| `tests/test_domain/__init__.py` | Tests domain init |
| `tests/test_domain/test_scoring.py` | Tests motor scoring (sin mocks, datos literales) |
| `tests/test_domain/test_pipeline.py` | Tests lógica de pipeline |
| `tests/test_infrastructure/__init__.py` | Tests infra init |
| `tests/test_infrastructure/test_repositorio_licitaciones.py` | Tests con SQLite in-memory |
| `tests/test_infrastructure/test_repositorio_reglas.py` | Tests con SQLite in-memory |
| `tests/test_workers/__init__.py` | Tests workers init |
| `tests/test_workers/test_extraccion.py` | Tests worker extracción (mock API) |
| `tests/test_workers/test_scoring.py` | Tests ScoringWorker con signals spy |
| `tests/test_workers/test_piloto.py` | Tests PilotoWorker con mock de datetime |

---

## Interfaces / Contratos

### Interfaz: RepositorioLicitaciones

```python
from typing import Protocol
from monitor_licitaciones.infrastructure.database.models import Licitacion

class RepositorioLicitaciones(Protocol):
    def obtener_por_etapa(
        self, etapa: str, pagina: int, por_pagina: int
    ) -> list[Licitacion]: ...

    def obtener_activas_en_pipeline(
        self, etapas: list[str], codigo_estado_activo: int
    ) -> list[Licitacion]: ...

    def buscar_por_texto(
        self, texto: str, etapa: str, pagina: int, por_pagina: int
    ) -> list[Licitacion]: ...

    def contar_por_etapa(self) -> dict[str, int]: ...

    def upsert(self, datos: dict) -> Licitacion: ...

    def actualizar_etapa(self, codigo_externo: str, etapa: str) -> bool: ...

    def actualizar_score(
        self,
        codigo_externo: str,
        score_resumen: int,
        score_detalle: int,
        score_total: int,
        justificacion: str
    ) -> bool: ...
```

### Interfaz: RepositorioReglas

```python
from monitor_licitaciones.infrastructure.database.models import PalabraClave, Organismo

class RepositorioReglas(Protocol):
    def obtener_palabras_clave(self) -> list[PalabraClave]: ...
    def guardar_palabra_clave(self, datos: dict) -> PalabraClave: ...
    def eliminar_palabra_clave(self, id: int) -> bool: ...
    def obtener_organismos(self) -> list[Organismo]: ...
    def actualizar_puntaje_organismo(self, codigo: str, puntaje: int) -> bool: ...
```

### Interfaz: RepositorioConfiguracion

```python
class RepositorioConfiguracion(Protocol):
    def obtener(self, clave: str) -> str | None: ...
    def guardar(self, clave: str, valor: str) -> None: ...
    def obtener_todas(self) -> dict[str, str]: ...
```

### Interfaz: ClienteAPI

```python
class ClienteAPI(Protocol):
    def obtener_licitaciones_dia(self, fecha: str) -> list[dict]: ...
    """fecha en formato DDMMYYYY. Una petición HTTP por día."""

    def obtener_detalle(self, codigo_externo: str) -> dict | None: ...
    """Retorna detalle completo o None si no encontrado / error definitivo."""

    def obtener_organismos(self) -> list[dict]: ...
    """Endpoint BuscarComprador. Usar solo en seed, no en extracción rutinaria."""
```

### Interfaz: MotorScoring

```python
from monitor_licitaciones.infrastructure.database.models import PalabraClave

class MotorScoring(Protocol):
    def evaluar_titulo(
        self, texto: str, reglas: list[PalabraClave]
    ) -> tuple[int, list[str]]: ...
    """Función pura. No tiene estado. No accede a BD."""

    def evaluar_detalle(
        self, descripcion: str, productos: str, reglas: list[PalabraClave]
    ) -> tuple[int, list[str]]: ...
    """Mismo contrato. Evalúa descripción y listado de productos."""
```

---

## Dependencias (pyproject.toml)

```toml
[tool.poetry.dependencies]
python          = ">=3.13,<3.15"
PySide6         = "^6.5.0"
SQLAlchemy      = "^2.0.0"
psycopg2-binary = "^2.9.0"
alembic         = "^1.12.0"
python-dotenv   = "^1.0.0"
requests        = "^2.31.0"
openpyxl        = "^3.1.0"
pandas          = "^2.0.0"
loguru          = "^0.7.0"
pydantic        = "^2.0.0"

[tool.poetry.group.dev.dependencies]
pytest          = "^9.0.0"
pytest-qt       = "^4.2.0"
pytest-cov      = "^4.1.0"
```

**Uso de Loguru**: configurado en `main.py` con sink a archivo rotativo
(`logs/monitor_{date}.log`) y sink a consola. Cada módulo importa
`from loguru import logger` directamente.

**Uso de Pydantic**: validación de los diccionarios crudos que devuelve la API
antes de pasarlos al repositorio, en `cliente_mp.py`. Evita que datos
malformados lleguen a la BD. No se usa en los modelos SQLAlchemy.

---

## Estrategia de Testing

| Capa | Qué testear | Enfoque |
|------|-------------|---------|
| Unit | Motor scoring (función pura) | pytest, datos literales, cero mocks |
| Unit | GestorReglas thread-safety | pytest + stress con lector y escritor simultáneos |
| Unit | Validación Pydantic respuestas API | pytest con dicts válidos e inválidos |
| Integration | RepositorioLicitaciones | pytest + SQLite in-memory |
| Integration | RepositorioReglas | pytest + SQLite in-memory |
| Integration | Cliente API | pytest + `responses` library (mock HTTP) |
| Integration | ScoringWorker | pytest-qt + QSignalSpy |
| Integration | PilotoWorker | pytest-qt + mock de `datetime.now()` |
| E2E | Flujo extracción → scoring → UI | pytest-qt + mock server |

---

## Setup para Nuevos Usuarios

```
1. Copiar .env.example a .env
   Configurar DATABASE_URL y TICKET_MERCADO_PUBLICO

2. poetry install

3. poetry run init-db
   (crea todas las tablas vía Alembic)

4. poetry run seed
   (carga catálogo de organismos desde endpoint BuscarComprador)

5. poetry run gui
   (inicia la aplicación)
```

---

## Orden de Implementación Sugerido

El agente implementador debe seguir este orden para evitar dependencias no
resueltas y poder testear cada capa antes de construir la siguiente:

```
1. models.py + connection.py
   → sin dependencias internas

2. repositorio_licitaciones.py
   repositorio_reglas.py
   repositorio_configuracion.py
   → dependen de 1

3. motor_scoring.py + gestor_reglas.py
   gestor_pipeline.py
   → sin dependencias (dominio puro, testeable desde aquí)

4. cliente_mp.py
   → sin dependencias internas

5. extraccion_worker.py   → depende de 2, 3, 4
   scoring_worker.py      → depende de 2, 3
   exportacion_worker.py  → depende de 2
   piloto_worker.py       → depende de 2, 5

6. Widgets y dialogs      → dependen de 2, 5

7. main_window.py + main.py → depende de todo

8. cli/seed.py            → depende de 2, 4
```

---

## Preguntas Abiertas

- [ ] **Verificar durante implementación**: Tipo de dato del campo
  `codigo_organismo` en respuestas reales de la API (definido como String por
  precaución; corregir si se confirma numérico).
- [ ] **Verificar durante implementación**: Consistencia del campo `Cantidad` en
  listados diarios (para logging; no bloquea el diseño).
- [ ] **Decisión de deploy**: Ubicación de logs — `logs/` en directorio de
  trabajo (más simple) vs `%APPDATA%/monitor_licitaciones/logs/` (más correcto
  en Windows). Recomendación: `logs/` en directorio de trabajo para primera
  versión.

---

*Documento de fase DESIGN — SDD*
*Proyecto: ML_AI | Mayo 2026*
