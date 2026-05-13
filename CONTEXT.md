# Estado Actual del Proyecto — ML_AI

## Fase Actual
APPLY (fase TASKS completada, lista para implementación)

## Fases Completadas
- [x] PRD — Documento: PRD_ML.md
- [x] SPEC — Documento: SPEC_ML.md
- [x] DESIGN — Documento: `openspec/changes/ML_AI/design_v2.md` ← ACTIVO
- [x] TASKS — Documento: `openspec/changes/ML_AI/tasks_v3.md` ← ACTIVO
  (versiones anteriores: `tasks_v2.md`, `tasks.md`) + Engram `sdd/ml-ai-monitor-licitaciones/tasks`
- [ ] APPLY — Pendiente: delegar al agente SDD apply
- [ ] VERIFY
- [ ] ARCHIVE

## Última Sesión
- Fecha: 12/05/2026
- Qué se hizo: Se actualizó design_v2.md como versión activa, se ejecutó fase TASKS (delegada al agente SDD tasks)
- Dónde quedamos: Listos para ejecutar fase APPLY — estrategia stacked-to-main confirmada

## Decisiones Tomadas
| Decisión | Opción Elegida | Fecha | Detalle en Engram |
|----------|---------------|-------|-------------------|
| Arquitectura Dominio | Paquetes por responsabilidad | 08/05/2026 | #monitor-v3 |
| Scoring recargable | Lock + copia profunda | 08/05/2026 | #monitor-v3 |
| Gestión configuración | Pydantic BaseSettings + reload manual | 08/05/2026 | #monitor-v3 |
| Estrategia testing | TDD mocks (dominio) + pytest-qt (UI) | 08/05/2026 | #monitor-v3 |
| Inicialización BD | Alembic + seed CLI (BuscarComprador) | 08/05/2026 | #monitor-v3 |
| Cómo ejecutar DESIGN | Agente SDD con decisiones confirmadas | 08/05/2026 | #monitor-v3-design-agente |
| Chain strategy PRs | stacked-to-main | 12/05/2026 | #ml-ai |
| Artifact store | hybrid (engram + openspec) | 08/05/2026 | #ml-ai |

## Próxima Tarea
Delegar la fase APPLY al agente SDD apply con estrategia:
- Modo: interactive
- Store: hybrid
- Delivery strategy: ask-on-risk
- Chain strategy: stacked-to-main
- Prioridad: Phase 1 (Foundation) primero

## Documentos del Proyecto
- PRD_ML.md
- SPEC_ML.md
- RULES.md
- CONTEXT.md
- Task.md

## Búsqueda en Engram
Para detalle de cualquier decisión usar tag: #monitor-v3