# Tasks: Monitor de Licitaciones - ML_AI

*Documento de fase TASKS — SDD*
*Proyecto: ML_AI*
*Fecha: Mayo 2026*

---

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 2500-3500+ |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 (Scaffolding + Foundation) → PR 2 (Domain) → PR 3 (Workers) → PR 4 (UI) → PR 5 (CLI + Entry Point) → PR 6 (E2E + Validación) |
| Delivery strategy | ask-on-risk |
| Chain strategy | stacked-to-main |

### Suggested Work Units

| Unit | Goal | PR | Notas |
|------|------|----|-------|
| 1 | Scaffolding + Foundation: estructura, dependencias, modelos, repositorios, conftest | PR 1 | Base branch. conftest incluido aquí para que todos los PRs siguientes puedan correr tests |
| 2 | Domain: motor scoring, gestor reglas, gestor pipeline + sus unit tests | PR 2 | Depende de PR 1. Dominio puro, testeable en aislamiento total |
| 3 | Workers: extraccion, scoring, exportacion, piloto + sus integration tests | PR 3 | Depende de PR 1, PR 2 |
| 4 | UI: widgets, dialogs, main window + tests de widgets | PR 4 | Depende de PR 1, PR 2, PR 3 |
| 5 | CLI + Entry Point: main.py, scripts CLI, README | PR 5 | Depende de PR 1 |
| 6 | E2E + Validación: tests end-to-end y validación Pydantic | PR 6 | Depende de todos los anteriores |

---

## Phase 1: Scaffolding + Foundation

> Esta fase crea todo lo que debe existir antes de que el agente pueda escribir
> cualquier línea de código de negocio. Las tareas 1.1–1.4 son prerrequisitos
> duros: sin ellas no se puede instalar dependencias, configurar Alembic ni
> correr ningún test.

### 1.1 Crear `pyproject.toml`

Crear con el siguiente contenido exacto. La sección `[tool.poetry.scripts]`
es obligatoria para que `poetry run gui|init-db|seed|migrate` funcionen.

```toml
[project]
name = "monitor-licitaciones"
version = "1.0.0"
description = "Monitor de Licitaciones - Mercado Público Chile"
requires-python = ">=3.13,<3.15"

[tool.poetry]
package-mode = false

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
responses       = "^0.25.0"

[tool.poetry.scripts]
gui      = "monitor_licitaciones.main:main"
init-db  = "monitor_licitaciones.cli.init_db:main"
migrate  = "monitor_licitaciones.cli.migrate:main"
seed     = "monitor_licitaciones.cli.seed:main"

[build-system]
requires      = ["poetry-core>=2.0.0,<3.0.0"]
build-backend = "poetry.core.masonry.api"
```

---

### 1.2 Crear `alembic.ini`

Archivo de configuración estándar de Alembic. La clave `sqlalchemy.url` se
sobreescribe en `alembic/env.py` desde la variable de entorno `DATABASE_URL`,
por lo que el valor literal aquí es solo un placeholder.

```ini
[alembic]
script_location = alembic
prepend_sys_path = .
path_separator = os

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARNING
handlers = console

[logger_sqlalchemy]
level = WARNING
handlers =

[logger_alembic]
level = INFO
handlers =

[handler_console]
class     = StreamHandler
args      = (sys.stderr,)
level     = NOTSET
formatter = generic

[formatter_generic]
format  = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

---

### 1.3 Crear `.env.example`

```env
# URL de conexión a PostgreSQL
# Formato: postgresql://usuario:contraseña@host:puerto/nombre_bd
DATABASE_URL=postgresql://usuario:contraseña@localhost:5432/monitor_licitaciones

# Ticket de autenticación de la API de Mercado Público
# Obtener en: https://api.mercadopublico.cl
TICKET_MERCADO_PUBLICO=tu_ticket_aqui
```

---

### 1.4 Crear estructura de directorios y archivos `__init__.py`

Crear todos los directorios y sus `__init__.py` vacíos. Esta tarea es
atómica: todos deben existir antes de continuar.

```
src/
└── monitor_licitaciones/
    ├── __init__.py
    ├── ui/
    │   ├── __init__.py
    │   ├── widgets/
    │   │   └── __init__.py
    │   └── dialogs/
    │       └── __init__.py
    ├── workers/
    │   └── __init__.py
    ├── domain/
    │   ├── __init__.py
    │   ├── scoring/
    │   │   └── __init__.py
    │   └── pipeline/
    │       └── __init__.py
    ├── infrastructure/
    │   ├── __init__.py
    │   ├── database/
    │   │   └── __init__.py
    │   └── api/
    │       └── __init__.py
    └── cli/
        └── __init__.py

tests/
├── __init__.py
├── test_domain/
│   └── __init__.py
├── test_infrastructure/
│   └── __init__.py
├── test_workers/
│   └── __init__.py
├── test_ui/
│   └── __init__.py
└── test_e2e/
    └── __init__.py
