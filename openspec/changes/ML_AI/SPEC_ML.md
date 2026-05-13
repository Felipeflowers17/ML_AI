# ESPECIFICACIONES TÉCNICAS COMPLETAS - ML_AI

> **Nota:** Este documento fue generado automáticamente desde las especificaciones guardadas en Engram, revisado manualmente, y enriquecido con información extraída directamente de la documentación oficial de `api.mercadopublico.cl` (verificada mayo 2026). Las secciones marcadas con `[CORREGIDO]` fueron ajustadas tras revisión del comportamiento real de la API. Las secciones marcadas con `[OFICIAL]` están respaldadas por la documentación oficial de ChileCompra. Las secciones marcadas con `[ADVERTENCIA]` o `[RIESGO]` señalan puntos que requieren verificación al momento de implementar.

---

## 1. ESPECIFICACIONES FUNCIONALES DETALLADAS

### 1.1 Extracción de Licitaciones desde API Mercado Público

#### Requisito: Extracción de Resumen de Licitaciones

El sistema DEBE extraer licitaciones desde `api.mercadopublico.cl` utilizando la API de búsqueda de licitaciones publicadas.

**Comportamiento esperado:**
- El worker de extracción DEBE obtener el ticket de autenticación desde configuración
- `[CORREGIDO]` La API acepta **un único día** por petición, en formato `DDMMYYYY`. El rango de fechas es una abstracción de la app: el Worker itera día por día en un loop y lanza una petición separada por cada día del rango configurado por el usuario
- `[CORREGIDO]` La API no soporta paginación confirmada en el endpoint de listado diario. No se implementará paginación automática hasta confirmar que el endpoint la soporta. El campo `Cantidad` de la respuesta se usará únicamente como dato informativo para logging
- `[CORREGIDO]` La API gubernamental no retorna código HTTP 429 de forma confirmada. El control de tasa se implementa mediante una **pausa fija configurable entre peticiones** (mínimo 2 segundos), no mediante detección de código 429
- `[DOCUMENTADO OFICIALMENTE]` Cada ticket tiene un **límite de 10.000 peticiones HTTP por día**. El límite aplica por llamada `requests.get()`, no por licitaciones devueltas: una petición de listado diario que retorna 450 licitaciones consume **1 solicitud**, no 450. El cuello de botella real son las llamadas de detalle individuales (1 solicitud por cada licitación). En uso diario normal (extracción de 1-7 días con ~200 licitaciones relevantes por día) el límite no representa un problema. El riesgo existe únicamente en **cargas históricas masivas**: extraer más de ~48 días de golpe con 200+ licitaciones relevantes por día podría acercarse al límite. En ese caso el Worker debe distribuir la extracción en múltiples días de ejecución
- El sistema DEBE manejar errores 500 con reintentos automáticos (máximo 3 intentos, backoff exponencial de 1.5 segundos base)
- El sistema DEBE manejar errores de red (timeout, conexión rechazada) con los mismos reintentos que los errores 500

**Escenario: Extracción exitosa por rango de fechas**
- GIVEN usuario configura ticket de API y rango de fechas (últimos 7 días)
- WHEN worker de extracción ejecuta la tarea
- THEN sistema lanza una petición a la API por cada día del rango, en secuencia
- AND espera mínimo 2 segundos entre cada petición
- AND cada licitación recibida se procesa mediante UPSERT a la base de datos
- AND los datos obtenidos son: código externo, título, fecha publicación, fecha cierre, organismo (código y nombre), estado

**Escenario: Error de servidor en petición diaria**
- GIVEN worker intenta descargar licitaciones para el día "05052026"
- AND la API responde con error 500
- THEN sistema espera y reintenta hasta 3 veces con backoff exponencial
- AND si los 3 intentos fallan, registra el fallo en log y continúa con el siguiente día
- AND notifica al usuario al finalizar qué días tuvieron errores

---

#### Requisito: Extracción de Detalle de Licitación

El sistema DEBE extraer el detalle completo de cada licitación cuya puntuación en la extracción de resumen sea mayor a 0.

**Comportamiento esperado:**
- El sistema DEBE ejecutar extracción de detalle solo para licitaciones con score > 0 tras la evaluación de resumen
- `[CORREGIDO]` La extracción de detalle obtiene los siguientes campos, confirmados por el comportamiento real de la API: descripción completa, listado de productos/ítems (nombre, cantidad, unidad de medida, descripción del ítem)
- `[CORREGIDO]` Campos como "condiciones de participación" y "criterios de evaluación" NO se especifican como requeridos porque su disponibilidad en el endpoint no está confirmada. Si están presentes en la respuesta se ignorarán en esta versión
- El sistema DEBE recalcular el score total sumando los puntos del detalle (descripción + productos) a los del resumen (título)
- El detalle DEBE actualizar la entidad Licitacion existente mediante UPSERT
- El campo `tiene_detalle` DEBE marcarse como `True` solo cuando la descarga del detalle fue exitosa

**Escenario: Detalle suma puntuación adicional**
- GIVEN licitación "L1" tiene score 15 puntos en extracción de resumen por coincidencia en título
- WHEN worker ejecuta extracción de detalle y encuentra coincidencia en descripción
- THEN sistema suma 10 puntos adicionales del detalle
- AND Licitación "L1" ahora tiene score_total de 25 puntos
- AND `justificacion_score` registra qué campos y reglas contribuyeron a cada parte del score

---

### 1.2 Sistema de Scoring Recargable en Caliente

#### Requisito: Motor de Scoring con Palabras Clave

