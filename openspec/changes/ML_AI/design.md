# Design: ML_AI - Monitor de Licitaciones

## Enfoque Técnico

Sistema de monitoreo de licitaciones de Mercado Público Chile con extracción automatizada via API, scoring configurable basado en reglas y pipeline operativo de tres etapas. La arquitectura sigue un patrón por capas que separa estrictamente la UI (PySide6) de la lógica de negocio (domain) y el acceso a datos (infrastructure). La concurrencia se maneja mediante QThread workers con señales nativas de PySide6 para comunicación thread-safe con la UI. El scoring es recargable en caliente usando un patrón de snapshots de reglas con locks, garantizando que las evaluaciones en curso no se corrompen al modificar las reglas.

## Decisiones de Arquitectura

### Decisión 1: Estructura de Proyecto

**Elección**: Estructura por capas con subdiretorios por tipo de componente
```
src/monitor_licitaciones/
├── ui/                    # PySide6 windows, widgets, dialogs
├── workers/                # QThread workers (extracción, scoring, exportación)
├── domain/                # Lógica de negocio pura (scoring motor, pipeline)
├── infrastructure/
│   ├── database/           # SQLAlchemy, repositorios
│   └── api/               # Cliente HTTP para Mercado Público
└── cli/                   # Scripts CLI (migrate, seed)
```

**Alternativas descartadas**: Estructura flat (todos módulos en src/), Estructura monomer (single package)

**Rationale**: La separación estricta UI/lógica es un PRINCIPIO del PRD. La estructura por capas hace enforce la separación arquitectónicamente y hace el dominio 100% testeable sin levantar UI ni BD.

---

### Decisión 2: Manejo de Configuración de Scoring (Thread Safety)

**Elección**: Copia de reglas por operación + threading.Lock durante lectura de config
```python
class GestorReglas:
    def __init__(self):
        self._lock = threading.Lock()
    
    def evaluar(self, texto: str) -> tuple[int, list[str]]:
        # Copia atómica de reglas para esta evaluación
        with self._lock:
            reglas = self._reglas.copy()
        # Evaluación con copia independiente
        return self._motor.calcular(texto, reglas)
```

**Alternativas descartadas**: Variables globales con locks, Singleton con lock interno

**Rationale**: El PRD exige "scoring recargable en caliente sin corromper evaluaciones en curso". La copia por operación garantiza que cada evaluación usa una versión consistente de las reglas. El lock protege solo la lectura de la referencia, no el cálculo completo.

---

### Decisión 3: Patrón de Comunicación UI ↔ Workers

**Elección**: Signals/slots de PySide6 (nativos) con patrón de señales predefinido
```python
class ExtraccionWorker(QThread):
    progreso = Signal(str)       # Mensaje de estado
    avance = Signal(int, int)    # actual, total
    finalizado = Signal()       # Éxito
    error = Signal(str)          # Fallo con mensaje
```

**Alternativas descartadas**: Queue de mensajes personalizada, Callbacks con thread-safe wrapper

**Rationale**: PySide6 tiene soporte nativo de signals/slots que funciona cross-thread automáticamente. No requiere dependencias adicionales y es el patrón RECOMENDADO por la documentación de PySide6. Reduce código y mantenimiento.

---

### Decisión 4: Persistencia de Configuración del Piloto Automático

**Elección**: Tabla `configuracion` en PostgreSQL (per SPEC)
```python
# Entidad Configuracion
# - clave: STRING(50) UNIQUE (PK)
# - valor: TEXT
# - fecha_actualizacion: DATETIME
```

**Alternativas descartadas**: Archivo JSON en filesystem, Archivo .env

**Rationale**: SPEC establece "La configuración DEBE persistir entre reinicios... almacenada en la entidad `Configuracion`". Usar filesystem multiplicaría los puntos de falla (archivos .env, .json, etc). BD unifica la persistencia y permite queries.

---

### Decisión 5: Validación de Credenciales al Inicio

**Elección**: Validación fail-fast al inicio de main()
```python
def main():
    config = cargar_configuracion()
    
    if not config.get('DATABASE_URL'):
        sys.exit("FALTA: DATABASE_URL. Configure en .env")
    
    if not config.get('TICKET_MERCADO_PUBLICO'):
        sys.exit("FALTA: TICKET_MERCADO_PUBLICO. Configure en .env")
    
    iniciar_app()
```

**Alternativas descartadas**: Validación lazy (al primer uso), Validación async en background

**Rationale**: El PRD establece "Fail-fast en configuración. Si el usuario no tiene credenciales, la app debe decirlo inmediatamente al arrancar, no fallar silenciosamente en la primera extracción."

---

## Data Flow

### Flujo 1: Extracción de Licitaciones

