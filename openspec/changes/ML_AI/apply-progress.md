# Apply Progress — Phase 7 (Fixes de Warnings)

**Change**: ML_AI — Monitor de Licitaciones
**Date**: 2026-05-13
**Mode**: Standard
**Final Status**: ✅ COMPLETE — 6/6 tasks done

---

## Completed Tasks

### ✅ T61 — Retry/backoff en `obtener_organismos()` (Quick Win)
**Warning W4**
- **Archivo**: `src/monitor_licitaciones/infrastructure/api/cliente_mp.py`
- **Qué**: Modificado `_request()` para aceptar `url: str | None` opcional. Refactorizado `obtener_organismos()` para usar `self._request()` con backoff exponencial.
- **Pruebas**: Agregados 4 tests en `test_cliente_mp.py` (exitoso, retry en 500, agota reintentos, 404).
- **DoD**: ✅ `obtener_organismos()` usa `self._request()`, tests pasando.

### ✅ T62 — Extraer `fecha_publicacion` del detalle
**Warning W5**
- **Archivos**: `extraccion_worker.py`, `models.py` (ya tenía), `repositorio_licitaciones.py` (ya manejaba)
- **Qué**: Agregada función helper `_parsear_fecha_api()` que convierte strings ISO 8601 a `datetime`. Agregado `fecha_publicacion` a los 3 branches de datos en `extraccion_worker.py`.
- **Pruebas**: 2 tests nuevos (extracción con fecha, fecha None sin detalle).
- **DoD**: ✅ `fecha_publicacion` persiste en BD, tests verifican extracción.

### ✅ T58 — Implementar `_ejecutar_extraccion_real()` en PilotoWorker
**Warning W1**
- **Archivo**: `src/monitor_licitaciones/workers/piloto_worker.py`
- **Qué**: Agregadas dependencias opcionales al constructor (`cliente_mp`, `repo_licitaciones`, `repo_reglas`, `gestor_reglas`). Implementado `_ejecutar_extraccion_real()` que crea `ExtraccionWorker` con fecha del día anterior y ejecuta `run()` síncrono dentro del hilo del piloto. RuntimeError si faltan dependencias (capturado por reintentos).
- **Pruebas**: 3 tests nuevos (creación correcta de ExtraccionWorker, error sin dependencias, reintentos capturan error). Tests existentes actualizados con `patch.object(worker, '_ejecutar_extraccion_real')`.
- **DoD**: ✅ Extracción real funcional, tests verifican con mock.

### ✅ T60 — Diálogo ficha técnica (doble clic)
**Warning W3**
- **Archivos**: `src/monitor_licitaciones/ui/dialogs/ficha_tecnica.py` (nuevo), `tabla_licitaciones.py` (modificado), `repositorio_licitaciones.py` (agregado `obtener_por_codigo()`), `main_window.py` (pasar repo a tablas)
- **Qué**: `FichaTecnicaDialog` muestra nombre, código, etapa, organismo, fecha_publicación, descripción, productos, scores y justificación. Conectado doble clic en tabla para abrir diálogo modal.
- **Pruebas**: 3 tests pytest-qt (datos completos, no encontrada, fecha None). Tests de exec_() omitidos por crash COM preexistente en Windows Qt CI.
- **DoD**: ✅ Diálogo funcional con datos, tests pasando.

### ✅ T59 — Gestión de organismos en UI (CRUD)
**Warning W2**
- **Archivos**: `src/monitor_licitaciones/ui/dialogs/gestion_organismos.py` (nuevo), `repositorio_reglas.py` (agregado `guardar_organismo()`), `main_window.py` (reemplazar placeholder)
- **Qué**: `GestionOrganismosDialog` con tabla de organismos, botones Agregar, Editar, Desactivar. Sub-diálogo `_OrganismoEditDialog` con validación de código/nombre.
- **Pruebas**: 4 tests (carga en tabla, guardar nuevo, actualizar existente, desactivar con puntaje 0).
- **DoD**: ✅ CRUD funcional, datos persistidos en BD, tests pytest-qt pasando.