El sistema DEBE evaluar cada licitación usando un motor de scoring basado en reglas configurables por el usuario.

**Comportamiento esperado:**
- El usuario DEBE poder definir palabras clave con pesos diferenciados por campo (título, descripción, productos)
- Cada palabra clave DEBE tener un peso independiente para cada campo
- `[CORREGIDO]` Cuando el usuario guarda cambios en las reglas, el sistema DEBE recalcular automáticamente los scores de todas las licitaciones que cumplan **ambas** condiciones:
  1. Estar en etapa activa del pipeline: `Candidata`, `Seguimiento` u `Ofertada`
  2. Tener estado de API `Publicada` (código 5)
- `[CORREGIDO]` Las licitaciones con etapa `ignorada` o estado distinto a `Publicada` NO se recalculan para mantener el rendimiento
- `[CORREGIDO]` El recálculo se ejecuta en un `ScoringWorker` (QThread separado) para no bloquear la UI. La UI debe mostrar un indicador de progreso durante el recálculo
- `[CORREGIDO]` Al finalizar el recálculo, la UI actualiza las vistas de las tres pestañas del pipeline automáticamente
- El scoring DEBE ser thread-safe: las reglas se copian al inicio de cada cálculo para no interferir con extracciones en curso
- Las licitaciones con score = 0 NO DEBEN aparecer en las vistas del pipeline

**Escenario: Usuario modifica palabras clave → recálculo acotado**
- GIVEN usuario tiene licitaciones distribuidas en las tres etapas del pipeline
- AND algunas tienen estado "Publicada" y otras "Cerrada" o "Adjudicada"
- WHEN usuario modifica el peso de la palabra "construcción" de 10 a 20 puntos en título
- AND usuario guarda la nueva configuración
- THEN sistema lanza ScoringWorker en segundo plano
- AND ScoringWorker recalcula únicamente las licitaciones en etapas Candidata/Seguimiento/Ofertada con estado Publicada
- AND UI muestra indicador de progreso durante el recálculo
- AND al finalizar, las tres pestañas del pipeline actualizan sus datos

**Escenario: Scoring en contexto de concurrencia**
- GIVEN worker de extracción está calculando scores de 100 licitaciones
- AND usuario modifica las reglas de scoring en la UI
- THEN sistema debe usar una copia de las reglas al momento de iniciar cada cálculo
- AND no debe afectar cálculos en curso (thread-safe mediante threading.Lock)

---

#### Requisito: Scoring por Organismo Comprador

El sistema DEBE permitir configurar un puntaje fijo por organismo comprador que se sume al score de cualquier licitación de ese organismo.

**Comportamiento esperado:**
- El usuario DEBE poder asignar puntaje positivo, negativo o neutro a cada organismo
- El puntaje del organismo DEBE sumarse al score_total durante la extracción y durante cualquier recálculo
- `[ACTUALIZADO]` La API **sí tiene** un endpoint oficial para obtener todos los organismos públicos: `GET /servicios/v1/Publico/Empresas/BuscarComprador?ticket=...`. Este endpoint retorna la lista completa con código y nombre de cada organismo. El comando `poetry run seed` PUEDE usar este endpoint como fuente alternativa o complementaria al CSV externo. La decisión de implementación queda al criterio del agente que construya el seed, pero el endpoint existe y es válido usarlo
- `[DOCUMENTADO]` La API también provee el código y nombre del organismo dentro de los datos de cada licitación extraída. Los organismos nuevos detectados durante la extracción se registran automáticamente si no existen en la BD, con `puntaje_fijo = 0`

---

### 1.3 Pipeline de Tres Etapas

#### Requisito: Clasificación en Pipeline

El sistema DEBE clasificar las licitaciones en un pipeline de tres etapas operativas: Candidata → Seguimiento → Ofertada.

**Comportamiento esperado:**
- Las licitaciones con score > 0 DEBEN clasificarse automáticamente como `Candidata` al ser extraídas
- `[CORREGIDO]` El usuario DEBE poder mover licitaciones entre etapas mediante **menú contextual (clic derecho)** sobre la fila de la licitación en la tabla. No se implementa drag-and-drop
- El menú contextual DEBE mostrar solo las etapas de destino válidas (no la etapa actual)
- El sistema DEBE mostrar indicadores visuales de cantidad de licitaciones por etapa
- Las licitaciones con score = 0 NO DEBEN aparecer en ninguna etapa del pipeline
- `[CORREGIDO]` Un texto de ayuda visible en la UI debe indicar que el clic derecho habilita opciones de movimiento (para descubrimiento de la función)

**Comportamiento no esperado:**
- El sistema NO DEBE implementar drag-and-drop entre etapas
- El sistema NO DEBE mover licitaciones automáticamente entre etapas tras el recálculo de scores
- Las licitaciones con score = 0 NO DEBEN ocupar espacio visual en el pipeline

**Escenario: Movimiento manual entre etapas**
- GIVEN el usuario está en la pestaña "Candidatas"
- AND existe la licitación "L1" con score 20 visible en la tabla
- AND hay un texto de ayuda visible que indica que el clic derecho habilita opciones
- WHEN el usuario hace clic derecho sobre la fila de "L1"
- THEN aparece un menú contextual con las opciones "Mover a Seguimiento" y "Mover a Ofertadas" (no aparece la opción de la etapa actual)
- WHEN el usuario selecciona "Mover a Seguimiento"
- THEN "L1" desaparece inmediatamente de la vista "Candidatas"
- AND la tabla de "Candidatas" se actualiza sin necesidad de recargar la página
- AND si el usuario navega a la pestaña "Seguimiento", "L1" aparece ahí con el mismo score y datos
- AND el cambio de etapa persiste en la base de datos aunque se cierre y reabra la aplicación

