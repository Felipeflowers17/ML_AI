# Estado Actual del Proyecto — ML_AI

## Fase Actual
PRE-ARCHIVE — VALIDACIÓN CON ENTORNO REAL — 🔄 EN CURSO
(Fase híbrida: smoke test → pytest suite → exploración manual contra Supabase + MP real)

## Fases Completadas
- [x] PRD — Documento: PRD_ML.md
- [x] SPEC — Documento: SPEC_ML.md
- [x] DESIGN — Documento: `openspec/changes/ML_AI/design_v2.md`
- [x] TASKS — Documento: `openspec/changes/ML_AI/tasks_v3.md`
  (versiones anteriores: `tasks_v2.md`, `tasks.md`) + Engram `sdd/ml-ai-monitor-licitaciones/tasks`
- [x] APPLY — COMPLETA — Phases 1-6 implementadas
- [x] VERIFY — COMPLETA — PASS (97/97 tests, 82.16% cobertura, 37/37 requisitos, 7/7 diseño, 57/57 tareas)
- [ ] ARCHIVE

## Phase 7: Fixes de Warnings (✅ COMPLETA)
| ID | Tarea | Severidad | Prioridad | Estado |
|----|-------|-----------|-----------|--------|
| T58 | Implementar `_ejecutar_extraccion_real()` | 🟡 Media | Alta | ✅ |
| T59 | Gestionar organismos en UI | 🟡 Media | Media | ✅ |
| T60 | Diálogo ficha técnica (doble clic) | 🟡 Media | Alta | ✅ |
| T61 | Retry en `obtener_organismos()` | 🟢 Baja | Alta (quick win) | ✅ |
| T62 | Extraer `fecha_publicacion` | 🟡 Media | Alta | ✅ |
| T63 | Verificar test_config.py | 🟢 Baja | Media | ✅ |

## Progreso de Phase APPLY

| Phase | Estado | Tareas | Tests |
|-------|--------|--------|-------|
| Phase 1 — Scaffolding + Foundation | ✅ Completa | 17/17 | 29/29 |
| Phase 2 — Core Domain | ✅ Completa | 7/7 | 20/20 |
| Phase 3 — Infrastructure Workers | ✅ Completa | 8/8 | 18/18 |
| Phase 4 — UI | ✅ Completa | 9/9 | 20/20 |
| Phase 5 — CLI + Entry Point | ✅ Completa | 5/5 | 8/8 |
| Phase 6 — E2E + Validación | ✅ Completa | 4/4 | 14/14 |
| Phase 7 — Fixes de Warnings | ✅ Completa | 6/6 | 16/16 |

**Tests acumulados:** 113/113 passing ✅ (0 fallantes)

## Cobertura
- Total: 81.71% (432 stmts, 79 missed) ✅ (umbral 80% superado)
- `domain/`: 100% ✅
- `infrastructure/api/`: cubierto por tests de cliente_mp con responses mock ✅
- Coverage enforce: funciona (pytest falla con exit code ≠ 0 si < 80%)
- Omisiones: `*/cli/*`, `*/main.py`, `*/ui/*`, `*/workers/exportacion_worker.py`,
  `*/infrastructure/database/connection.py`, `*/infrastructure/database/repositorio_configuracion.py`,
  `*/infrastructure/api/schemas_mp.py`

## Nota técnica: Cobertura en QThread
coverage.py NO puede trackear código que corre dentro de `QThread.run()`. Los workers
(ScoringWorker, ExtraccionWorker, ExportacionWorker) ejecutan su lógica en hilos C++
que `sys.settrace` no puede seguir. Por eso `scoring_worker.py` (50%) y
`extraccion_worker.py` (36%) solo muestran cobertura en `__init__` y métodos accesibles
desde el hilo principal. Los tests existen y pasan, pero las líneas dentro de `run()`
aparecen como no cubiertas en el reporte.

## Última Sesión (APPLY Phase 7 — 13/05/2026)
- Qué se hizo: Implementación de Phase 7 (Fixes de Warnings) completa vía delegación a `sdd-apply`.
  - 6/6 tareas implementadas (T58-T63)
  - 113/113 tests passing, 81.71% cobertura (umbral 80% superado)
  - 16 tests nuevos agregados (4 cliente_mp + 2 extraccion_worker + 3 piloto_worker + 7 diálogos UI)
  - 2 archivos nuevos: `ficha_tecnica.py`, `gestion_organismos.py`
  - W1-W6 resueltos (W6 documentado como falso positivo)
  - Agente: sdd-apply con modelo opencode/deepseek-v4-flash-free

## Sesión Actual (13/05/2026) — PRE-ARCHIVE (1ra parte)
- **Decisión**: Opción C híbrida — smoke test → pytest → exploración manual contra .env real
- **Fix aplicado**: Refactor de `validar_entorno()` en main.py — 2 tests fallidos corregidos + 1 test nuevo
- **Tests**: 114/114 passing ✅ (antes 111/113, se agregó 1 test nuevo)
- **Smoke test**: App ARRANCA ✅ — ventana UI se muestra, conexión a Supabase OK
- **Issue detectado**: API MP responde HTTP 400 — ticket puede ser inválido o formato incorrecto
- **Sesión pausada** — retomar después

## Próximos pasos (pendientes)

### 1. VALIDACIÓN (continuar)
- Investigar HTTP 400 en API MP (ticket `4F829904-227F-4B2E-858F-1C6D0C1480CC`)
- Exploración manual de UI completa (scraping, scoring, exportación, ficha técnica)

### 2. ARCHIVE
Cerrar el cambio SDD: sincronizar delta specs, persistir estado final en engram,
y marcar el cambio como completado.