```
┌─────────────────────────────────────────────────────────────┐
│                    UI (Main Thread)                        │
│  ┌──────────┐    ┌─────────────┐    ┌──────────────┐    │
│  │ Dialogo  │───→│ Extraccion │───→│ Actualizar  │    │
│  │ Extracc. │    │ Worker     │    │ Vistas      │    │
│  └──────────┘    └─────┬───────┘    └──────────────┘    │
└─────────────────────────┼─────────────────────────────────────┘
                          │ signals (progress, error, finished)
        ┌──────────────────┴──────────────────┐
        ▼                                         ▼
┌─────────────────────────┐        ┌─────────────────────────┐
│   API Mercado Público  │        │   PostgreSQL Database   │
│ (HTTP requests)         │        │ (Repositorio)          │
│                        │        │                        │
│ 1. Listado diario      │        │ UPSERT licitacion       │
│ 2. Detalle (si score>0)│        │ UPDATE score/jus-      │
└─────────────────────────┘        │ tificacion             │
                                  └─────────────────────────┘
```

### Flujo 2: Scoring Recargable en Caliente

```
┌─────────────────────────────────────────────────────────────┐
│                    UI (Main Thread)                        │
│  ┌──────────────────┐    ┌───────────────────────────┐   │
│  │ Guardar palabras  │───→│ Signal: reglas_cambiadas  │───→│
│  │ clave           │    │                         │   │
│  └──────────────────┘    └───────────┬───────────┘   │
└─────────────────────────────────────────┼───────────────┘
                                          │
                    ┌───────────────────���─��─────────────────────┐
                    ▼                                             ▼
          ┌───────────────────┐              ┌───────────────────────────┐
          │ ScoringWorker     │              │     Domain (puro)          │
          │ (QThread)        │              │                           │
          │                  │              │ 1. Copiar reglas (lock)   │
          │ 1. Obtener reglas  │              │ 2. Para cada licitacion   │
          │ 2. Para cada lic  │─────────────→│    evaluar_titulo()       │
          │ 3. Update BD     │              │    evaluar_detalle()      │
          │ 4. Signal UI     │              │ 3. Return score+jus-     │
          └───────────────────┘              │    tificacion              │
                                            └───────────────────────────┘
```

---

## Archivos del Proyecto

| Archivo | Acción | Descripción |
|---------|--------|------------|
| `pyproject.toml` | Create | Config Poetry + dependencias |
| `.env.example` | Create | Template de variables de entorno |
| `src/monitor_licitaciones/__init__.py` | Create | Package init |
| `src/monitor_licitaciones/main.py` | Create | Entry point + fail-fast validation |
| `src/monitor_licitaciones/config.py` | Create | Carga de .env + validación |
| `src/monitor_licitaciones/ui/__init__.py` | Create | UI layer init |
| `src/monitor_licitaciones/ui/main_window.py` | Create | Main window con pestañas |
| `src/monitor_licitaciones/ui/widgets/__init__.py` | Create | Widgets init |
| `src/monitor_licitaciones/ui/widgets/tabla_licitaciones.py` | Create | Tabla con paginación y menú contextual |
| `src/monitor_licitaciones/ui/widgets/indicadores_pipeline.py` | Create | Contadores por etapa |
| `src/monitor_licitaciones/ui/dialogs/__init__.py` | Create | Dialogs init |
| `src/monitor_licitaciones/ui/dialogs/config_palabras_clave.py` | Create | Diálogo de palabras clave |
| `src/monitor_licitaciones/ui/dialogs/config_extraccion.py` | Create | Diálogo de extracción |
| `src/monitor_licitaciones/ui/dialogs/config_exportacion.py` | Create | Diálogo de exportación |
| `src/monitor_licitaciones/ui/dialogs/config_piloto.py` | Create | Diálogo de piloto automático |
| `src/monitor_licitaciones/workers/__init__.py` | Create | Workers init |
| `src/monitor_licitaciones/workers/extraccion_worker.py` | Create | Extracción API (listado + detalle) |
| `src/monitor_licitaciones/workers/scoring_worker.py` | Create | Recálculo de scores |
| `src/monitor_licitaciones/workers/exportacion_worker.py` | Create | Export Excel/CSV con lotes |
| `src/monitor_licitaciones/workers/piloto_worker.py` | Create | Ejecución automática programada |
| `src/monitor_licitaciones/domain/__init__.py` | Create | Domain init |
| `src/monitor_licitaciones/domain/scoring/__init__.py` | Create | Scoring init |
| `src/monitor_licitaciones/domain/scoring/motor_scoring.py` | Create | Lógica de scoring puro |
| `src/monitor_licitaciones/domain/scoring/gestor_reglas.py` | Create | Gestor thread-safe de reglas |
| `src/monitor_licitaciones/domain/pipeline/__init__.py` | Create | Pipeline init |
| `src/monitor_licitaciones/domain/pipeline/gestor_pipeline.py` | Create | Lógica de pipeline (etapas) |
| `src/monitor_licitaciones/infrastructure/__init__.py` | Create | Infra init |
| `src/monitor_licitaciones/infrastructure/database/__init__.py` | Create | Database init |
| `src/monitor_licitaciones/infrastructure/database/models.py` | Create | Modelos SQLAlchemy ORM |
| `src/monitor_licitaciones/infrastructure/database/connection.py` | Create | Connection manager (session-per-request) |
| `src/monitor_licitaciones/infrastructure/database/repositorio.py` | Create | Repositorio licitaciones |
| `src/monitor_licitaciones/infrastructure/api/__init__.py` | Create | API init |
| `src/monitor_licitaciones/infrastructure/api/cliente_mp.py` | Create | Cliente HTTP Mercado Público |
| `src/monitor_licitaciones/cli/__init__.py` | Create | CLI init |
| `src/monitor_licitaciones/cli/migrate.py` | Create | Script migrate |
| `src/monitor_licitaciones/cli/init_db.py` | Create | Script init-db (crea tablas) |
| `src/monitor_licitaciones/cli/seed.py` | Create | Script seed organismos |
| `alembic.ini` | Create | Config Alembic |
| `alembic/env.py` | Create | Entorno Alembic |
| `alembic/versions/001_initial.py` | Create | Migración inicial (todas las tablas) |
| `tests/conftest.py` | Create | Fixtures pytest |
| `tests/__init__.py` | Create | Tests init |
| `tests/test_domain/__init__.py` | Create | Tests domain init |
| `tests/test_domain/test_scoring.py` | Create | Tests domain scoring (sin mocks) |
| `tests/test_domain/test_pipeline.py` | Create | Tests pipeline |
| `tests/test_infrastructure/__init__.py` | Create | Tests infra init |
| `tests/test_infrastructure/test_repositorio.py` | Create | Tests repositorio con SQLite in-memory |
| `tests/test_workers/__init__.py` | Create | Tests workers init |
| `tests/test_workers/test_extraccion.py` | Create | Tests worker extracción |