**Escenario: Clasificación automática por score al extraer**
- GIVEN el sistema extrae una licitación nueva desde la API con el título "Compra de equipos de construcción"
- AND las reglas activas asignan 25 puntos a coincidencias en el título
- WHEN el motor de scoring evalúa el título de la licitación
- THEN el sistema calcula score_resumen = 25
- AND dado que score_resumen > 0, descarga el detalle completo de la licitación
- AND recalcula el score_total sumando score_resumen + score_detalle + puntaje_organismo
- AND dado que score_total > 0, asigna etapa = "candidata" automáticamente
- AND la licitación aparece en la pestaña "Candidatas" al finalizar la extracción

**Escenario: Licitación con score cero no aparece en el pipeline**
- GIVEN el sistema extrae una licitación cuyo título no coincide con ninguna palabra clave
- WHEN el motor de scoring evalúa el título
- THEN el sistema calcula score_resumen = 0
- AND dado que score_resumen = 0, no descarga el detalle (ahorro de una solicitud HTTP)
- AND la licitación se guarda en BD con etapa = "ignorada"
- AND la licitación NO aparece en ninguna de las tres pestañas del pipeline

---

### 1.4 Exportación a Excel/CSV

#### Requisito: Exportación con Procesamiento por Lotes

El sistema DEBE permitir exportar licitaciones a Excel o CSV, procesando grandes volúmenes sin bloquear la UI.

**Comportamiento esperado:**
- El usuario DEBE poder exportar licitaciones de una etapa específica o de todas
- El usuario DEBE poder elegir formato (Excel `.xlsx` o CSV)
- El sistema DEBE procesar las licitaciones en lotes de 1000 registros para mantener consumo de RAM constante
- El sistema DEBE actualizar el progreso de exportación en la UI
- La exportación NO DEBE consumir RAM proporcional al total de registros

**Escenario: Exportación de 5000 licitaciones**
- GIVEN usuario selecciona exportar 5000 licitaciones a CSV
- WHEN usuario inicia exportación
- THEN worker de exportación procesa en lotes de 1000
- AND la UI muestra progreso: "Exportando... 1000/5000 (20%)"
- AND al finalizar, archivo se guarda en ubicación seleccionada por usuario

---

### 1.5 Piloto Automático Programable

#### Requisito: Programación de Ejecución Automática

El sistema DEBE permitir configurar una ejecución automática diaria con hora específica.

**Comportamiento esperado:**
- El usuario DEBE poder habilitar/deshabilitar el piloto automático
- El usuario DEBE poder configurar la hora de ejecución (formato 24 horas)
- `[DOCUMENTADO OFICIALMENTE]` La documentación oficial de ChileCompra recomienda ejecutar procesos de alta demanda **entre las 22:00 y las 07:00 horas** para mayor estabilidad. El Piloto Automático DEBE mostrar esta recomendación al usuario y usar **22:30** como hora sugerida por defecto (en lugar de cualquier hora diurna)
- La configuración DEBE persistir entre reinicios de la aplicación (almacenada en la entidad `Configuracion` de la base de datos)
- El piloto DEBE ejecutarse automáticamente a la hora configurada cada día

**Comportamiento de reintentos:**
- Si la extracción automática falla, el sistema DEBE reintentar hasta 3 veces
- Los reintentos DEBEN ejecutarse con backoff de 5, 10, 20 minutos
- Si todos los reintentos fallan, el sistema DEBE registrar el fallo y notificar al usuario al abrir la app

**Escenario: Configuración de piloto automático**
- GIVEN usuario habilita piloto automático para las 20:30 horas
- AND usuario cierra la aplicación
- WHEN usuario abre la app al día siguiente
- THEN la configuración de las 20:30 sigue activa (persistida en BD)
- AND si la hora ya pasó y no se ejecutó, notifica al usuario que hubo una ejecución pendiente

---

## 2. ESPECIFICACIONES TÉCNICAS DEL STACK

### 2.1 PySide6 + QThread/Worker Pattern

#### Arquitectura de Threads

El sistema DEBE implementar separación estricta entre UI Thread y Worker Threads:

**UI Thread (Main Thread):**
- Maneja toda la interacción con el usuario
- Actualiza widgets y vistas
- NUNCA ejecuta operaciones bloqueantes (I/O, cálculo pesado)
- Instala manejador global de excepciones para capturar errores no manejados en workers

**Worker Threads:**
- `ExtraccionWorker`: ejecuta llamadas a API de Mercado Público (listado diario + detalle)
- `ScoringWorker`: recalcula scores de licitaciones activas en pipeline tras cambios de reglas
- `ExportacionWorker`: genera archivos Excel/CSV
- Cada worker hereda de `QThread` y usa signals para comunicarse con UI

**Comunicación UI-Workers usando Signals/Slots:**

```python
class ExtraccionWorker(QThread):
    progreso = Signal(str)       # mensaje de estado
    avance   = Signal(int, int)  # actual, total (para barra de progreso)
    finalizado = Signal()
    error    = Signal(str)       # mensaje de error

    def run(self):
        # Ejecución en thread separado
```

#### Patrones de Worker

**Patrón de Worker Limpio:**
- Cada worker DEBE implementar cleanup en el método `run()` usando `try/finally`
- Cada worker DEBE capturar sus propias excepciones y emitirlas como signals de error
- Los workers NO DEBEN modificar directamente la base de datos; deben delegar al repositorio