```

---

### 1.5 Crear `tests/conftest.py`

> **Crítico**: Este archivo debe existir antes de cualquier test en cualquier
> fase. Todos los fixtures compartidos viven aquí.

Fixtures requeridos:

- `engine` (scope=`session`): SQLite in-memory con `create_all` de todos los
  modelos. Usar `check_same_thread=False`.
- `session` (scope=`function`): Sesión SQLAlchemy que hace rollback al finalizar
  cada test para garantizar aislamiento.
- `qapp` (scope=`session`): `QApplication([])`. Solo una instancia por proceso.
  Usar `pytest_configure` o fixture con scope session para evitar conflictos con
  pytest-qt.
- `repo_licitaciones`: instancia de `RepositorioLicitaciones` inyectada con la
  session de test.
- `repo_reglas`: instancia de `RepositorioReglas` inyectada con la session de
  test.
- `repo_config`: instancia de `RepositorioConfiguracion` inyectada con la
  session de test.

---

### 1.6 Crear `src/monitor_licitaciones/config.py`

Responsabilidad: cargar variables de entorno y exponer constantes globales.

Contenido requerido:

```python
# Constantes de etapas del pipeline
ETAPA_CANDIDATA  = "candidata"
ETAPA_SEGUIMIENTO = "seguimiento"
ETAPA_OFERTADA   = "ofertada"
ETAPA_IGNORADA   = "ignorada"

ETAPAS_ACTIVAS = [ETAPA_CANDIDATA, ETAPA_SEGUIMIENTO, ETAPA_OFERTADA]

# Estado Publicada en la API de Mercado Público
CODIGO_ESTADO_PUBLICADA = 5

# Configuración de paginación
TAMANIO_PAGINA = 50

# Configuración del piloto automático
PILOTO_ACTIVO           = "piloto_activo"
PILOTO_HORA             = "piloto_hora"
PILOTO_HORA_DEFAULT     = "22:30"
PILOTO_ULTIMA_EJECUCION = "piloto_ultima_ejecucion"
PILOTO_ULTIMO_ERROR     = "piloto_ultimo_error"

# Configuración de la API
API_PAUSA_SEGUNDOS       = 2.0
API_MAX_INTENTOS         = 3
API_BASE_RETRASO         = 1.5
API_TIMEOUT_SEGUNDOS     = 15

# Configuración de exportación
EXPORT_CHUNK_SIZE        = 1000
```

---

### 1.7 Crear `src/monitor_licitaciones/infrastructure/database/models.py`

Modelos SQLAlchemy ORM. Campos obligatorios por modelo:

**Licitacion**:
- `id`: Integer PK autoincrement
- `codigo_externo`: String(50), unique, indexed
- `nombre`: String(500)
- `descripcion`: Text, nullable
- `detalle_productos`: Text, nullable
- `fecha_publicacion`: DateTime, nullable
- `fecha_cierre`: DateTime, nullable
- `fecha_inicio`: DateTime, nullable
- `fecha_adjudicacion`: DateTime, nullable
- `codigo_organismo`: String FK → `organismos.codigo`, nullable
- `codigo_estado`: Integer FK → `estados_licitacion.codigo`, nullable
- `score_resumen`: Integer, default 0 (puntos del título)
- `score_detalle`: Integer, default 0 (puntos de descripción + productos)
- `score_total`: Integer, default 0, indexed (suma total incluyendo organismo)
- `etapa`: String, default `"ignorada"` — valores: candidata/seguimiento/ofertada/ignorada
- `justificacion_score`: Text, nullable (auditoría legible de qué reglas aplicaron)
- `tiene_detalle`: Boolean, default False
- `fecha_extraccion`: DateTime, default `func.now()`
- `fecha_actualizacion`: DateTime, default `func.now()`, onupdate `func.now()`

**PalabraClave**:
- `id`: Integer PK autoincrement
- `termino`: String(100), indexed
- `categoria`: String(100), nullable
- `peso_titulo`: Integer, default 0
- `peso_descripcion`: Integer, default 0
- `peso_productos`: Integer, default 0
- `activa`: Boolean, default True

**Organismo**:
- `codigo`: String PK, indexed
- `nombre`: String(200), indexed
- `puntaje_fijo`: Integer, default 0

**EstadoLicitacion**:
- `id`: Integer PK
- `codigo`: Integer, unique
- `descripcion`: String(100)

**Configuracion**:
- `clave`: String(50) PK
- `valor`: Text
- `fecha_actualizacion`: DateTime, default `func.now()`, onupdate `func.now()`

---

### 1.8 Crear `src/monitor_licitaciones/infrastructure/database/connection.py`

Session manager con patrón session-per-request usando context manager.

```python
from contextlib import contextmanager

