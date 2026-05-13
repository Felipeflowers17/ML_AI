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
| Suggested split | PR 1 → PR 2 → PR 3 → PR 4 → PR 5 → PR 6 |
| Delivery strategy | ask-on-risk |
| Chain strategy | stacked-to-main |

### Suggested Work Units

| Unit | Goal | PR | Tamaño | Notas |
|------|------|----|--------|-------|
| 1 | Scaffolding + Foundation | PR 1 | L | Base branch. `conftest.py` incluido aquí |
| 2 | Domain | PR 2 | M | Depende de PR 1. Dominio puro |
| 3 | Workers | PR 3 | L | Depende de PR 1, PR 2 |
| 4 | UI | PR 4 | L | Depende de PR 1, PR 2, PR 3 |
| 5 | CLI + Entry Point | PR 5 | S | Depende de PR 1 |
| 6 | E2E + Validación | PR 6 | M | Depende de todos los anteriores |

### Rollback Plan

Si un PR falla sus tests en CI:
- El PR no se fusiona a main.
- Se corrige en la misma branch antes de reintentar.
- Los PRs siguientes de la cadena no avanzan hasta que el PR bloqueado pase.
- La cadena `stacked-to-main` garantiza que main siempre tiene código verde.

### Formato de Definition of Done

Cada tarea incluye una sección **DoD** con criterios medibles. Una tarea está
completa cuando todos sus criterios DoD se cumplen simultáneamente.

---

## Phase 1: Scaffolding + Foundation

> Esta fase crea todo lo que debe existir antes de cualquier código de negocio.
> Las tareas 1.1–1.4 son prerrequisitos duros: sin ellas no se puede instalar
> dependencias, configurar Alembic ni correr ningún test.

---

### 1.1 Crear `pyproject.toml` ✅

Crear con el siguiente contenido exacto. Incluye `ruff` para linting y
`responses` para tests HTTP.

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
ruff            = "^0.4.0"

[tool.poetry.scripts]
gui      = "monitor_licitaciones.main:main"
init-db  = "monitor_licitaciones.cli.init_db:main"
migrate  = "monitor_licitaciones.cli.migrate:main"
seed     = "monitor_licitaciones.cli.seed:main"