**Manejo de Estado Compartido:**
- El acceso a la configuración de scoring DEBE usar `threading.Lock`
- Las reglas de scoring se copian al inicio de cada evaluación para evitar race conditions
- El repositorio de datos usa sesiones aisladas por operación (session-per-request)

---

### 2.2 SQLAlchemy + PostgreSQL + Alembic

#### Modelos de Datos SQLAlchemy ORM

**Entidad: Licitacion**
- `id`: Integer (PK, autoincrement)
- `codigo_externo`: String(50) (unique, indexed)
- `nombre`: String(500)
- `descripcion`: Text
- `detalle_productos`: Text (texto formateado con nombre, cantidad y unidad de cada ítem)
- `fecha_publicacion`: DateTime
- `fecha_cierre`: DateTime
- `fecha_inicio`: DateTime
- `fecha_adjudicacion`: DateTime
- `codigo_organismo`: String (FK → `organismos.codigo`) `[CORREGIDO]`
- `codigo_estado`: Integer (FK → `estados_licitacion.codigo`)
- `score_resumen`: Integer (default 0) — puntos obtenidos del título
- `score_detalle`: Integer (default 0) — puntos obtenidos de descripción y productos
- `score_total`: Integer (default 0, indexed) — suma de resumen + detalle + puntaje organismo
- `etapa`: String — valores: `'candidata'`, `'seguimiento'`, `'ofertada'`, `'ignorada'`
- `justificacion_score`: Text — detalle legible de qué reglas aplicaron y cuánto sumó cada una
- `tiene_detalle`: Boolean (default False)
- `fecha_extraccion`: DateTime
- `fecha_actualizacion`: DateTime

**Entidad: PalabraClave**
- `id`: Integer (PK)
- `termino`: String(100) (indexed)
- `categoria`: String(100)
- `peso_titulo`: Integer (default 0)
- `peso_descripcion`: Integer (default 0)
- `peso_productos`: Integer (default 0)
- `activa`: Boolean (default True)
- `fecha_creacion`: DateTime

**Entidad: Organismo** `[ACTUALIZADO]`
- `codigo`: String (PK, indexed) — código del organismo. **Advertencia:** la documentación oficial muestra el código como numérico en los parámetros de URL (ej: `CodigoOrganismo=6945`), pero el tipo exacto del campo dentro del JSON de respuesta de licitaciones no está confirmado sin ver una respuesta real. Se define como String por precaución y compatibilidad. Si al implementar se confirma que es numérico, se debe corregir el tipo y actualizar este spec
- `nombre`: String(200) (indexed)
- `puntaje_fijo`: Integer (default 0)
- `fecha_creacion`: DateTime
- **Nota:** El campo `rut` fue eliminado. El catálogo inicial se puede cargar desde un archivo CSV externo (`poetry run seed`) o consumiendo el endpoint oficial `BuscarComprador`. Los organismos nuevos detectados durante la extracción se registran automáticamente con `puntaje_fijo = 0`

**Entidad: EstadoLicitacion**
- `id`: Integer (PK)
- `codigo`: Integer (unique)
- `descripcion`: String(100)
- **Nota:** Los estados conocidos de la API son: 5 = Publicada, 6 = Cerrada, 7 = Desierta, 8 = Adjudicada, 18 = Revocada, 19 = Suspendida

**Entidad: Configuracion**
- `id`: Integer (PK)
- `clave`: String(50) (unique)
- `valor`: Text
- `fecha_actualizacion`: DateTime
- **Uso principal:** persistencia de configuración del Piloto Automático entre reinicios

---

#### Estrategias de Upsert

El sistema DEBE usar el dialecto PostgreSQL de SQLAlchemy para operaciones de UPSERT:

```python
from sqlalchemy.dialects.postgresql import insert

def upsert_licitacion(session, licitacion_data):
    stmt = insert(Licitacion).values(**licitacion_data)
    stmt = stmt.on_conflict_do_update(
        index_elements=['codigo_externo'],
        set_={
            'nombre': stmt.excluded.nombre,
            'descripcion': stmt.excluded.descripcion,
            'score_resumen': stmt.excluded.score_resumen,
            'score_total': stmt.excluded.score_total,
            'fecha_actualizacion': func.now()
        }
    )
    session.execute(stmt)
```

#### Migraciones con Alembic

El sistema DEBE usar Alembic para gestión de migraciones:
- Directorio: `alembic/versions/`
- Archivo de configuración: `alembic.ini`
- Entorno: `alembic/env.py` con configuración para PostgreSQL, leyendo `DATABASE_URL` desde `.env`

**Migración inicial requerida:**
- Tablas: `licitaciones`, `palabras_clave`, `organismos`, `estados_licitacion`, `configuracion`
- Índices: `idx_licitacion_codigo_externo`, `idx_licitacion_etapa`, `idx_licitacion_score_total`, `idx_palabra_clave_termino`, `idx_organismo_codigo`

#### Concurrencia con Sesiones SQLAlchemy

**Estrategia de sesiones:**
- Cada worker usa su propia sesión (no compartida entre threads)
- Sesiones con `expire_on_commit=False` para evitar problemas de lazy loading entre threads
- Transacciones explícitas: `begin()` → operaciones → `commit()` o `rollback()`

---

### 2.3 Poetry

#### Estructura de Proyecto