@contextmanager
def get_session():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
```

La `SessionLocal` se crea con `expire_on_commit=False` para evitar problemas
de lazy loading en workers con sesiones de corta vida.

---

### 1.9 Crear `src/monitor_licitaciones/infrastructure/database/repositorio_licitaciones.py`

Implementar todos los métodos del contrato `RepositorioLicitaciones` del design.
Especificaciones por método:

- `obtener_por_etapa(etapa, pagina, por_pagina)`: query con filtro de etapa,
  orden por `score_total DESC`, offset y limit.
- `obtener_activas_en_pipeline(etapas, codigo_estado_activo)`: filtro
  `etapa IN etapas AND codigo_estado = codigo_estado_activo`. Sin paginación,
  retorna todos los registros (usado por ScoringWorker).
- `buscar_por_texto(texto, etapa, pagina, por_pagina)`: ILIKE en `nombre` y
  `descripcion` con `OR`. Combinar con filtro de etapa. Orden por
  `score_total DESC`.
- `contar_por_etapa()`: `COUNT(*) GROUP BY etapa` solo para
  `ETAPAS_ACTIVAS`. Retornar dict con los tres valores aunque alguno sea 0.
- `upsert(datos)`: si existe `codigo_externo`, actualizar campos básicos
  siempre y campos de detalle solo si `tiene_detalle=True`. Si no existe,
  insertar. Regla de ascenso: si `etapa` actual es `"ignorada"` y la nueva
  es `"candidata"`, actualizar; nunca retroceder una etapa asignada
  manualmente.
- `actualizar_etapa(codigo_externo, etapa)`: UPDATE simple, retorna bool.
- `actualizar_score(codigo_externo, score_resumen, score_detalle,
  score_total, justificacion)`: UPDATE de los cuatro campos de score.

---

### 1.10 Crear `src/monitor_licitaciones/infrastructure/database/repositorio_reglas.py`

Implementar contrato `RepositorioReglas`:

- `obtener_palabras_clave()`: todas las `PalabraClave` donde `activa=True`.
- `guardar_palabra_clave(datos)`: INSERT si no tiene `id`, UPDATE si tiene.
- `eliminar_palabra_clave(id)`: soft delete (poner `activa=False`), no DELETE físico.
- `obtener_organismos()`: todos los organismos ordenados por nombre.
- `actualizar_puntaje_organismo(codigo, puntaje)`: UPDATE del campo
  `puntaje_fijo`.

---

### 1.11 Crear `src/monitor_licitaciones/infrastructure/database/repositorio_configuracion.py`

Implementar contrato `RepositorioConfiguracion`:

- `obtener(clave)`: SELECT por PK, retorna `valor` o `None`.
- `guardar(clave, valor)`: UPSERT por PK (INSERT or UPDATE).
- `obtener_todas()`: SELECT all, retorna dict `{clave: valor}`.

---

### 1.12 Crear entorno Alembic

Crear `alembic/env.py` que:
1. Agrega `src/` al `sys.path`
2. Importa `DATABASE_URL` desde `.env` usando `python-dotenv`
3. Sobreescribe `config.set_main_option("sqlalchemy.url", DATABASE_URL)`
4. Importa `Base` desde `models.py` para `target_metadata`

Crear `alembic/script.py.mako` con el template estándar de Alembic.

---

### 1.13 Crear migración inicial `alembic/versions/001_initial.py`

Migración que crea todas las tablas e índices:

Tablas: `licitaciones`, `palabras_clave`, `organismos`, `estados_licitacion`,
`configuracion`

Índices adicionales (además de los PK):
- `idx_licitacion_codigo_externo` (unique)
- `idx_licitacion_etapa`
- `idx_licitacion_score_total`
- `idx_palabra_clave_termino`
- `idx_organismo_codigo`

---

### 1.14 Crear `src/monitor_licitaciones/infrastructure/api/cliente_mp.py`

Implementar contrato `ClienteAPI` con:

- URL base: `https://api.mercadopublico.cl/servicios/v1/publico/licitaciones.json`
- Pausa mínima de `API_PAUSA_SEGUNDOS` entre peticiones (control de tasa).
- Reintentos con backoff exponencial (`API_BASE_RETRASO ** intento`) para
  errores 500 y errores de red. Máximo `API_MAX_INTENTOS` intentos.
- Timeout de `API_TIMEOUT_SEGUNDOS` en cada `requests.get()`.
- Validación Pydantic de la respuesta antes de retornar datos. Si la validación
  falla, loguear con Loguru y retornar `[]` o `None` según el método.
- Modelos Pydantic internos para validar la estructura de la respuesta:
  campos obligatorios de cada licitación en el listado y en el detalle.

---

### 1.15 Crear tests de integración para repositorios

**`tests/test_infrastructure/test_repositorio_licitaciones.py`**

Tests requeridos (usando fixtures de `conftest.py`):
- `test_upsert_inserta_nuevo`: verifica que una licitación nueva se inserta.
- `test_upsert_actualiza_existente`: misma licitación, segunda llamada actualiza.
- `test_upsert_no_retrocede_etapa`: si etapa es `"seguimiento"`, el upsert
  no la pisa con `"candidata"`.
- `test_obtener_por_etapa_paginacion`: retorna solo los de la etapa pedida,
  respeta limit y offset.
- `test_buscar_por_texto_ilike`: búsqueda case-insensitive en nombre y descripcion.
- `test_contar_por_etapa_retorna_ceros`: cuando no hay datos, retorna
  `{'candidata': 0, 'seguimiento': 0, 'ofertada': 0}`.