[tool.ruff]
line-length = 100
select      = ["E", "F", "I"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts   = "--cov=src/monitor_licitaciones --cov-report=term-missing --cov-fail-under=80"

[tool.coverage.run]
omit = ["*/cli/*", "*/main.py", "*/ui/*"]

[tool.coverage.report]
fail_under = 80

[build-system]
requires      = ["poetry-core>=2.0.0,<3.0.0"]
build-backend = "poetry.core.masonry.api"
```

**DoD**: `poetry install` completa sin errores. `poetry run ruff check src/`
no reporta errores en archivos vacíos de `__init__.py`.

---

### 1.2 Crear `alembic.ini` ✅

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
level    = WARNING
handlers = console

[logger_sqlalchemy]
level    = WARNING
handlers =

[logger_alembic]
level    = INFO
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

**DoD**: El archivo existe en la raíz del proyecto.

---

### 1.3 Crear `.env.example` ✅

```env
# URL de conexión a PostgreSQL
# Formato: postgresql://usuario:contraseña@host:puerto/nombre_bd
DATABASE_URL=postgresql://usuario:contraseña@localhost:5432/monitor_licitaciones

# Ticket de autenticación de la API de Mercado Público
# Obtener en: https://api.mercadopublico.cl
TICKET_MERCADO_PUBLICO=tu_ticket_aqui
```

**DoD**: El archivo existe en la raíz. No contiene credenciales reales.
Está listado en `.gitignore` junto con `.env`.

---

### 1.4 Crear estructura de directorios y `__init__.py` ✅

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

**Nota**: Para verificar que la estructura es correcta antes de continuar,
ejecutar `python -c "import monitor_licitaciones"` desde la raíz. Si no
lanza `ModuleNotFoundError`, la estructura es válida.

**DoD**: `python -c "import monitor_licitaciones"` ejecuta sin errores.
Todos los directorios y `__init__.py` listados existen.

---

### 1.5 Crear `tests/conftest.py` ✅

> **Crítico**: Debe existir antes de cualquier test en cualquier fase.
> Todos los fixtures compartidos viven aquí.

Fixtures requeridos:

- `engine` (scope=`session`): SQLite in-memory con `create_all` sobre
  todos los modelos. Parámetro `connect_args={"check_same_thread": False}`.
- `session` (scope=`function`): Sesión SQLAlchemy con rollback automático
  al finalizar cada test para garantizar aislamiento total entre tests.
- `qapp` (scope=`session`): `QApplication([])`. Una sola instancia por
  proceso de pytest.
- `repo_licitaciones` (scope=`function`): instancia de
  `RepositorioLicitaciones` inyectada con la `session` de test.
- `repo_reglas` (scope=`function`): instancia de `RepositorioReglas`
  inyectada con la `session` de test.
- `repo_config` (scope=`function`): instancia de `RepositorioConfiguracion`
  inyectada con la `session` de test.

**DoD**: `pytest tests/ --collect-only` ejecuta sin errores de importación.
Los fixtures `session`, `repo_licitaciones`, `repo_reglas` y `repo_config`
están disponibles en cualquier test sin importación adicional.

---

### 1.6 Crear `src/monitor_licitaciones/config.py` ✅

Responsabilidad única: constantes globales y carga de variables de entorno.
No contiene lógica de negocio.

```python
# Etapas del pipeline
ETAPA_CANDIDATA   = "candidata"
ETAPA_SEGUIMIENTO = "seguimiento"
ETAPA_OFERTADA    = "ofertada"
ETAPA_IGNORADA    = "ignorada"
ETAPAS_ACTIVAS    = [ETAPA_CANDIDATA, ETAPA_SEGUIMIENTO, ETAPA_OFERTADA]

# Estado Publicada en API de Mercado Público
CODIGO_ESTADO_PUBLICADA = 5

# Paginación
TAMANIO_PAGINA = 50

# Claves de configuración del piloto automático (tabla configuracion en BD)
PILOTO_ACTIVO            = "piloto_activo"
PILOTO_HORA              = "piloto_hora"
PILOTO_HORA_DEFAULT      = "22:30"
PILOTO_ULTIMA_EJECUCION  = "piloto_ultima_ejecucion"
PILOTO_ULTIMO_ERROR      = "piloto_ultimo_error"

# API de Mercado Público
API_PAUSA_SEGUNDOS   = 2.0
API_MAX_INTENTOS     = 3
API_BASE_RETRASO     = 1.5
API_TIMEOUT_SEGUNDOS = 15

# Exportación
EXPORT_CHUNK_SIZE = 1000
```

**DoD**: `tests/test_infrastructure/test_config.py` pasa (ver tarea 1.7).

---

### 1.7 Crear `tests/test_infrastructure/test_config.py` ✅

Tests que verifican que `config.py` tiene los valores correctos y que el
módulo carga sin errores de importación.

Tests requeridos:
- `test_etapas_activas_contiene_exactamente_tres_etapas`: verifica que
  `ETAPAS_ACTIVAS` tiene exactamente los valores `candidata`, `seguimiento`
  y `ofertada`.
- `test_etapas_activas_no_contiene_ignorada`: `"ignorada"` no debe estar
  en `ETAPAS_ACTIVAS`.
- `test_piloto_hora_default_es_22_30`: verifica el valor exacto `"22:30"`.
- `test_codigo_estado_publicada_es_5`: verifica el valor exacto `5`.
- `test_todas_las_constantes_son_strings_o_numeros`: verificar que ninguna
  constante es `None`.
- `test_fail_fast_con_database_url_faltante`: usando `monkeypatch` para
  borrar `DATABASE_URL` del entorno, verificar que `main.py` llama a
  `sys.exit(1)` antes de levantar la UI.
- `test_fail_fast_con_ticket_faltante`: mismo patrón para
  `TICKET_MERCADO_PUBLICO`.

**DoD**: Los 7 tests pasan con `pytest tests/test_infrastructure/test_config.py`.

---

### 1.8 Crear `src/monitor_licitaciones/infrastructure/database/models.py` ✅

Modelos SQLAlchemy ORM. Campos obligatorios:

**Licitacion**:
- `id`: Integer PK autoincrement
- `codigo_externo`: String(50), unique, indexed
- `nombre`: String(500)
- `descripcion`: Text, nullable
- `detalle_productos`: Text, nullable
- `fecha_publicacion`, `fecha_cierre`, `fecha_inicio`, `fecha_adjudicacion`:
  DateTime, nullable
- `codigo_organismo`: String FK → `organismos.codigo`, nullable
- `codigo_estado`: Integer FK → `estados_licitacion.codigo`, nullable
- `score_resumen`: Integer default 0 — puntos del título
- `score_detalle`: Integer default 0 — puntos de descripción + productos
- `score_total`: Integer default 0, indexed — suma total
- `etapa`: String default `"ignorada"`
- `justificacion_score`: Text, nullable
- `tiene_detalle`: Boolean default False
- `fecha_extraccion`: DateTime default `func.now()`
- `fecha_actualizacion`: DateTime default `func.now()`, onupdate `func.now()`

**PalabraClave**:
- `id`: Integer PK, `termino`: String(100) indexed, `categoria`: String(100)
  nullable, `peso_titulo`: Integer default 0, `peso_descripcion`: Integer
  default 0, `peso_productos`: Integer default 0, `activa`: Boolean default True

**Organismo**:
- `codigo`: String PK indexed, `nombre`: String(200) indexed,
  `puntaje_fijo`: Integer default 0

**EstadoLicitacion**:
- `id`: Integer PK, `codigo`: Integer unique, `descripcion`: String(100)

**Configuracion**:
- `clave`: String(50) PK, `valor`: Text,
  `fecha_actualizacion`: DateTime onupdate

**DoD**: `from monitor_licitaciones.infrastructure.database.models import
Licitacion, PalabraClave, Organismo, EstadoLicitacion, Configuracion`
ejecuta sin errores. Los 5 modelos tienen todos los campos listados.

---

### 1.9 Crear `src/monitor_licitaciones/infrastructure/database/connection.py` ✅

Session manager con patrón context manager. `expire_on_commit=False`.

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

**DoD**: El context manager abre y cierra sesión correctamente. Si ocurre
una excepción dentro del bloque `with`, hace rollback sin propagar el error
de rollback.

---

### 1.10 Crear `src/monitor_licitaciones/infrastructure/database/repositorio_licitaciones.py` ✅

Implementar todos los métodos del contrato `RepositorioLicitaciones`.

Especificaciones por método:
- `obtener_por_etapa(etapa, pagina, por_pagina)`: filtro de etapa, orden
  `score_total DESC`, offset y limit.
- `obtener_activas_en_pipeline(etapas, codigo_estado_activo)`: filtro
  `etapa IN etapas AND codigo_estado = codigo_estado_activo`. Sin paginación.
- `buscar_por_texto(texto, etapa, pagina, por_pagina)`: ILIKE en `nombre`
  OR `descripcion`. Combinar con filtro de etapa. Orden `score_total DESC`.
- `contar_por_etapa()`: `COUNT(*) GROUP BY etapa` solo para `ETAPAS_ACTIVAS`.
  Retornar `{'candidata': 0, 'seguimiento': 0, 'ofertada': 0}` aunque
  alguno sea cero.
- `upsert(datos)`: si existe `codigo_externo`, actualizar campos básicos
  siempre y campos de detalle solo si `tiene_detalle=True` en los datos
  nuevos. Regla de ascenso de etapa: solo si la etapa actual es `"ignorada"`
  y la nueva es `"candidata"`. Nunca retroceder una etapa asignada
  manualmente.
- `actualizar_etapa(codigo_externo, etapa)`: UPDATE simple, retorna bool.
- `actualizar_score(codigo_externo, score_resumen, score_detalle,
  score_total, justificacion)`: UPDATE de los cuatro campos de score.

**DoD**: `tests/test_infrastructure/test_repositorio_licitaciones.py`
pasa (ver tarea 1.13). Los 7 métodos del contrato están implementados.

---

### 1.11 Crear `src/monitor_licitaciones/infrastructure/database/repositorio_reglas.py` ✅

Implementar contrato `RepositorioReglas`:
- `obtener_palabras_clave()`: solo registros con `activa=True`.
- `guardar_palabra_clave(datos)`: INSERT si sin `id`, UPDATE si con `id`.
- `eliminar_palabra_clave(id)`: soft delete (`activa=False`), no DELETE físico.
- `obtener_organismos()`: todos, ordenados por `nombre`.
- `actualizar_puntaje_organismo(codigo, puntaje)`: UPDATE de `puntaje_fijo`.

**DoD**: `tests/test_infrastructure/test_repositorio_reglas.py` pasa
(ver tarea 1.14). Los 5 métodos están implementados.

---

### 1.12 Crear `src/monitor_licitaciones/infrastructure/database/repositorio_configuracion.py` ✅

Implementar contrato `RepositorioConfiguracion`:
- `obtener(clave)`: SELECT por PK, retorna `valor` o `None`.
- `guardar(clave, valor)`: UPSERT por PK.
- `obtener_todas()`: SELECT all, retorna `dict[str, str]`.

**DoD**: Los 3 métodos están implementados y usables desde los fixtures de
conftest.

---

### 1.13 Crear entorno Alembic ✅

Crear `alembic/env.py`:
1. Agrega `src/` al `sys.path`
2. Carga `DATABASE_URL` desde `.env` con `python-dotenv`
3. Sobreescribe `config.set_main_option("sqlalchemy.url", DATABASE_URL)`
4. Importa `Base` desde `models.py` para `target_metadata`

Crear `alembic/script.py.mako` con template estándar de Alembic.

**DoD**: `alembic/env.py` y `alembic/script.py.mako` existen y no tienen
errores de sintaxis.

---

### 1.14 Crear migración inicial `alembic/versions/001_initial.py` ✅

Tablas: `licitaciones`, `palabras_clave`, `organismos`, `estados_licitacion`,
`configuracion`.

Índices adicionales:
- `idx_licitacion_codigo_externo` (unique)
- `idx_licitacion_etapa`
- `idx_licitacion_score_total`
- `idx_palabra_clave_termino`
- `idx_organismo_codigo`

**DoD**: `alembic upgrade head` (sobre una BD PostgreSQL de test) completa
sin errores. `alembic downgrade base` revierte todas las tablas.

---

### 1.15 Crear `src/monitor_licitaciones/infrastructure/api/schemas_mp.py` ✅

> **Nota arquitectónica**: Los modelos Pydantic de validación de la API
> viven en `infrastructure/api/`, NO dentro de `cliente_mp.py`. Esto
> permite testearlos en aislamiento y reutilizarlos si el cliente cambia.

Modelos Pydantic requeridos:

```python
from pydantic import BaseModel, Field
from datetime import datetime

class OrganismoAPI(BaseModel):
    CodigoOrganismo: str
    NombreOrganismo: str

class ItemAPI(BaseModel):
    NombreProducto: str = ""
    Cantidad: float = 0
    UnidadMedida: str = ""
    Descripcion: str = ""

class LicitacionResumenAPI(BaseModel):
    """Modelo para cada elemento del listado diario."""
    CodigoExterno: str
    Nombre: str
    FechaCierre: str | None = None
    CodigoEstado: int | None = None
    Comprador: OrganismoAPI | None = None

class LicitacionDetalleAPI(BaseModel):
    """Modelo para la respuesta de detalle individual."""
    CodigoExterno: str
    Nombre: str
    Descripcion: str | None = None
    FechaCierre: str | None = None
    FechaInicio: str | None = None
    FechaPublicacion: str | None = None
    CodigoEstado: int | None = None
    Comprador: OrganismoAPI | None = None
    Items: dict | None = None  # estructura variable según la licitación

class RespuestaListadoAPI(BaseModel):
    """Envelope de la respuesta del listado diario."""
    Cantidad: int = 0
    Listado: list[LicitacionResumenAPI] = Field(default_factory=list)
```

Regla de validación: todos los campos opcionales deben tener `default=None`
o `default_factory`. La API gubernamental puede omitir campos sin previo
aviso — nunca lanzar `ValidationError` por campos faltantes, solo por
tipos incompatibles en campos presentes.

**DoD**: `tests/test_e2e/test_validacion_pydantic.py` pasa (ver tarea 6.3).
Los 5 modelos importan correctamente desde `schemas_mp.py`.

---

### 1.16 Crear `src/monitor_licitaciones/infrastructure/api/cliente_mp.py` ✅

Implementar contrato `ClienteAPI` usando los schemas de `schemas_mp.py`.

- URL base: `https://api.mercadopublico.cl/servicios/v1/publico/licitaciones.json`
- Pausa mínima de `API_PAUSA_SEGUNDOS` entre peticiones.
- Reintentos con backoff exponencial para errores 500 y errores de red.
  Máximo `API_MAX_INTENTOS` intentos.
- Timeout de `API_TIMEOUT_SEGUNDOS`.
- `obtener_licitaciones_dia(fecha)`: parsear con `RespuestaListadoAPI`,
  retornar `lista.Listado` como `list[dict]`. Si validación falla,
  loguear y retornar `[]`.
- `obtener_detalle(codigo_externo)`: parsear con `LicitacionDetalleAPI`,
  retornar como `dict` o `None`.
- `obtener_organismos()`: usar endpoint `BuscarComprador`. Solo para `seed`.

**DoD**: `tests/test_infrastructure/test_cliente_mp.py` pasa (ver tarea 6.1).
El cliente importa y usa `schemas_mp.py` para toda validación. No hay
validación Pydantic inline en el cliente.

---

### 1.17 Crear tests de integración de repositorios ✅

**`tests/test_infrastructure/test_repositorio_licitaciones.py`**

Tests requeridos:
- `test_upsert_inserta_nuevo`: licitación nueva se inserta correctamente.
- `test_upsert_actualiza_existente`: segunda llamada con mismo código actualiza.
- `test_upsert_no_retrocede_etapa_manual`: si etapa es `"seguimiento"`,
  upsert con `"candidata"` no la pisa.
- `test_upsert_asciende_de_ignorada_a_candidata`: si etapa es `"ignorada"`,
  upsert con `"candidata"` sí la actualiza.
- `test_obtener_por_etapa_paginacion`: respeta limit y offset, retorna
  solo la etapa pedida.
- `test_buscar_por_texto_ilike_case_insensitive`: búsqueda con mayúsculas
  encuentra coincidencia en minúsculas.
- `test_buscar_por_texto_en_nombre_y_descripcion`: el OR funciona en ambos
  campos.
- `test_contar_por_etapa_retorna_ceros_cuando_no_hay_datos`: retorna dict
  con los tres valores en cero.
- `test_contar_por_etapa_cuenta_correctamente`: con datos insertados,
  retorna los conteos correctos.
- `test_actualizar_etapa_existente`: actualiza y retorna `True`.
- `test_actualizar_etapa_inexistente`: retorna `False`.
- `test_actualizar_score_actualiza_tres_campos`: verifica `score_resumen`,
  `score_detalle` y `score_total` en BD.

**`tests/test_infrastructure/test_repositorio_reglas.py`**

Tests requeridos:
- `test_guardar_y_obtener_palabra_clave`: insert y select.
- `test_eliminar_es_soft_delete`: no aparece en `obtener_palabras_clave()`
  pero existe en BD con `activa=False`.
- `test_obtener_palabras_clave_excluye_inactivas`: reglas con `activa=False`
  no se incluyen.
- `test_actualizar_puntaje_organismo`: verifica el UPDATE en BD.

**DoD**: Todos los tests de ambos archivos pasan con `pytest
tests/test_infrastructure/`.

---

## Phase 2: Core Domain

> Todo el dominio es framework-agnostic. Ningún archivo de esta fase importa
> PySide6, SQLAlchemy ni `requests`. Los tests corren sin ningún mock de BD.

---

### 2.1 Crear `src/monitor_licitaciones/domain/scoring/tipos.py` ✅

> **Solución al acoplamiento dominio ↔ infraestructura**: El motor de scoring
> no puede importar `PalabraClave` de `models.py` porque eso crearía una
> dependencia del dominio hacia la infraestructura, violando la arquitectura
> por capas. En su lugar, el dominio define su propio tipo de datos con
> exactamente los campos que necesita. El mapping de `PalabraClave` →
> `ReglaScoring` ocurre en la capa de workers, que ya conoce ambas capas.

```python
from typing import TypedDict

class ReglaScoring(TypedDict):
    """
    Representación de una regla de scoring en la capa de dominio.
    El motor de scoring solo conoce este tipo, nunca PalabraClave.
    Los workers son responsables de mapear PalabraClave → ReglaScoring.
    """
    termino:          str
    peso_titulo:      int
    peso_descripcion: int
    peso_productos:   int
```

**DoD**: `from monitor_licitaciones.domain.scoring.tipos import ReglaScoring`
ejecuta sin errores. El archivo no importa nada de `infrastructure`.

---

### 2.2 Crear `src/monitor_licitaciones/domain/scoring/motor_scoring.py` ✅

Función pura que evalúa textos contra una lista de `ReglaScoring`.

Requisitos:
- Importar solo `ReglaScoring` desde `domain/scoring/tipos.py`. Cero
  imports de `infrastructure`.
- Precompilar patrones regex al inicio de cada llamada usando
  `re.compile(rf"\b{re.escape(regla['termino'].lower())}\b")`.
- `evaluar_titulo(texto, reglas)`: iterar reglas, buscar coincidencias,
  sumar `peso_titulo`. Retornar `(score_int, lista_motivos)`.
  Formato de motivo: `"[TÍTULO] 'término' (+10)"`.
- `evaluar_detalle(descripcion, productos, reglas)`: buscar en descripción
  con `peso_descripcion` y en productos con `peso_productos` por separado.
  Formato de motivos: `"[DESC] 'término' (+5)"` y `"[PROD] 'término' (+1)"`.
- Manejar `None` en cualquier texto sin lanzar excepción (tratar como `""`).

**DoD**: `tests/test_domain/test_motor_scoring.py` pasa (ver tarea 2.4).
El archivo no importa nada de `infrastructure`.

---

### 2.3 Crear `src/monitor_licitaciones/domain/scoring/gestor_reglas.py` ✅

Gestor thread-safe del estado compartido. Trabaja con `list[ReglaScoring]`.

```python
import threading
from monitor_licitaciones.domain.scoring.tipos import ReglaScoring

class GestorReglas:
    def __init__(self):
        self._lock   = threading.Lock()
        self._reglas: list[ReglaScoring] = []

    def recargar(self, reglas: list[ReglaScoring]) -> None:
        with self._lock:
            self._reglas = list(reglas)   # copia defensiva

    def obtener_snapshot(self) -> list[ReglaScoring]:
        with self._lock:
            return list(self._reglas)     # snapshot inmutable
```

El lock nunca se mantiene durante la evaluación léxica. El snapshot se
obtiene antes de llamar al motor y se pasa como parámetro.

**DoD**: `tests/test_domain/test_gestor_reglas.py` pasa (ver tarea 2.5).
El archivo no importa nada de `infrastructure`.

---

### 2.4 Crear `src/monitor_licitaciones/domain/pipeline/gestor_pipeline.py` ✅

Lógica de transiciones válidas entre etapas.

```python
TRANSICIONES_VALIDAS = {
    "candidata":   ["seguimiento", "ofertada"],
    "seguimiento": ["candidata",   "ofertada"],
    "ofertada":    ["candidata",   "seguimiento"],
    "ignorada":    ["candidata"],
}

class GestorPipeline:
    def es_transicion_valida(self, origen: str, destino: str) -> bool:
        return destino in TRANSICIONES_VALIDAS.get(origen, [])

    def destinos_disponibles(self, etapa_actual: str) -> list[str]:
        return TRANSICIONES_VALIDAS.get(etapa_actual, [])
```

**DoD**: `tests/test_domain/test_gestor_pipeline.py` pasa (ver tarea 2.6).

---

### 2.5 Crear `tests/test_domain/test_motor_scoring.py` ✅

Tests sin mocks, sin BD. Solo `ReglaScoring` con datos literales.

```python
# Fixture de reglas para todos los tests de este archivo
REGLAS_TEST = [
    ReglaScoring(termino="silla", peso_titulo=10, peso_descripcion=5, peso_productos=1),
    ReglaScoring(termino="mesa",  peso_titulo=20, peso_descripcion=10, peso_productos=2),
]
```

Tests requeridos:
- `test_evaluar_titulo_coincidencia_simple`: texto con "silla" → score 10.
- `test_evaluar_titulo_multiples_coincidencias`: "silla" y "mesa" → score 30.
- `test_evaluar_titulo_sin_coincidencias`: retorna `(0, [])`.
- `test_evaluar_titulo_case_insensitive`: "SILLA" coincide con regla "silla".
- `test_evaluar_titulo_texto_none`: retorna `(0, [])` sin excepción.
- `test_evaluar_titulo_boundary_palabra_completa`: "sillas" (plural) NO
  coincide con regla "silla" gracias al `\b`.
- `test_evaluar_detalle_descripcion`: texto en descripción suma
  `peso_descripcion`.
- `test_evaluar_detalle_productos`: texto en productos suma `peso_productos`.
- `test_evaluar_detalle_textos_none`: retorna `(0, [])` sin excepción.
- `test_motivos_incluyen_termino_y_puntaje_con_signo`: verificar que el
  string de motivo contiene el término y el puntaje con signo `+` o `-`.

**DoD**: Los 10 tests pasan. Ningún test importa nada de `infrastructure`.

---

### 2.6 Crear `tests/test_domain/test_gestor_reglas.py` ✅

Tests de thread-safety. Archivo separado de `test_motor_scoring.py`.

Tests requeridos:
- `test_snapshot_es_copia_independiente`: modificar el resultado de
  `obtener_snapshot()` no altera el estado interno del gestor.
- `test_recargar_actualiza_snapshot`: después de `recargar()` con nuevas
  reglas, `obtener_snapshot()` retorna las nuevas.
- `test_recargar_con_lista_vacia`: `obtener_snapshot()` retorna `[]`.
- `test_concurrencia_lector_escritor`: lanzar 1 thread escritor (llama a
  `recargar()` en loop durante 2 segundos) y 5 threads lectores (llaman a
  `obtener_snapshot()` en loop). Verificar que no hay excepciones en ningún
  thread. Usar `threading.Thread` y capturar excepciones con una lista
  compartida protegida por lock.

**DoD**: Los 4 tests pasan. El test de concurrencia no falla en 10
ejecuciones consecutivas.

---

### 2.7 Crear `tests/test_domain/test_gestor_pipeline.py` ✅

Tests requeridos:
- `test_transicion_valida_candidata_seguimiento`.
- `test_transicion_valida_candidata_ofertada`.
- `test_transicion_invalida_retorna_false`: `"ignorada"` →
  `"seguimiento"` es inválida.
- `test_ignorada_solo_puede_ir_a_candidata`.
- `test_destinos_disponibles_candidata`: retorna exactamente
  `["seguimiento", "ofertada"]`.
- `test_destinos_disponibles_etapa_desconocida`: retorna `[]`.

**DoD**: Los 6 tests pasan.

---

## Phase 3: Workers

> Los workers orquestan el trabajo entre capas. No implementan lógica de
> negocio propia. Son responsables del mapping `PalabraClave → ReglaScoring`
> antes de llamar al motor de scoring.

### Función de mapping compartida

Crear en `src/monitor_licitaciones/workers/__init__.py` (o en un módulo
`workers/utils.py`):

```python
from monitor_licitaciones.domain.scoring.tipos import ReglaScoring
from monitor_licitaciones.infrastructure.database.models import PalabraClave

def mapear_reglas(palabras: list[PalabraClave]) -> list[ReglaScoring]:
    return [
        ReglaScoring(
            termino=p.termino,
            peso_titulo=p.peso_titulo,
            peso_descripcion=p.peso_descripcion,
            peso_productos=p.peso_productos,
        )
        for p in palabras
        if p.activa
    ]
```

Esta función es el único punto donde `PalabraClave` se convierte en
`ReglaScoring`. Todos los workers la usan.

---

### 3.1 Crear `src/monitor_licitaciones/workers/extraccion_worker.py`

Signals:
```python
progreso   = Signal(str)
avance     = Signal(int, int)   # procesadas, total_del_dia
finalizado = Signal()
error      = Signal(str)
```

Lógica del método `run()`:
1. Para cada día en el rango:
   a. Llamar `cliente_mp.obtener_licitaciones_dia(fecha)`.
   b. Por cada licitación del listado:
      - Llamar `gestor_reglas.obtener_snapshot()`.
      - Evaluar título con `motor.evaluar_titulo(nombre, snapshot)`.
      - Si `score_resumen > 0`: llamar `cliente_mp.obtener_detalle()`,
        evaluar descripción y productos.
      - Calcular `score_total = score_resumen + score_detalle +
        puntaje_organismo` (puntaje_organismo viene del cache de organismos
        cargado al inicio del `run()`).
      - Llamar `repo_licitaciones.upsert(datos)`. El worker NO implementa
        lógica de UPSERT propia.
   c. Emitir `avance` cada 10 licitaciones.
2. Emitir `finalizado` al terminar.

Flag `_ejecutando = True` con método `detener()` que lo pone en `False`.
Verificar el flag al inicio de cada iteración del día.

**DoD**: `tests/test_workers/test_extraccion_worker.py` pasa (ver tarea 3.5).

---

### 3.2 Crear `src/monitor_licitaciones/workers/scoring_worker.py`

Signals:
```python
progreso   = Signal(str)
avance     = Signal(int, int)
finalizado = Signal()    # UI recarga las 3 pestañas al recibir esto
error      = Signal(str)
```

Lógica:
1. `palabras = repo_reglas.obtener_palabras_clave()`
2. `reglas = mapear_reglas(palabras)` — usar función de mapping.
3. `gestor_reglas.recargar(reglas)`
4. `licitaciones = repo_licitaciones.obtener_activas_en_pipeline(
   ETAPAS_ACTIVAS, CODIGO_ESTADO_PUBLICADA)`
5. Cargar puntajes de organismos una vez: `{org.codigo: org.puntaje_fijo
   for org in repo_reglas.obtener_organismos()}`.
6. Por cada licitación:
   - `snapshot = gestor_reglas.obtener_snapshot()`
   - Evaluar título, descripción y productos.
   - `score_total = score_resumen + score_detalle + puntaje_organismo`
   - `repo_licitaciones.actualizar_score(...)`
   - Emitir `avance` cada 25 licitaciones.
7. Emitir `finalizado`.

**DoD**: `tests/test_workers/test_scoring_worker.py` pasa (ver tarea 3.6).

---

### 3.3 Crear `src/monitor_licitaciones/workers/exportacion_worker.py`

Signals:
```python
avance     = Signal(int, int)   # chunks procesados, chunks totales
finalizado = Signal(str)        # ruta del archivo generado
error      = Signal(str)
```

Lógica:
- Procesar en chunks de `EXPORT_CHUNK_SIZE` usando paginación del repositorio.
- CSV: modo append (`mode='a'`), cabecera solo en el primer chunk.
- Excel: acumular DataFrames, `pd.concat` al final.
- Limpiar zonas horarias: `df[col].dt.tz_localize(None)` en columnas datetime.
- Nombre de archivo: `Reporte_{etapa}_{YYYY-MM-DD_HH-MM-SS}.{ext}`.

**DoD**: Dado un repositorio con 150 registros, el worker genera un archivo
`.xlsx` o `.csv` con los 150 registros y emite `finalizado` con la ruta.

---

### 3.4 Crear `src/monitor_licitaciones/workers/piloto_worker.py`

Signals:
```python
estado_cambiado       = Signal(str)
extraccion_iniciada   = Signal()
extraccion_completada = Signal()
error_ocurrido        = Signal(str)
```

Lógica del método `run()`:
```python
while self._ejecutando:
    config  = self._repo_config.obtener_todas()
    activo  = config.get(PILOTO_ACTIVO) == "true"
    hora    = config.get(PILOTO_HORA) or PILOTO_HORA_DEFAULT   # "22:30"
    ultima  = config.get(PILOTO_ULTIMA_EJECUCION)
    ahora   = datetime.now()

    if activo and self._es_hora(ahora, hora):
        if str(ahora.date()) != ultima:
            self._ejecutar_con_reintentos(ahora)

    self._sleep_interrumpible(60)
```

`_sleep_interrumpible(segundos)`: loop de `range(segundos)` durmiendo 1
segundo cada iteración, verificando `self._ejecutando` en cada vuelta.

`_ejecutar_con_reintentos(ahora)`: backoff de 5, 10 y 20 minutos. Si éxito:
`repo_config.guardar(PILOTO_ULTIMA_EJECUCION, str(ahora.date()))`. Si agota
reintentos: `repo_config.guardar(PILOTO_ULTIMO_ERROR, mensaje)` y emitir
`error_ocurrido`.

Regla crítica: el worker lee la configuración de BD en cada ciclo de 60s.
La UI no necesita reiniciar el worker al cambiar la configuración.

**DoD**: `tests/test_workers/test_piloto_worker.py` pasa (ver tarea 3.7).

---

### 3.5 Crear `tests/test_workers/test_extraccion_worker.py`

Usar `QSignalSpy` de pytest-qt. Mockear `ClienteAPI` y repositorios.

Tests requeridos:
- `test_emite_finalizado_al_completar_rango`: API retorna lista vacía,
  `finalizado` se emite exactamente una vez.
- `test_score_cero_no_descarga_detalle`: mock de motor con score 0,
  `obtener_detalle` nunca se llama.
- `test_score_positivo_descarga_detalle`: mock de motor con score > 0,
  `obtener_detalle` se llama una vez por licitación relevante.
- `test_upsert_llamado_por_cada_licitacion`: verificar que
  `repo_licitaciones.upsert()` se llama, no que el worker implementa UPSERT.
- `test_detener_interrumpe_el_loop`: `detener()` durante ejecución,
  worker para antes de procesar todos los días del rango.
- `test_reintenta_en_error_500`: mock de API que falla y luego tiene éxito,
  `error` no se emite.

**DoD**: Los 6 tests pasan.

---

### 3.6 Crear `tests/test_workers/test_scoring_worker.py`

Tests requeridos:
- `test_recalcula_solo_licitaciones_activas`: mock del repositorio devuelve
  licitaciones mezcladas, `actualizar_score` solo se llama para las activas.
- `test_emite_avance_cada_25`: con 50 licitaciones, `avance` se emite
  exactamente 2 veces.
- `test_emite_finalizado_siempre`: incluso con lista vacía, `finalizado`
  se emite.
- `test_usa_mapping_de_palabras_a_reglas`: verificar que el worker llama
  a `mapear_reglas()` antes de pasar al motor (no pasa `PalabraClave`
  directamente).

**DoD**: Los 4 tests pasan.

---

### 3.7 Crear `tests/test_workers/test_piloto_worker.py`

Tests requeridos:
- `test_no_ejecuta_si_ya_se_ejecuto_hoy`: `repo_config` devuelve fecha de
  hoy en `PILOTO_ULTIMA_EJECUCION`, `extraccion_iniciada` no se emite.
- `test_ejecuta_si_es_la_hora_y_no_se_ejecuto`: hora coincide, fecha
  distinta, `extraccion_iniciada` se emite.
- `test_lee_config_de_bd_en_cada_ciclo`: cambiar la config entre ciclos
  afecta el comportamiento del siguiente ciclo sin reiniciar el worker.
- `test_sleep_interrumpible_responde_a_detener`: `detener()` durante el
  sleep de 60s, el worker termina en menos de 2 segundos.
- `test_persiste_error_tras_agotar_reintentos`: extracción siempre falla,
  `repo_config.guardar(PILOTO_ULTIMO_ERROR, ...)` se llama y `error_ocurrido`
  se emite.

**DoD**: Los 5 tests pasan.

---

## Phase 4: UI

> La UI no accede directamente a la BD. Operaciones de datos pasan por workers
> (operaciones largas) o por repositorios directamente (operaciones síncronas
> simples como actualizar etapa).

### 4.1 Crear `src/monitor_licitaciones/ui/widgets/tabla_licitaciones.py`

Requisitos:
- `QTableWidget`: columnas Puntaje Total, Código, Nombre, Fecha Cierre, Estado.
- Selección por fila completa, solo lectura.
- Menú contextual (clic derecho): opciones basadas en
  `GestorPipeline.destinos_disponibles(etapa_actual)`. No mostrar la etapa
  actual como opción.
- Doble clic: abre diálogo de ficha técnica con descripción, productos y
  justificación del score.
- Paginación: botones Anterior / `Página N` / Siguiente. Siguiente
  deshabilitado si `rowCount() < TAMANIO_PAGINA`.
- Texto de ayuda visible: `"Clic derecho sobre una fila para mover entre etapas."`.
- Señal: `etapa_cambiada = Signal(str, str)` — `(codigo_externo, nueva_etapa)`.

**DoD**: `tests/test_ui/test_widgets.py` pasa los tests de tabla (ver 4.9).
El texto de ayuda es visible sin hacer clic.

---

### 4.2 Crear `src/monitor_licitaciones/ui/widgets/filtro_busqueda.py`

Requisitos:
- `QLineEdit` con placeholder `"Filtrar por nombre o descripción..."`.
- Debounce: cada cambio de texto cancela el timer anterior y crea uno de
  300ms. Al disparar: emitir `texto_cambiado`.
- Texto vacío: emitir `texto_cambiado("")` para que la vista cargue sin filtro.
- Señal: `texto_cambiado = Signal(str)`.

**DoD**: `tests/test_ui/test_widgets.py` pasa los tests de filtro (ver 4.9).
La señal se emite una sola vez tras ingresar texto rápidamente.

---

### 4.3 Crear `src/monitor_licitaciones/ui/widgets/indicadores_pipeline.py`

Requisitos:
- Tres `QLabel`: `"Candidatas (N)"`, `"Seguimiento (N)"`, `"Ofertadas (N)"`.
- Método `actualizar()` que llama a `repo_licitaciones.contar_por_etapa()`
  y actualiza los tres labels.
- `actualizar()` es llamado por la main window en tres momentos: inicio de
  app, cualquier worker emite `finalizado`, tabla emite `etapa_cambiada`.

**DoD**: `tests/test_ui/test_widgets.py` pasa los tests de indicadores
(ver 4.9). Los labels muestran cero por defecto, no texto vacío.

---

### 4.4 Crear `src/monitor_licitaciones/ui/dialogs/config_palabras_clave.py`

Requisitos:
- Tabla con columnas: Término, Categoría, Peso Título, Peso Descripción,
  Peso Productos, Estado (Activa/Inactiva).
- Botones: Agregar (abre subdiálogo de edición), Editar, Eliminar (soft
  delete con confirmación).
- Al guardar cualquier cambio, emitir `reglas_cambiadas = Signal()` para
  que main window lance `ScoringWorker`.

**DoD**: El diálogo abre sin errores. `reglas_cambiadas` se emite al
guardar. Los cambios persisten en BD al cerrar el diálogo.

---

### 4.5 Crear `src/monitor_licitaciones/ui/dialogs/config_extraccion.py`

Requisitos:
- Dos `QDateEdit` con calendario popup.
- Validación: fecha inicio ≤ fecha fin, mostrar error inline.
- Botón "Iniciar Extracción" → lanza `ExtraccionWorker`.
- Botón "Cancelar" visible solo durante extracción activa → llama
  `worker.detener()`.
- `QTextEdit` readonly conectado a `worker.progreso`.
- `QProgressBar` conectada a `worker.avance`.

**DoD**: El diálogo lanza el worker correctamente. El botón Cancelar
aparece solo durante extracción. Al finalizar, el botón Iniciar
se reactiva.

---

### 4.6 Crear `src/monitor_licitaciones/ui/dialogs/config_exportacion.py`

Requisitos:
- Checkboxes para etapas y formatos. Validación: al menos una etapa y
  un formato.
- `QFileDialog` para directorio destino.
- `QProgressBar` conectada a `worker.avance`.
- Al completar: `QMessageBox` con ruta del archivo.

**DoD**: El diálogo genera un archivo en el directorio seleccionado.
La barra de progreso avanza durante la exportación.

---

### 4.7 Crear `src/monitor_licitaciones/ui/dialogs/config_piloto.py`

Requisitos:
- `QTimeEdit` formato `HH:mm`, valor inicial `"22:30"`.
- Texto informativo visible: `"ChileCompra recomienda ejecutar entre
  las 22:00 y las 07:00 horas para mayor estabilidad de la API."`.
- Botón toggle Activar/Desactivar. Al cambiar: persiste en BD con
  `repo_config.guardar(PILOTO_ACTIVO, "true"/"false")`.
- Al cambiar hora: persiste con `repo_config.guardar(PILOTO_HORA, "HH:MM")`.
- Label de estado conectado a `piloto_worker.estado_cambiado`.
- Label de última ejecución: `repo_config.obtener(PILOTO_ULTIMA_EJECUCION)`.

**DoD**: El texto de ChileCompra es visible sin scroll. El valor inicial
del selector es exactamente `"22:30"`. Los cambios persisten en BD.

---

### 4.8 Crear `src/monitor_licitaciones/ui/main_window.py`

Pestañas principales: Candidatas, Seguimiento, Ofertadas, Herramientas.
Sub-pestañas en Herramientas: Extracción, Exportación, Palabras Clave,
Organismos, Piloto Automático.

Responsabilidades:
- Instanciar `PilotoWorker` al iniciar y llamar `start()`.
- Instanciar `indicadores_pipeline` y conectar:
  - `extraccion_worker.finalizado` → `indicadores.actualizar()`
  - `scoring_worker.finalizado` → `indicadores.actualizar()` + recargar las 3 pestañas
  - `tabla.etapa_cambiada` → `indicadores.actualizar()`
- Conectar `config_palabras_clave.reglas_cambiadas` → lanzar `ScoringWorker`.
- Lazy loading: cada pestaña carga datos solo al visitarla por primera vez
  o cuando `necesita_actualizacion = True`.
- Al cerrar la ventana: llamar `piloto_worker.detener()` y esperar con
  `piloto_worker.wait(3000)`.

**DoD**: La app inicia sin errores. Las 4 pestañas principales y las
5 sub-pestañas de Herramientas son accesibles. Los indicadores muestran
datos al iniciar.

---

### 4.9 Crear `tests/test_ui/test_widgets.py`

Tests con pytest-qt.

Tests requeridos:
- `test_filtro_debounce_emite_una_sola_vez`: simular 5 cambios de texto
  rápidos, verificar que `texto_cambiado` se emite exactamente 1 vez después
  de 300ms con `qtbot.waitSignal`.
- `test_filtro_texto_vacio_emite_string_vacio`: limpiar el campo, verificar
  que la señal emite `""`.
- `test_tabla_menu_contextual_candidata`: simular clic derecho en fila de
  etapa `"candidata"`, verificar que el menú tiene opciones
  `"seguimiento"` y `"ofertada"` pero no `"candidata"`.
- `test_tabla_paginacion_siguiente_deshabilitado`: cargar menos filas que
  `TAMANIO_PAGINA`, verificar que botón Siguiente está deshabilitado.
- `test_indicadores_muestra_cero_por_defecto`: sin datos, labels muestran
  `"Candidatas (0)"`, no texto vacío.
- `test_indicadores_actualizar_con_datos`: mock de `contar_por_etapa()`
  retorna `{'candidata': 5, 'seguimiento': 2, 'ofertada': 1}`, verificar
  el texto de los tres labels.

**DoD**: Los 6 tests pasan.

---

## Phase 5: CLI + Entry Point

### 5.1 Crear `src/monitor_licitaciones/main.py`

Entry point con validación fail-fast y configuración de Loguru.

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
        print(f"\nEdite: {Path('.env').resolve()}")
        sys.exit(1)

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

**DoD**: Con `.env` configurado correctamente, `poetry run gui` abre la
ventana. Sin `.env`, imprime el mensaje de error y sale con código 1.

---

### 5.2 Crear `src/monitor_licitaciones/cli/init_db.py`

Script para primer uso. Verifica conectividad antes de migrar.

```python
def main():
    load_dotenv()
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL no configurada.")
        sys.exit(1)

    # Verificar conectividad antes de intentar migrar
    try:
        engine = create_engine(db_url)
        with engine.connect():
            pass
        print("Conexión a PostgreSQL: OK")
    except Exception as e:
        print(f"ERROR: No se pudo conectar a PostgreSQL: {e}")
        sys.exit(1)

    from alembic.config import Config
    from alembic import command
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
    print("Base de datos inicializada correctamente.")
```

**DoD**: `poetry run init-db` con BD disponible completa sin errores.
Con BD no disponible, imprime error descriptivo y sale con código 1.

---

### 5.3 Crear `src/monitor_licitaciones/cli/migrate.py`

Script para actualizaciones sobre una BD ya existente. A diferencia de
`init_db.py`, asume que la conexión ya funciona (no verifica conectividad)
y solo ejecuta las migraciones pendientes.

```python
def main():
    load_dotenv()
    from alembic.config import Config
    from alembic import command
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
    print("Migraciones aplicadas correctamente.")
```

**DoD**: `poetry run migrate` sobre una BD con migraciones al día imprime
"Migraciones aplicadas correctamente." sin errores.

> **Diferencia semántica con `init-db`**: `init-db` es para primer uso e
> incluye verificación de conectividad. `migrate` es para CI/CD o
> actualizaciones donde la conexión ya está garantizada.

---

### 5.4 Crear `src/monitor_licitaciones/cli/seed.py`

Estrategia de carga con fallback:
1. Intentar desde endpoint `BuscarComprador` de la API.
2. Si falla, intentar desde archivo `organismos.csv` en raíz del proyecto.
3. Si ninguno disponible: imprimir instrucciones y salir con código 1.

Para cada organismo: INSERT si no existe. Si ya existe, no sobreescribir
`puntaje_fijo` (respetar configuración manual del usuario).

**DoD**: `poetry run seed` con API disponible carga organismos sin errores.
Con API no disponible y `organismos.csv` presente, carga desde CSV. Con
ninguno disponible, imprime mensaje de instrucciones claro.

---

### 5.5 Crear `README.md`

```markdown
# Monitor de Licitaciones - ML_AI

## Setup (5 pasos)

1. cp .env.example .env
   # Editar DATABASE_URL y TICKET_MERCADO_PUBLICO

2. poetry install

3. poetry run init-db

4. poetry run seed

5. poetry run gui

## Troubleshooting

**"DATABASE_URL no configurada"**: Editar el archivo `.env` en la raíz.

**"connection refused"**: PostgreSQL no está corriendo en el host/puerto
configurado en DATABASE_URL.

**"TICKET_MERCADO_PUBLICO no configurada"**: Obtener el ticket en
https://api.mercadopublico.cl

**Tests**: `pytest` (requiere PostgreSQL para tests de integración,
SQLite in-memory para tests de dominio y repositorios).
```

**DoD**: El README tiene los 5 pasos de setup y la sección de
troubleshooting con los 3 errores comunes.

---

## Phase 6: E2E + Validación

### 6.1 Crear `tests/test_infrastructure/test_cliente_mp.py`

Tests con la librería `responses`.

Tests requeridos:
- `test_obtener_licitaciones_dia_exitoso`: mock 200 con payload válido,
  retorna lista parseada con longitud correcta.
- `test_obtener_licitaciones_dia_respuesta_sin_listado`: payload sin clave
  `"Listado"`, retorna `[]` sin excepción.
- `test_obtener_detalle_exitoso`: mock 200 con detalle, retorna dict con
  `CodigoExterno`.
- `test_obtener_detalle_404_retorna_none`: mock 404, retorna `None`.
- `test_obtener_detalle_reintenta_en_500`: mock 500 seguido de 200, la
  segunda llamada retorna datos (no error).
- `test_obtener_detalle_agota_reintentos`: 3 mocks 500 consecutivos,
  retorna `None` sin lanzar excepción.
- `test_pausa_entre_peticiones`: dos llamadas consecutivas, el tiempo
  transcurrido es ≥ `API_PAUSA_SEGUNDOS`.

**DoD**: Los 7 tests pasan.

---

### 6.2 Crear `tests/test_e2e/test_flujo_completo.py`

Test del flujo principal: extracción → scoring → persistencia.

```
Dado:
  - 2 reglas configuradas: "silla" (peso_titulo=10) y "mesa" (peso_titulo=20)
  - Mock de API que retorna 3 licitaciones:
      L1: "Compra de sillas de oficina" (debe coincidir)
      L2: "Servicio de aseo" (no debe coincidir)
      L3: "Adquisición de mesas" (debe coincidir)
  - Mock de detalle que retorna descripción sin coincidencias adicionales

Cuando: se ejecuta ExtraccionWorker completo (usando qtbot.waitSignal)

Entonces:
  - L1 en BD con score_resumen=10, etapa="candidata"
  - L3 en BD con score_resumen=20, etapa="candidata"
  - L2 en BD con score_resumen=0, etapa="ignorada"
  - obtener_detalle fue llamado exactamente 2 veces (L1 y L3)
  - obtener_detalle NO fue llamado para L2
```

**DoD**: El test pasa y verifica exactamente las condiciones descritas.

---

### 6.3 Crear `tests/test_e2e/test_validacion_pydantic.py`

Tests de los modelos Pydantic en `schemas_mp.py`.

Tests requeridos:
- `test_listado_valido_parsea_correctamente`: payload completo de listado,
  `RespuestaListadoAPI` parsea sin error y `Cantidad` y `Listado` son
  correctos.
- `test_listado_sin_campo_opcional_no_lanza_error`: payload sin `Comprador`
  en una licitación, parsea sin `ValidationError`.
- `test_listado_vacio_retorna_lista_vacia`: `Listado: []`, retorna lista
  vacía.
- `test_detalle_campo_obligatorio_faltante`: payload sin `CodigoExterno`,
  debe lanzar `ValidationError`.
- `test_detalle_fecha_malformada_queda_como_none`: campo de fecha con valor
  inválido, el campo queda `None` y no lanza excepción (configurar el campo
  como `str | None` con default None — la conversión a datetime ocurre
  en el cliente, no en el schema).
- `test_detalle_campos_opcionales_con_defaults`: todos los campos opcionales
  tienen valores por defecto sensatos.

**DoD**: Los 6 tests pasan.

---

### 6.4 Configurar cobertura de tests

La configuración ya está en `pyproject.toml` (tarea 1.1):

```toml
[tool.pytest.ini_options]
addopts = "--cov=src/monitor_licitaciones --cov-report=term-missing --cov-fail-under=80"

[tool.coverage.run]
omit = ["*/cli/*", "*/main.py", "*/ui/*"]

[tool.coverage.report]
fail_under = 80
```

El umbral del 80% es **enforceable**: `pytest` falla con código de salida
no-cero si la cobertura cae por debajo. Las exclusiones de `cli/`, `main.py`
y `ui/` son intencionales: estas capas tienen alta dependencia de Qt y
PostgreSQL real, y se cubren con los tests E2E, no con cobertura de líneas.

**DoD**: `pytest` con cobertura por debajo del 80% en `domain/` o
`infrastructure/database/` falla con código de salida 2. Con cobertura
≥ 80%, el comando termina con código 0.

---

## Resumen de Dependencias entre Fases

```
Phase 1 (Scaffolding + Foundation)
│  ├── conftest.py    ← prerrequisito de TODOS los tests en fases 2, 3, 4, 6
│  ├── models.py      ← prerrequisito de repositorios y types de dominio
│  └── config.py      ← prerrequisito de workers y UI
│
├── Phase 2 (Domain)          ← depende de: tipos.py + models.py de Phase 1
│     └── Phase 3 (Workers)   ← depende de: Phase 1 + Phase 2
│           └── Phase 4 (UI)  ← depende de: Phase 1 + Phase 2 + Phase 3
│
├── Phase 5 (CLI)             ← depende de: repositorios de Phase 1
│
└── Phase 6 (E2E)             ← depende de: todas las fases anteriores
```

---

*Documento de fase TASKS — SDD*
*Proyecto: ML_AI | Mayo 2026*
*Revisión final: incorpora observaciones 1–10 del orquestador*