```
monitor_licitaciones/
├── pyproject.toml
├── README.md
├── .env.example
├── src/
│   └── monitor_licitaciones/
│       ├── __init__.py
│       ├── main.py                  # Entry point PySide6
│       ├── config.py                # Carga de configuración
│       ├── ui/                      # Capa de presentación
│       │   ├── __init__.py
│       │   ├── main_window.py
│       │   ├── widgets/
│       │   └── dialogs/
│       ├── workers/                 # QThread workers
│       │   ├── __init__.py
│       │   ├── extraccion_worker.py
│       │   ├── scoring_worker.py
│       │   └── exportacion_worker.py
│       ├── domain/                  # Lógica de negocio pura
│       │   ├── __init__.py
│       │   ├── scoring/
│       │   │   ├── motor_scoring.py
│       │   │   └── gestor_reglas.py
│       │   └── pipeline/
│       │       └── gestor_pipeline.py
│       ├── infrastructure/          # Capa de datos
│       │   ├── __init__.py
│       │   ├── database/
│       │   │   ├── connection.py
│       │   │   ├── repositorio.py
│       │   │   └── modelos.py
│       │   └── api/
│       │       └── cliente_mercado_publico.py
│       └── cli/                     # Scripts CLI
│           ├── __init__.py
│           ├── migrate.py
│           ├── init_db.py
│           └── seed.py              # Carga CSV de organismos
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
├── tests/
└── docs/
```

#### Dependencias (pyproject.toml) `[CORREGIDO]`

```toml
[tool.poetry]
name = "monitor-licitaciones-ai"
version = "3.0.0"
description = "Monitor de Licitaciones - Mercado Público Chile"
authors = ["Usuario"]

[tool.poetry.dependencies]
python = "^3.10"
PySide6 = "^6.5.0"
SQLAlchemy = "^2.0.0"
psycopg2-binary = "^2.9.0"
alembic = "^1.12.0"
python-dotenv = "^1.0.0"
requests = "^2.31.0"
openpyxl = "^3.1.0"
pydantic = "^2.0.0"
loguru = "^0.7.0"
pandas = "^2.0.0"

# ELIMINADO: python-csv no existe como paquete. csv es parte de la librería estándar de Python.

[tool.poetry.group.dev.dependencies]
pytest = "^7.4.0"
pytest-qt = "^4.2.0"
pytest-cov = "^4.1.0"
```

#### Scripts CLI

- `poetry run init-db`: Inicializa base de datos y ejecuta migraciones de Alembic
- `poetry run seed`: Carga catálogo inicial de organismos desde archivo CSV externo
- `poetry run migrate`: Ejecuta migraciones de Alembic pendientes

---

## 3. ESPECIFICACIONES DE ARQUITECTURA

### 3.1 Patrón de Diseño: Layered Architecture

El sistema DEBE seguir una arquitectura por capas:

**Capa de Presentación (UI):**
- Ubicación: `src/monitor_licitaciones/ui/`
- Responsabilidad: Renderizado de vistas, manejo de eventos de usuario
- Dependencias: Solo hacia domain (sin acceso directo a database ni API)

**Capa de Aplicación (Workers):**
- Ubicación: `src/monitor_licitaciones/workers/`
- Responsabilidad: Orquestación de operaciones, comunicación asíncrona con la UI
- Dependencias: domain, infrastructure

**Capa de Dominio:**
- Ubicación: `src/monitor_licitaciones/domain/`
- Responsabilidad: Lógica de negocio pura (scoring, clasificación de pipeline)
- Dependencias: Ninguna (framework-agnostic, 100% testeable sin BD ni API)

**Capa de Infraestructura:**
- Ubicación: `src/monitor_licitaciones/infrastructure/`
- Responsabilidad: Acceso a datos externos (BD, API de Mercado Público)
- Dependencias: Solo hacia modelos de dominio

---

### 3.2 Interfaces entre Componentes

Las interfaces definen el **contrato que debe cumplir cada componente** antes de implementarlo. Están escritas usando `Protocol` de Python, que es la forma estándar de declarar interfaces sin necesidad de herencia. Su propósito no es ser código ejecutable sino ser una especificación inequívoca: si dos agentes distintos construyen el cliente de API y el Worker de extracción por separado, las interfaces garantizan que las piezas encajen sin necesidad de coordinar en el momento. También permiten que los tests usen implementaciones falsas (mocks) sin modificar el código de producción.

**Interfaz: RepositorioLicitacion**
```python
class RepositorioLicitacion(Protocol):
    def obtener_por_etapa(etapa: str, pagina: int, por_pagina: int) -> list[Licitacion]: ...
    def obtener_activas_en_pipeline(etapas: list[str], codigo_estado_activo: int) -> list[Licitacion]: ...
    def upsert(datos: dict) -> Licitacion: ...
    def actualizar_etapa(codigo_externo: str, etapa: str) -> bool: ...
    def actualizar_score(codigo_externo: str, score_total: int, justificacion: str) -> bool: ...
```

**Interfaz: ClienteAPI** `[ACTUALIZADO]`
```python
class ClienteAPI(Protocol):
    def obtener_licitaciones_dia(fecha: str) -> list[dict]: ...
    # fecha en formato DDMMYYYY, una petición por día
    # Cada llamada consume 1 solicitud del límite diario de 10.000,
    # independientemente de cuántas licitaciones retorne la respuesta

    def obtener_detalle(codigo_externo: str) -> dict | None: ...
    # Cada llamada consume 1 solicitud del límite diario de 10.000

    def obtener_organismos() -> list[dict]: ...
    # [CORREGIDO] SÍ existe un endpoint oficial para esto:
    # GET /servicios/v1/Publico/Empresas/BuscarComprador?ticket=...
    # Retorna lista completa de organismos públicos con código y nombre.
    # Cada llamada consume 1 solicitud del límite diario de 10.000.
    # Usar principalmente en el comando seed, no en extracción rutinaria.
```