- `test_actualizar_etapa`: cambia etapa correctamente.
- `test_actualizar_score`: actualiza los tres campos de score.

**`tests/test_infrastructure/test_repositorio_reglas.py`**

Tests requeridos:
- `test_guardar_y_obtener_palabra_clave`: insert y select.
- `test_eliminar_palabra_clave_es_soft_delete`: después de eliminar, no aparece
  en `obtener_palabras_clave()` pero el registro sigue en BD con `activa=False`.
- `test_actualizar_puntaje_organismo`: verifica el UPDATE.

---

## Phase 2: Core Domain

> Todo el dominio es framework-agnostic. Ningún archivo de esta fase importa
> PySide6, SQLAlchemy ni requests. Los tests corren sin ningún mock de BD.

### 2.1 Crear `src/monitor_licitaciones/domain/scoring/motor_scoring.py`

Implementar función pura que evalúa textos contra una lista de reglas.

Requisitos:
- Precompilar patrones regex al recibir la lista de reglas (no en cada
  evaluación individual). Patrón: `rf"\b{re.escape(termino.lower())}\b"`.
- `evaluar_titulo(texto, reglas)`: buscar coincidencias en el texto del título.
  Sumar `peso_titulo` de cada regla que coincida. Retornar `(score, motivos)`
  donde `motivos` es lista de strings legibles: `"[TÍTULO] 'término' (+10)"`.
- `evaluar_detalle(descripcion, productos, reglas)`: buscar en descripción
  (`peso_descripcion`) y en texto de productos (`peso_productos`) por separado.
  Retornar `(score, motivos)`.
- Manejar `None` en cualquier texto de entrada sin lanzar excepción.
- No importar nada de `infrastructure`. Recibe `list[PalabraClave]` pero
  `PalabraClave` debe importarse solo desde `models.py` si es estrictamente
  necesario, o usar duck typing / TypedDict para mantener el dominio desacoplado.

---

### 2.2 Crear `src/monitor_licitaciones/domain/scoring/gestor_reglas.py`

Gestor thread-safe del estado compartido de reglas.

```python
class GestorReglas:
    def __init__(self):
        self._lock   = threading.Lock()
        self._reglas = []

    def recargar(self, reglas: list) -> None:
        with self._lock:
            self._reglas = list(reglas)   # copia defensiva

    def obtener_snapshot(self) -> list:
        with self._lock:
            return list(self._reglas)     # snapshot inmutable para el llamador
```

El snapshot debe hacerse antes de llamar al motor. El lock nunca debe mantenerse
durante la evaluación léxica.

---

### 2.3 Crear `src/monitor_licitaciones/domain/pipeline/gestor_pipeline.py`

Lógica de transiciones válidas entre etapas.

```python
TRANSICIONES_VALIDAS = {
    "candidata":   ["seguimiento", "ofertada"],
    "seguimiento": ["candidata", "ofertada"],
    "ofertada":    ["candidata", "seguimiento"],
    "ignorada":    ["candidata"],   # solo puede ascender automáticamente
}

class GestorPipeline:
    def es_transicion_valida(self, etapa_actual: str, etapa_destino: str) -> bool: ...
    def destinos_disponibles(self, etapa_actual: str) -> list[str]: ...
```

---

### 2.4 Crear `tests/test_domain/test_motor_scoring.py`

Tests de la función pura. Sin mocks, sin BD, solo datos literales.

Tests requeridos:
- `test_evaluar_titulo_coincidencia_simple`: un término, un match, score correcto.
- `test_evaluar_titulo_multiples_coincidencias`: dos términos en el texto,
  scores se suman.
- `test_evaluar_titulo_sin_coincidencias`: retorna `(0, [])`.
- `test_evaluar_titulo_case_insensitive`: "SILLA" coincide con regla "silla".
- `test_evaluar_titulo_texto_none`: retorna `(0, [])` sin excepción.
- `test_evaluar_titulo_solo_palabra_completa`: "computadoras" NO coincide con
  regla "computador" (boundary `\b`).
- `test_evaluar_detalle_descripcion_y_productos`: evalúa ambos campos
  independientemente y suma.
- `test_evaluar_detalle_textos_none`: retorna `(0, [])` sin excepción.
- `test_motivos_formato_legible`: los strings de motivos incluyen el término
  y el puntaje con signo.

---

### 2.5 Crear `tests/test_domain/test_gestor_reglas.py`

Tests de thread-safety. Separado de `test_motor_scoring.py`.

Tests requeridos:
- `test_obtener_snapshot_retorna_copia`: modificar el snapshot no afecta el
  estado interno del gestor.
- `test_recargar_actualiza_estado`: después de `recargar()`, `obtener_snapshot()`
  retorna las nuevas reglas.
- `test_concurrencia_lector_escritor`: lanzar 1 thread escritor (llama a
  `recargar()` en loop 100 veces) y 5 threads lectores (llaman a
  `obtener_snapshot()` en loop). Verificar que no hay excepciones ni
  condiciones de carrera en 3 segundos de ejecución.