### ✅ T63 — Verificar test_config.py (falso positivo)
**Warning W6**
- **Archivo**: `tests/test_infrastructure/test_config.py`
- **Qué**: Verificado que el archivo existe (105 líneas, 7 tests) y cubre TODOS los requisitos de task 1.7. Task 1.10 cubierta por `test_repositorio_licitaciones.py`. Documentado como falso positivo del verify.
- **DoD**: ✅ Inconsistencia resuelta — documentado como falso positivo.

---

## Files Changed

| File | Action | What Was Done |
|------|--------|---------------|
| `src/monitor_licitaciones/infrastructure/api/cliente_mp.py` | Modified | `_request()` acepta URL opcional; `obtener_organismos()` usa retry |
| `src/monitor_licitaciones/workers/extraccion_worker.py` | Modified | Helper `_parsear_fecha_api()`; `fecha_publicacion` en datos |
| `src/monitor_licitaciones/workers/piloto_worker.py` | Modified | Dependencias extracción; `_ejecutar_extraccion_real()` implementado |
| `src/monitor_licitaciones/infrastructure/database/repositorio_licitaciones.py` | Modified | Nuevo método `obtener_por_codigo()` |
| `src/monitor_licitaciones/infrastructure/database/repositorio_reglas.py` | Modified | Nuevo método `guardar_organismo()` |
| `src/monitor_licitaciones/ui/widgets/tabla_licitaciones.py` | Modified | Acepta `repo_licitaciones`; `_on_doble_clic` abre FichaTecnicaDialog |
| `src/monitor_licitaciones/ui/main_window.py` | Modified | Pasa repo a tablas; Reemplaza placeholder organismos con GestionOrganismosDialog |
| `src/monitor_licitaciones/ui/dialogs/ficha_tecnica.py` | **Created** | Diálogo modal ficha técnica de licitación |
| `src/monitor_licitaciones/ui/dialogs/gestion_organismos.py` | **Created** | Diálogo CRUD para organismos |
| `tests/test_infrastructure/test_cliente_mp.py` | Modified | 4 tests nuevos para `obtener_organismos()` |
| `tests/test_workers/test_extraccion_worker.py` | Modified | 2 tests nuevos para `fecha_publicacion` |
| `tests/test_workers/test_piloto_worker.py` | Modified | 3 tests nuevos para `_ejecutar_extraccion_real()`; tests existentes parchados |
| `tests/test_ui/test_dialogs.py` | **Created** | Tests para FichaTecnicaDialog y GestionOrganismosDialog |

---

## Test Results

| Suite | Tests | Status |
|-------|-------|--------|
| Original (Phase 1-6) | 97 | ✅ All passing |
| New T61 (cliente_mp) | 4 | ✅ Added |
| New T62 (extraccion_worker) | 2 | ✅ Added |
| New T58 (piloto_worker) | 3 | ✅ Added |
| New T60 (ficha_tecnica) | 3 | ✅ Added |
| New T59 (organismos UI) | 4 | ✅ Added |
| **Total** | **113** | **✅ ALL PASSING** |
| **Coverage** | **81.71%** (≥80%) | **✅ PASS** |

---

## Deviations from Design

None — implementation matches design.

## Issues Found

1. **Windows COM exception 0x8001010d**: Tests de diálogos modales Qt con `exec_()` crashean en Windows CI. Es el mismo problema preexistente en `test_widgets.py` (test_filtro_debounce_emite_una_sola_vez). No afecta funcionalidad.

---

## Warnings Resolution

| Warning | Severity | Task | Resolution |
|---------|----------|------|------------|
| W1 — PilotoWorker placeholder | 🟡 Media | T58 | ✅ Implementado |
| W2 — Organismos UI placeholder | 🟡 Media | T59 | ✅ CRUD completo |
| W3 — Ficha técnica TODO | 🟡 Media | T60 | ✅ Diálogo modal |
| W4 — Sin retry en organismos | 🟢 Baja | T61 | ✅ Retry/backoff |
| W5 — fecha_publicacion faltante | 🟡 Media | T62 | ✅ Extraído del detalle |
| W6 — test_config.py missing | 🟢 Baja | T63 | ✅ Falso positivo |

---

*Documento de progreso — SDD Apply Phase 7*
*Proyecto: ML_AI | Fecha: Mayo 2026*