---

## Interfaces / Contratos

### Interfaz: RepositorioLicitacion
```python
from typing import Protocol
from domain.scoring.models import Licitacion, PalabraClave, Organismo

class RepositorioLicitacion(Protocol):
    def obtener_por_etapa(self, etapa: str, pagina: int, por_pagina: int) -> list[Licitacion]: ...
    def obtener_activas_en_pipeline(self, etapas: list[str], codigo_estado_activo: int) -> list[Licitacion]: ...
    def upsert(self, datos: dict) -> Licitacion: ...
    def actualizar_etapa(self, codigo_externo: str, etapa: str) -> bool: ...
    def actualizar_score(self, codigo_externo: str, score_total: int, justificacion: str) -> bool: ...
```

### Interfaz: ClienteAPI
```python
class ClienteAPI(Protocol):
    def obtener_licitaciones_dia(self, fecha: str) -> list[dict]: ...
    """Form fecha: DDMMYYYY. Una petición por día (la app itera)."""
    
    def obtener_detalle(self, codigo_externo: str) -> dict | None: ...
    """Retorna detalle completo de una licitación."""
    
    def obtener_organismos(self) -> list[dict]: ...
    """Obtiene lista completa de organismos públicos."""
```

### Interfaz: MotorScoring
```python
class MotorScoring(Protocol):
    def evaluar_titulo(self, texto: str, reglas: list[PalabraClave]) -> tuple[int, list[str]]: ...
    def evaluar_detalle(self, descripcion: str, productos: str, reglas: list[PalabraClave]) -> tuple[int, list[str]]: ...
```

---

## Estrategia de Testing

| Capa | Qué Testear | Enfoque |
|------|------------|---------|
| Unit | Dominio puro: scoring, pipeline | pytest puro sin mocks, lógica determinística |
| Unit | GestorReglas thread-safety | pytest con threading stress test |
| Unit | Model validation (Pydantic) | pytest con datos válidos e inválidos |
| Integration | Repositorio | pytest con SQLite in-memory |
| Integration | Cliente API | pytest con responses mockeadas ( responses= en requests) |
| Integration | Workers | pytest-qt con signals spy |
| E2E | Flujo completo UI | pytest + app real (mock server para API) |

---

## Migración / Despliegue

No se requiere migración inicial (proyecto nuevo). La migración `001_initial` crea todas las tablas al ejecutar `poetry run init-db`.

**Para nuevos usuarios**: El flujo de setup es:

1. Copiar `.env.example` a `.env` y configurar `DATABASE_URL` y `TICKET_MERCADO_PUBLICO`
2. Ejecutar `poetry install` para instalar dependencias
3. Ejecutar `poetry run init-db` para crear tablas
4. Ejecutar `poetry run seed` para cargar organismos (usa endpointBuscarComprador)
5. Ejecutar `poetry run gui` o `poetry run main` para iniciar la app

---

## Preguntas Abiertas

- [ ] **Pendiente**: Confirmar tipo de dato del campo `codigo_organismo` en respuestas reales de la API (SPEC indica String por precaución, pero requiere verificación durante implementación)
- [ ] **Pendiente**: Validar si la API devuelve el campo `cantidad` consistente en respuestas de listado diario (para logging, no es crítico)
- [ ] **Pendiente**: Definir ubicación por defecto de logs ( `logs/` en directorio de trabajo o `%APPDATA%/monitor_licitaciones/logs/` )

Estos son temas técnicos que requieren verificación durante la implementación inicial, pero no bloquean el diseño ahora.

---

*Documento generado en fase DESIGN del SDD*
*Proyecto: ML_AI*
*Fecha: Mayo 2026*