---

### 2.6 Crear `tests/test_domain/test_gestor_pipeline.py`

Tests requeridos:
- `test_transicion_valida_candidata_a_seguimiento`.
- `test_transicion_invalida_lanza_error_o_retorna_false`.
- `test_destinos_disponibles_por_etapa`: para cada etapa, verifica la lista
  correcta de destinos.
- `test_ignorada_solo_puede_ir_a_candidata`.

---

## Phase 3: Workers

> Los workers orquestan el trabajo entre capas. No implementan lógica de
> negocio propia: delegan en el motor de scoring y en los repositorios.

### 3.1 Crear `src/monitor_licitaciones/workers/extraccion_worker.py`

Signals requeridos:
```python
progreso   = Signal(str)       # mensaje de estado
avance     = Signal(int, int)  # procesadas, total
finalizado = Signal()
error      = Signal(str)
```

Lógica del método `run()`:
1. Para cada día en el rango `fecha_inicio → fecha_fin`:
   - Llamar `cliente_mp.obtener_licitaciones_dia(fecha)` (1 petición HTTP).
   - Para cada licitación del listado, evaluar título con `motor.evaluar_titulo()`.
   - Si `score_resumen > 0`: llamar `cliente_mp.obtener_detalle(codigo)`,
     evaluar descripción y productos, calcular `score_total = score_resumen +
     score_detalle + puntaje_organismo`.
   - Llamar `repo_licitaciones.upsert(datos)` — el worker NO implementa
     lógica de UPSERT propia.
   - Emitir `avance` cada 10 licitaciones procesadas.
2. Emitir `finalizado` al terminar el rango.

El worker debe tener un flag `_ejecutando = True` con método `detener()` que
lo pone en `False`. El loop debe verificar este flag en cada iteración para
permitir cancelación.

---

### 3.2 Crear `src/monitor_licitaciones/workers/scoring_worker.py`

Signals:
```python
progreso   = Signal(str)
avance     = Signal(int, int)
finalizado = Signal()          # UI debe recargar las 3 pestañas
error      = Signal(str)
```

Lógica del método `run()`:
1. Cargar reglas actualizadas desde `repo_reglas.obtener_palabras_clave()`.
2. Llamar `gestor_reglas.recargar(reglas)`.
3. Llamar `repo_licitaciones.obtener_activas_en_pipeline(ETAPAS_ACTIVAS,
   CODIGO_ESTADO_PUBLICADA)`.
4. Para cada licitación, tomar `snapshot = gestor_reglas.obtener_snapshot()`.
5. Evaluar título, descripción y productos con el motor.
6. Calcular `score_total` sumando puntaje del organismo (desde
   `repo_reglas.obtener_organismos()`).
7. Llamar `repo_licitaciones.actualizar_score(...)`.
8. Emitir `avance` cada 25 licitaciones.

---

### 3.3 Crear `src/monitor_licitaciones/workers/exportacion_worker.py`

Signals:
```python
avance     = Signal(int, int)  # chunks procesados, total estimado
finalizado = Signal(str)       # ruta del archivo generado
error      = Signal(str)
```

Lógica:
- Procesar en chunks de `EXPORT_CHUNK_SIZE` usando paginación del repositorio.
- Para CSV: modo append (`mode='a'`) con cabecera solo en el primer chunk.
- Para Excel: acumular DataFrames y escribir al final con `pd.concat`.
- Limpiar zonas horarias de columnas datetime antes de escribir
  (`dt.tz_localize(None)`).
- El nombre del archivo incluye timestamp: `Reporte_YYYY-MM-DD_HH-MM-SS.xlsx/csv`.

---

### 3.4 Crear `src/monitor_licitaciones/workers/piloto_worker.py`

Signals:
```python
estado_cambiado      = Signal(str)
extraccion_iniciada  = Signal()
extraccion_completada = Signal()
error_ocurrido       = Signal(str)
```

Lógica del método `run()`:
```python
while self._ejecutando:
    config = repo_config.obtener_todas()
    activo = config.get(PILOTO_ACTIVO) == "true"
    hora   = config.get(PILOTO_HORA) or PILOTO_HORA_DEFAULT   # "22:30"
    ultima = config.get(PILOTO_ULTIMA_EJECUCION)
    ahora  = datetime.now()

    if activo and self._es_hora(ahora, hora):
        if str(ahora.date()) != ultima:
            self._ejecutar_con_reintentos(ahora)

    self._sleep_interrumpible(60)
```

`_sleep_interrumpible(segundos)`: loop de 1 segundo verificando `_ejecutando`.
Esto permite que `detener()` interrumpa el sleep sin esperar el ciclo completo.

`_ejecutar_con_reintentos(ahora)`: máximo 3 reintentos con backoff de
5, 10 y 20 minutos. Si éxito: persiste fecha en BD. Si agota reintentos:
persiste error en BD y emite `error_ocurrido`.