**Interfaz: MotorScoring**
```python
class MotorScoring(Protocol):
    def evaluar_titulo(texto: str) -> tuple[int, list[str]]: ...
    def evaluar_detalle(descripcion: str, productos: str) -> tuple[int, list[str]]: ...
    def recargar_reglas() -> None: ...
```

---

### 3.3 Manejo de Errores y Logging

**Estrategia de manejo de errores:**
- Errores de configuración: Fallo al inicio con mensaje claro (fail-fast)
- `[CORREGIDO]` Errores de API: reintentos automáticos para 500 y errores de red. No se espera código 429 de esta API; si aparece se trata igual que un 500
- Errores de base de datos: Logging con detalle, rollback de transacción
- Errores en workers: Captura local, emisión como signal de error a UI

**Logging con Loguru:**
- Nivel `DEBUG`: Operaciones detalladas de debugging
- Nivel `INFO`: Operaciones normales (inicio de extracción, fin de exportación, licitaciones procesadas)
- Nivel `WARNING`: Situaciones anómalas recuperables (timeout, error 500 con reintento pendiente)
- Nivel `ERROR`: Fallos que requieren intervención (fallo de conexión definitivo, excepción no manejada)

**Estructura de logs:**
```
logs/
└── monitor_licitaciones_{fecha}.log
```

---

### 3.4 Configuración y Variables de Entorno

**Variables requeridas (en `.env`):**
- `DATABASE_URL`: `postgresql://user:pass@host:port/dbname`
- `TICKET_MERCADO_PUBLICO`: Ticket de autenticación para la API de Mercado Público

**Variables opcionales:**
- `LOG_LEVEL`: `DEBUG` | `INFO` | `WARNING` | `ERROR` (default: `INFO`)
- `EXPORT_PATH`: Ruta por defecto para exportaciones
- `API_PAUSA_SEGUNDOS`: Pausa entre peticiones a la API (default: `2`, mínimo recomendado)

**Carga de configuración:**
- Usar `python-dotenv` para cargar desde `.env`
- Validar al inicio que las variables requeridas existan
- Mostrar error claro y detallado si falta alguna variable requerida (fail-fast)

---

## 4. CASOS DE USO TÉCNICOS DETALLADOS

### Caso de Uso 1: Usuario configura palabras clave → Sistema recarga scoring acotado

**Flujo técnico:**
1. Usuario abre diálogo de configuración de palabras clave (ventana PySide6)
2. Sistema carga palabras clave actuales desde base de datos
3. Usuario modifica pesos y guarda
4. Sistema actualiza tabla `palabras_clave` en base de datos
5. `[CORREGIDO]` Sistema lanza `ScoringWorker` en segundo plano
6. `ScoringWorker` consulta licitaciones que cumplan: etapa IN (`candidata`, `seguimiento`, `ofertada`) AND `codigo_estado = 5` (Publicada)
7. Para cada licitación del conjunto, recalcula `score_total` con las reglas actualizadas
8. Actualiza `score_total` y `justificacion_score` en BD
9. Al finalizar, emite signal a UI para que las tres pestañas recarguen sus datos

**Thread safety:**
- Las reglas se copian al inicio del `ScoringWorker` (snapshot de reglas)
- `threading.Lock` durante la copia de reglas
- Sesión SQLAlchemy independiente dentro del worker

---

### Caso de Uso 2: Extracción masiva por rango de fechas

**Flujo técnico:**
1. Usuario configura rango: fecha_inicio = "01/05/2026", fecha_fin = "05/05/2026"
2. `ExtraccionWorker` calcula los días del rango: [01/05, 02/05, 03/05, 04/05, 05/05]
3. Worker estima el consumo de solicitudes: `dias × (1 listado + N_estimado_detalles)` y lo loguea al inicio
4. Por cada día:
   - Construye parámetro `fecha` en formato `DDMMYYYY`
   - Llama a `api.obtener_licitaciones_dia(fecha)` → consume 1 solicitud
   - Espera mínimo 2 segundos antes de la siguiente llamada
   - Si error 500: reintenta hasta 3 veces con backoff exponencial
   - Si 3 intentos fallan: loguea el fallo, emite aviso parcial, continúa con el siguiente día
5. Por cada licitación con score_resumen > 0: llama a `api.obtener_detalle(codigo_externo)` → consume 1 solicitud por licitación
6. Persiste las licitaciones del día en **lotes de 100 registros por transacción** (no en una sola transacción). Cada lote hace su propio commit. Si un lote falla, solo se repite ese lote, no todo el día. Esto evita locks prolongados en BD y es compatible con bases de datos en la nube donde las transacciones largas generan timeouts
7. Al finalizar todos los días, emite signal `finalizado` con resumen de estadísticas incluyendo total de solicitudes consumidas

---

### Caso de Uso 3: Usuario mueve licitación entre etapas

**Flujo técnico:** `[CORREGIDO]`
1. Usuario hace clic derecho sobre una fila en la tabla de Candidatas
2. UI muestra menú contextual con opciones disponibles: "Mover a Seguimiento", "Mover a Ofertadas"
3. Usuario selecciona una opción
4. UI llama directamente al repositorio (operación síncrona, es un UPDATE simple y rápido, no requiere Worker separado)
5. El repositorio localiza la licitación por su `codigo_externo` usando SQLAlchemy ORM y actualiza el campo `etapa` con el nuevo valor
6. Commit de la transacción
7. UI remueve la fila de la vista actual y emite señal global de datos actualizados