Regla crítica: el worker lee la configuración de BD en cada ciclo. La UI
no necesita reiniciar el worker cuando el usuario cambia la hora o
activa/desactiva el piloto — el cambio se refleja en el siguiente ciclo.

---

### 3.5 Crear `tests/test_workers/test_extraccion_worker.py`

Tests con mocks de `ClienteAPI` y `RepositorioLicitaciones`. Usar
`QSignalSpy` de pytest-qt.

Tests requeridos:
- `test_emite_finalizado_al_completar_rango`: mock de API que retorna
  lista vacía, verificar que `finalizado` se emite.
- `test_licitacion_con_score_cero_no_descarga_detalle`: mock de evaluación
  con score 0, verificar que `obtener_detalle` nunca se llama.
- `test_licitacion_con_score_positivo_descarga_detalle`: verificar que
  `obtener_detalle` sí se llama.
- `test_detener_interrumpe_el_loop`: llamar `detener()` durante la ejecución,
  verificar que el worker para antes de procesar todos los días.
- `test_error_api_500_reintenta`: mock que lanza error en primera llamada
  y tiene éxito en la segunda, verificar que no emite `error`.

---

### 3.6 Crear `tests/test_workers/test_scoring_worker.py`

Tests requeridos:
- `test_recalcula_solo_licitaciones_activas`: mock de repositorio que
  retorna una mezcla de etapas, verificar que `actualizar_score` solo se
  llama para las activas.
- `test_emite_avance_cada_25`: con 50 licitaciones mock, verificar que
  `avance` se emite exactamente 2 veces.
- `test_emite_finalizado`: verificar que siempre emite `finalizado` al terminar.

---

### 3.7 Crear `tests/test_workers/test_piloto_worker.py`

Tests requeridos:
- `test_no_ejecuta_si_ya_se_ejecuto_hoy`: mock de `repo_config` con
  `piloto_ultima_ejecucion` igual a hoy, verificar que no se lanza extracción.
- `test_ejecuta_si_es_la_hora_y_no_se_ejecuto`: mock de hora que coincide
  y fecha distinta, verificar que `extraccion_iniciada` se emite.
- `test_sleep_interrumpible_responde_a_detener`: llamar `detener()` durante
  el sleep, verificar que el worker termina en menos de 2 segundos.
- `test_persiste_error_tras_agotar_reintentos`: mock de extracción que
  siempre falla, verificar que `repo_config.guardar(PILOTO_ULTIMO_ERROR, ...)`
  se llama y `error_ocurrido` se emite.

---

## Phase 4: UI

> La UI no accede directamente a la BD. Toda operación de datos pasa por un
> worker o por una llamada directa al repositorio para operaciones síncronas
> simples (actualizar etapa es un UPDATE rápido, no necesita worker).

### 4.1 Crear `src/monitor_licitaciones/ui/widgets/tabla_licitaciones.py`

Widget reutilizable que muestra una lista paginada de licitaciones.

Requisitos:
- `QTableWidget` con columnas: Puntaje Total, Código, Nombre, Fecha Cierre,
  Estado.
- Selección por fila completa, solo lectura.
- Menú contextual con clic derecho que muestra las etapas de destino válidas
  según `GestorPipeline.destinos_disponibles(etapa_actual)`.
- Doble clic en fila abre diálogo de ficha técnica (detalle de licitación).
- Botonera de paginación: Anterior / `Página N` / Siguiente.
- Botón Siguiente deshabilitado si el número de filas es menor que
  `TAMANIO_PAGINA` (indica última página).
- Señal `etapa_cambiada = Signal(str, str)` emitida cuando el usuario mueve
  una licitación: `(codigo_externo, nueva_etapa)`.
- Texto de ayuda visible: *"Clic derecho sobre una fila para mover la
  licitación entre etapas."*

---

### 4.2 Crear `src/monitor_licitaciones/ui/widgets/filtro_busqueda.py`

Requisitos:
- `QLineEdit` con placeholder `"Filtrar por nombre o descripción..."`.
- Debounce de 300ms usando `QTimer.singleShot`: cada vez que el texto cambia,
  cancelar el timer anterior y crear uno nuevo. Al dispararse, emitir
  `Signal(str)` con el texto actual.
- Si el texto queda vacío, emitir `Signal("")` para que la vista cargue sin
  filtro.
- Señal: `texto_cambiado = Signal(str)`.

---

### 4.3 Crear `src/monitor_licitaciones/ui/widgets/indicadores_pipeline.py`

Requisitos:
- Tres `QLabel` que muestran: `"Candidatas (N)"`, `"Seguimiento (N)"`,
  `"Ofertadas (N)"`.
- Método público `actualizar()` que llama a
  `repo_licitaciones.contar_por_etapa()` y actualiza los tres labels.
- `actualizar()` debe llamarse en tres momentos (la main window es responsable
  de conectar estas señales):
  1. Al iniciar la app.
  2. Cuando cualquier worker emite `finalizado`.
  3. Cuando la tabla emite `etapa_cambiada`.

---

### 4.4 Crear `src/monitor_licitaciones/ui/dialogs/config_palabras_clave.py`

Diálogo para gestionar el diccionario de scoring.

Requisitos:
- Tabla con columnas: Término, Categoría, Peso Título, Peso Descripción,
  Peso Productos, Activa.
- Botones: Agregar, Editar (abre subdiálogo), Eliminar (soft delete).
- Al guardar cambios, emitir `Signal()` para que la main window lance el
  `ScoringWorker`.
- Señal: `reglas_cambiadas = Signal()`.

---

### 4.5 Crear `src/monitor_licitaciones/ui/dialogs/config_extraccion.py`

Requisitos:
- `QDateEdit` para fecha inicio y fecha fin con calendario popup.
- Validación: fecha inicio no puede ser posterior a fecha fin.
- Botón "Iniciar Extracción" que lanza `ExtraccionWorker`.
- Botón "Cancelar" visible solo durante extracción activa, llama a
  `worker.detener()`.
- Área de log (`QTextEdit` readonly) conectada a `worker.progreso`.
- Barra de progreso conectada a `worker.avance`.

---

### 4.6 Crear `src/monitor_licitaciones/ui/dialogs/config_exportacion.py`

Requisitos:
- Checkboxes para seleccionar etapas a exportar.
- Checkboxes para formato: Excel (`.xlsx`) y/o CSV.
- Validación: al menos una etapa y un formato seleccionados.
- `QFileDialog` para seleccionar directorio de destino.
- Barra de progreso conectada a `worker.avance`.
- Al completar, mostrar diálogo con la ruta del archivo generado.

---

### 4.7 Crear `src/monitor_licitaciones/ui/dialogs/config_piloto.py`

Requisitos:
- `QTimeEdit` con formato `HH:mm` y valor inicial `22:30`.
- Texto informativo visible: *"ChileCompra recomienda ejecutar procesos de
  alta demanda entre las 22:00 y las 07:00 horas para mayor estabilidad."*
- Botón toggle "Activar / Desactivar Piloto Automático".
- Al activar/desactivar o cambiar la hora, guardar en BD mediante
  `repo_config.guardar()`.
- Label de estado que muestra el texto recibido por `piloto_worker.estado_cambiado`.
- Label de última ejecución leída desde `repo_config.obtener(PILOTO_ULTIMA_EJECUCION)`.

---

### 4.8 Crear `src/monitor_licitaciones/ui/main_window.py`

Ventana principal con estructura de pestañas.

Pestañas principales: `Candidatas`, `Seguimiento`, `Ofertadas`,
`Herramientas del Sistema`.

`Herramientas del Sistema` contiene sub-pestañas: `Extracción`, `Exportación`,
`Palabras Clave`, `Organismos`, `Piloto Automático`.

Responsabilidades de la main window:
- Instanciar y conectar el `PilotoWorker` al iniciar.
- Instanciar los `indicadores_pipeline` y conectarlos a las señales de workers
  y a `tabla.etapa_cambiada`.
- Conectar `config_palabras_clave.reglas_cambiadas` al lanzamiento del
  `ScoringWorker`.
- Conectar `ScoringWorker.finalizado` a la recarga de las tres pestañas de
  listado y a `indicadores.actualizar()`.
- Implementar lazy loading: cada pestaña carga sus datos solo cuando el
  usuario la visita por primera vez o cuando tiene el flag
  `necesita_actualizacion=True`.

---

### 4.9 Crear `tests/test_ui/test_widgets.py`

Tests con pytest-qt.

Tests requeridos:
- `test_filtro_busqueda_debounce`: simular texto rápido, verificar que la
  señal se emite una sola vez después del debounce.
- `test_filtro_busqueda_texto_vacio_emite_string_vacio`: verificar el caso
  vacío.
- `test_tabla_menu_contextual_muestra_destinos_correctos`: verificar que el
  menú muestra las etapas de destino según la etapa actual de la fila.
- `test_indicadores_actualizar_muestra_conteos`: mock de
  `contar_por_etapa()` que retorna valores, verificar texto de los labels.

---

## Phase 5: CLI + Entry Point

### 5.1 Crear `src/monitor_licitaciones/main.py`

Entry point de la aplicación con validación fail-fast.

```python
def main():
    load_dotenv()

    errores = []
    if not os.getenv("DATABASE_URL"):
        errores.append("DATABASE_URL")
    if not os.getenv("TICKET_MERCADO_PUBLICO"):
        errores.append("TICKET_MERCADO_PUBLICO")

    if errores:
        print("ERROR: Faltan variables de entorno requeridas:")
        for e in errores:
            print(f"  - {e}: no configurada en .env")
        print(f"\nEdite el archivo: {Path('.env').resolve()}")
        sys.exit(1)

    # Configurar Loguru
    logger.add(
        "logs/monitor_{time:YYYY-MM-DD}.log",
        rotation="1 day",
        retention="30 days",
        level="DEBUG",
        encoding="utf-8"
    )
    logger.add(sys.stdout, level="INFO")

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    ventana = MainWindow()
    ventana.show()
    sys.exit(app.exec())
```