---

### Caso de Uso 4: Exportación grande → Procesamiento por lotes sin bloquear UI

**Flujo técnico:**
1. Usuario selecciona exportar licitaciones de etapa "Candidatas" a CSV
2. `ExportacionWorker` recibe la solicitud con etapa y formato
3. Worker consulta el total de registros para calcular el progreso
4. Worker procesa en chunks de 1000:
   - Lee 1000 licitaciones desde BD
   - Escribe al archivo (modo append para CSV)
   - Emite `avance(1000, total)`
   - Libera memoria del chunk antes del siguiente
5. Worker cierra archivo, emite signal `finalizado`
6. UI muestra diálogo de confirmación con ruta del archivo generado

---

## 5. REQUISITOS NO FUNCIONALES ADAPTADOS

### 5.1 Performance

**Consumo de RAM:**
- La aplicación debe consumir menos de 200MB en estado de reposo
- Cada worker adicional no debe agregar más de 50MB
- Procesamiento de exportación no debe exceder 100MB adicionales

**Tiempos de respuesta:**
- La UI debe permanecer responsiva durante extracciones masivas
- Los listados con paginación deben cargar en menos de 500ms
- El scoring de 1000 licitaciones debe completarse en menos de 5 segundos

**Manejo de memoria con grandes volúmenes:**
- Implementar paginación en todas las consultas de licitaciones hacia la UI
- El `ScoringWorker` procesa licitaciones en lotes para no cargar todo el conjunto en RAM

### 5.2 Robustez

**Errores de red y API:**
- Timeout de 15 segundos para llamadas a la API de Mercado Público
- `[CORREGIDO]` Reintentos con backoff exponencial (base 1.5s) para errores 500 y errores de red
- `[CORREGIDO]` Si aparece un código HTTP inesperado (incluyendo 429 si ocurre), se trata igual que un error 500
- Errores 4xx distintos de 500 (ej: 404 = licitación no encontrada): sin reintento, se loguea y se continúa

**Integridad de datos:**
- Transacciones atómicas para todas las operaciones de escritura
- Validación de datos antes de escribir en base de datos
- Logging de todas las operaciones de modificación

### 5.3 Usabilidad

**Interfaz de usuario:**
- Pestañas separadas para: Candidatas, Seguimiento, Ofertadas, Herramientas del Sistema
- Herramientas del Sistema incluye sub-pestañas: Extracción, Exportación, Palabras Clave, Organismos, Piloto Automático
- `[CORREGIDO]` Indicación visible de clic derecho para opciones de movimiento entre etapas
- Indicadores visuales de progreso durante operaciones largas (extracción, recálculo, exportación)
- Feedback claro de errores al usuario

**Criterio de éxito para usuario nuevo:**
- Configurar credenciales y ejecutar migraciones: menos de 5 minutos
- Primera extracción operativa: menos de 10 minutos desde instalación
- Exportar licitaciones: flujo intuitivo sin necesidad de documentación

---

## 6. CRITERIOS DE ACEPTACIÓN TÉCNICOS

### Extracción de Licitaciones
- [ ] Sistema extrae licitaciones iterando día por día dentro del rango configurado
- [ ] Sistema aplica pausa mínima de 2 segundos entre peticiones a la API
- [ ] Sistema reintenta errores 500 y de red hasta 3 veces con backoff exponencial
- [ ] Sistema continúa con el siguiente día si un día falla definitivamente
- [ ] Sistema extrae detalle únicamente de licitaciones con score_resumen > 0
- [ ] Campo `tiene_detalle` se marca `True` solo si la descarga de detalle fue exitosa
- [ ] Sistema loguea el total de solicitudes HTTP consumidas al finalizar cada extracción

### Scoring Recargable en Caliente
- [ ] Usuario puede modificar palabras clave sin reiniciar la app
- [ ] Al guardar cambios, ScoringWorker recalcula licitaciones en pipeline con estado Publicada
- [ ] ScoringWorker corre en thread separado sin bloquear la UI
- [ ] UI muestra progreso durante el recálculo y actualiza vistas al finalizar
- [ ] Scoring es thread-safe durante extracciones concurrentes
- [ ] Sistema aplica pesos diferenciados por campo (título, descripción, productos)

### Pipeline de Tres Etapas
- [ ] Licitaciones con score_total > 0 se clasifican como Candidata automáticamente
- [ ] Usuario puede mover licitaciones entre etapas mediante menú contextual (clic derecho)
- [ ] Sistema muestra indicadores visuales de cantidad por etapa
- [ ] Licitaciones con score_total = 0 no aparecen en pipeline
- [ ] UI incluye indicación visible de que el clic derecho habilita opciones

### Exportación
- [ ] Sistema exporta a formato Excel (.xlsx)
- [ ] Sistema exporta a formato CSV
- [ ] Exportación procesa en lotes de 1000 sin bloquear UI
- [ ] Sistema muestra progreso de exportación

### Piloto Automático
- [ ] Usuario puede configurar hora de ejecución automática
- [ ] Hora sugerida por defecto es 22:30 (alineada con recomendación oficial de ChileCompra)
- [ ] UI muestra nota informativa sobre el horario recomendado por ChileCompra (22:00-07:00)
- [ ] Configuración persiste entre reinicios (almacenada en tabla `configuracion`)
- [ ] Sistema reintenta hasta 3 veces si extracción falla (backoff 5, 10, 20 min)
- [ ] Sistema notifica al usuario si piloto falla o si hubo ejecución pendiente