---

### 5.2 Crear `src/monitor_licitaciones/cli/init_db.py`

Script que ejecuta las migraciones de Alembic programáticamente:

```python
def main():
    from alembic.config import Config
    from alembic import command
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
    print("Base de datos inicializada correctamente.")
```

---

### 5.3 Crear `src/monitor_licitaciones/cli/migrate.py`

Igual que `init_db.py` pero orientado a ejecutar migraciones pendientes sobre
una BD ya existente. Mismo comando `upgrade(cfg, "head")`.

---

### 5.4 Crear `src/monitor_licitaciones/cli/seed.py`

Script que carga el catálogo inicial de organismos. Estrategia:
1. Intentar desde el endpoint `BuscarComprador` de la API.
2. Si falla (sin conexión, sin ticket), intentar desde archivo
   `organismos.csv` en el directorio raíz.
3. Si ninguno está disponible, imprimir instrucciones claras y salir con
   código 1.

Para cada organismo: INSERT si no existe, skip si ya existe (no sobreescribir
`puntaje_fijo` configurado por el usuario).

---

### 5.5 Crear `README.md`

Documentar el proceso de setup en 5 pasos:

```
1. cp .env.example .env
   # Editar DATABASE_URL y TICKET_MERCADO_PUBLICO

2. poetry install

3. poetry run init-db

4. poetry run seed

5. poetry run gui
```

Incluir sección de troubleshooting con los errores más comunes:
- `DATABASE_URL not set`: qué editar
- `connection refused`: PostgreSQL no está corriendo
- `TICKET_MERCADO_PUBLICO not set`: dónde obtener el ticket

---

## Phase 6: E2E + Validación

### 6.1 Crear `tests/test_infrastructure/test_cliente_mp.py`

Tests con la librería `responses` (mock HTTP).

Tests requeridos:
- `test_obtener_licitaciones_dia_exitoso`: mock de respuesta 200 con
  payload válido, verificar que retorna lista parseada.
- `test_obtener_licitaciones_dia_respuesta_vacia`: payload sin "Listado",
  retorna `[]`.
- `test_obtener_detalle_no_encontrado`: mock 404, retorna `None`.
- `test_obtener_detalle_reintenta_en_error_500`: mock 500 seguido de 200,
  verifica que la segunda llamada retorna los datos.
- `test_obtener_detalle_agota_reintentos`: mock de 500 en todos los intentos,
  retorna `None` sin lanzar excepción.
- `test_pausa_entre_peticiones`: verificar que hay al menos
  `API_PAUSA_SEGUNDOS` de pausa entre llamadas consecutivas.

---

### 6.2 Crear `tests/test_e2e/test_flujo_completo.py`

Test end-to-end del flujo principal: extracción → scoring → persistencia.

```
Dado: reglas configuradas (2 palabras clave con pesos)
Y:   mock de API que retorna 3 licitaciones (1 con coincidencia en título)
Cuando: se ejecuta ExtraccionWorker completo
Entonces:
  - La licitación con coincidencia tiene score_resumen > 0
  - Se llamó a obtener_detalle solo para esa licitación
  - La licitación está en BD con etapa "candidata"
  - Las otras 2 están en BD con etapa "ignorada"
```

---

### 6.3 Crear `tests/test_e2e/test_validacion_pydantic.py`

Tests de los modelos Pydantic que validan respuestas de la API.

Tests requeridos:
- `test_payload_valido_listado`: payload completo con todos los campos,
  sin error de validación.
- `test_payload_falta_campo_obligatorio`: falta `CodigoExterno`, debe
  lanzar `ValidationError`.
- `test_payload_tipo_incorrecto`: campo numérico con string, debe lanzar
  `ValidationError` o hacer coerción según el modelo.
- `test_payload_fecha_malformada`: fecha que no es ISO, el campo debe
  quedar `None` y no lanzar excepción (manejo tolerante de fechas).

---

### 6.4 Configurar `pytest-cov`

Agregar configuración en `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts   = "--cov=src/monitor_licitaciones --cov-report=term-missing"

[tool.coverage.run]
omit = ["*/cli/*", "*/main.py"]
```

Umbral mínimo de cobertura aceptable: 80% en capas `domain` e
`infrastructure/database`. Los workers y la UI tienen menor prioridad
de cobertura por su dependencia de Qt.

---

## Resumen de Dependencias entre Fases

```
Phase 1 (Scaffolding + Foundation)
   └── Phase 2 (Domain)          ← depende de models.py (1.7)
         └── Phase 3 (Workers)   ← depende de domain (2.x) + repos (1.9–1.11)
               └── Phase 4 (UI)  ← depende de workers (3.x)
Phase 1 └── Phase 5 (CLI)        ← depende de repos (1.9–1.11)
All     └── Phase 6 (E2E)        ← depende de todo
```

El `conftest.py` (tarea 1.5) es prerrequisito de todas las tareas de test
en fases 2, 3, 4 y 6.

---

*Documento de fase TASKS — SDD*
*Proyecto: ML_AI | Mayo 2026*