### Configuración Inicial
- [ ] Sistema valida credenciales al iniciar y falla con mensaje claro si faltan (fail-fast)
- [ ] `poetry run init-db` crea estructura de base de datos vía Alembic
- [ ] `poetry run seed` carga catálogo de organismos (desde CSV externo o desde endpoint `BuscarComprador`)

---

## 7. STACK CONFIRMADO

| Componente | Tecnología |
|------------|------------|
| Lenguaje | Python 3.10+ |
| Gestor de dependencias | Poetry |
| UI Framework | PySide6 |
| Concurrencia | QThread Worker Pattern |
| ORM | SQLAlchemy 2.0 |
| Base de datos | PostgreSQL |
| Migraciones | Alembic |
| HTTP Client | Requests |
| Excel Export | OpenPyXL |
| Procesamiento tabular | Pandas |
| Logging | Loguru |
| Configuración | python-dotenv |
| Validación de datos | Pydantic |

---

## 8. RESTRICCIONES Y SUPUESTOS CONFIRMADOS SOBRE LA API

> Esta sección fue construida combinando el comportamiento observado en producción (código original) con la documentación oficial publicada en `api.mercadopublico.cl` (verificada en mayo 2026). Todo lo marcado como `[OFICIAL]` está extraído directamente de la documentación de ChileCompra.

### Comportamiento del endpoint de licitaciones
- `[OFICIAL]` La API acepta **un día por petición** en formato `ddmmaaaa`. No existe parámetro de rango de fechas. El loop día a día es responsabilidad de la app.
- `[OFICIAL]` La búsqueda por fecha retorna **información básica** de las licitaciones del día. La búsqueda por código retorna **información detallada** de esa licitación específica. Son dos modos del mismo endpoint.
- La API **no tiene modo sandbox**. Los tests del cliente HTTP deben usar mocks, nunca peticiones reales.
- La paginación del listado diario **no está documentada**. No se implementa hasta confirmar que el endpoint la soporta.

### Límites y restricciones de uso
- `[OFICIAL]` Cada ticket tiene un **límite de 10.000 peticiones HTTP por día**. El límite no es modificable.
- `[OFICIAL]` El límite aplica **por llamada HTTP individual**, no por licitaciones dentro de la respuesta. Una petición de listado que devuelve 450 licitaciones consume 1 solicitud, no 450.
- `[OFICIAL]` ChileCompra monitorea el uso **por dirección IP** y puede establecer restricciones de acceso según volumen de peticiones desde una misma IP. Las pausas entre peticiones son obligatorias.
- `[OFICIAL]` Para procesos de alta demanda, ChileCompra **recomienda ejecutar entre las 22:00 y las 07:00 horas**.
- `[OFICIAL]` La API **no retorna código 429**. Si se excede el límite o hay restricción por IP, el comportamiento observado es error 500 o corte de conexión. Ambos se tratan con el mismo mecanismo de reintentos.

### Códigos de estado oficiales confirmados
- `[OFICIAL]` 5 = Publicada, 6 = Cerrada, 7 = Desierta, 8 = Adjudicada, 18 = Revocada, 19 = Suspendida

### Tipos de licitación oficiales confirmados
- `[OFICIAL]` L1 (Pública <100 UTM), LE (Pública 100-1000 UTM), LP (Pública >1000 UTM), LS (Servicios personales), B2 (Privada >1000 UTM), A1, D1, C1, C2, R1, CA, SE, entre otros. El validador regex `r'^\d+-\d+-[A-Z0-9]+$'` cubre todos los tipos actuales.

### Endpoint de organismos
- `[OFICIAL]` **Sí existe** un endpoint para obtener todos los organismos públicos: `GET /servicios/v1/Publico/Empresas/BuscarComprador?ticket=...`. Retorna lista completa con código y nombre.
- `[ADVERTENCIA]` El código de organismo aparece como **numérico** en los ejemplos de URL de la documentación (`CodigoOrganismo=6945`). Sin embargo, el tipo exacto del campo dentro del JSON de cada licitación no está confirmado. El modelo lo define como String por precaución; debe verificarse al implementar.
- También existe `GET /servicios/v1/Publico/Empresas/BuscarProveedor?rutempresaproveedor=...` para buscar proveedores por RUT. No es relevante para esta app pero documenta que el ecosistema de la API es más amplio.

### Evolución futura de la API
- `[RIESGO]` ChileCompra está activamente trabajando en **evolucionar sus APIs** (talleres de co-creación en marzo 2026, nueva API de Compra Ágil anunciada para mayo 2026). Los endpoints actuales pueden cambiar. No se debe sobre-construir lógica dependiente de detalles de respuesta no documentados. Los agentes deben implementar el cliente API con la interfaz `ClienteAPI(Protocol)` definida en la sección 3.2 para facilitar el reemplazo si la API cambia.

### Campos de detalle confirmados
- Los campos confirmados en el detalle de licitación son: descripción completa, listado de productos/ítems (nombre, cantidad, unidad de medida, descripción del ítem).
- Otros campos adicionales que pueda devolver la API se tratan como **datos opcionales** en esta versión. No se deben crear columnas en BD para campos no confirmados.

### Credenciales
- `[OFICIAL]` El ticket es **único por persona** (un ticket por RUT). ChileCompra puede suspender el acceso si detecta inconsistencias en los datos del solicitante o uso abusivo.

---

*Documento revisado, corregido y enriquecido con documentación oficial de api.mercadopublico.cl*
*Proyecto: ML_AI*
*Fecha de última modificación: Mayo 2026 — Revisión 3*
