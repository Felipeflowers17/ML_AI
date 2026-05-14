# Tasks: Monitor de Licitaciones - ML_AI

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 2000-3000+ |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 (Foundation) → PR 2 (Core Domain) → PR 3 (Workers) → PR 4 (UI) → PR 5 (CLI/Setup) |
| Delivery strategy | ask-on-risk |
| Chain strategy | stacked-to-main |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Foundation: DB models, connections, repositories | PR 1 | Base branch; includes migrations setup |
| 2 | Core Domain: Scoring motor, pipeline gestor, rules manager | PR 2 | Depends on PR 1; pure domain logic, testable in isolation |
| 3 | Infrastructure Workers: Extraction, scoring, export, piloto | PR 3 | Depends on PR 1, PR 2; QThread implementations |
| 4 | UI Components: Widgets, dialogs, main window | PR 4 | Depends on PR 1, PR 2, PR 3; PySide6 implementation |
| 5 | CLI Scripts & Setup: seed, init-db, migrate | PR 5 | Depends on PR 1; setup and initialization scripts |

## Phase 1: Foundation / Infrastructure

- [ ] 1.1 Create `src/monitor_licitaciones/infrastructure/database/models.py` with SQLAlchemy ORM models (Licitacion, PalabraClave, Organismo, EstadoLicitacion, Configuracion)
- [ ] 1.2 Create `src/monitor_licitaciones/infrastructure/database/connection.py` with session manager (session-per-request strategy)
- [ ] 1.3 Create `src/monitor_licitaciones/infrastructure/database/repositorio_licitaciones.py` implementing RepositorioLicitaciones protocol
- [ ] 1.4 Create `src/monitor_licitaciones/infrastructure/database/repositorio_reglas.py` implementing RepositorioReglas protocol
- [ ] 1.5 Create `src/monitor_licitaciones/infrastructure/database/repositorio_configuracion.py` implementing RepositorioConfiguracion protocol
- [ ] 1.6 Create Alembic migration environment (`alembic/env.py`, `alembic/script.py.mako`)
- [ ] 1.7 Create initial migration (`alembic/versions/001_initial.py`) for all tables and indices
- [ ] 1.8 Create `src/monitor_licitaciones/infrastructure/api/cliente_mp.py` implementing ClienteAPI protocol with Pydantic validation
- [ ] 1.9 Create `src/monitor_licitaciones/config.py` for loading .env variables and global constants
- [ ] 1.10 Create `src/monitor_licitaciones/__init__.py` package files as needed

## Phase 2: Core Domain (Pure Logic, Testable in Isolation)

- [ ] 2.1 Create `src/monitor_licitaciones/domain/scoring/motor_scoring.py` implementing MotorScoring protocol as pure function
- [ ] 2.2 Create `src/monitor_licitaciones/domain/scoring/gestor_reglas.py` with thread-safe rules management using threading.Lock
- [ ] 2.3 Create `src/monitor_licitaciones/domain/pipeline/gestor_pipeline.py` with pipeline stage transition logic
- [ ] 2.4 Create unit tests for motor scoring (tests/test_domain/test_scoring.py) with literal data
- [ ] 2.5 Create unit tests for gestor_reglas thread-safety (tests/test_domain/test_scoring.py) with concurrent reader/writer scenarios
- [ ] 2.6 Create unit tests for pipeline gestor (tests/test_domain/test_pipeline.py) covering stage transitions
- [ ] 2.7 Create `src/monitor_licitaciones/domain/__init__.py` and subpackage init files

## Phase 3: Infrastructure Workers (QThread Implementations)

- [ ] 3.1 Create `src/monitor_licitaciones/workers/extraccion_worker.py` with API calls, UPSERT logic, batch processing, and progress signals
- [ ] 3.2 Create `src/monitor_licitaciones/workers/scoring_worker.py` for recalculating scores in batches with progress reporting
- [ ] 3.3 Create `src/monitor_licitaciones/workers/exportacion_worker.py` for Excel/CSV export with batch processing and progress signals
- [ ] 3.4 Create `src/monitor_licitaciones/workers/piloto_worker.py` with interruptible sleep, retry logic (5/10/20 min), and state persistence
- [ ] 3.5 Create `src/monitor_licitaciones/workers/__init__.py` package file
- [ ] 3.6 Create integration tests for workers (tests/test_workers/test_extraccion.py, test_scoring.py, test_piloto.py) using mocks/spies

## Phase 4: UI Components (PySide6 Implementation)

- [ ] 4.1 Create `src/monitor_licitaciones/ui/widgets/tabla_licitaciones.py` with pagination, sorting, and contextual menu (right-click for stage movement)
- [ ] 4.2 Create `src/monitor_licitaciones/ui/widgets/filtro_busqueda.py` with QLineEdit, debounce timer (300ms), and ILIKE search integration
- [ ] 4.3 Create `src/monitor_licitaciones/ui/widgets/indicadores_pipeline.py` with three QLabels showing counts per stage
- [ ] 4.4 Create `src/monitor_licitaciones/ui/dialogs/config_palabras_clave.py` for managing keywords with weight configuration
- [ ] 4.5 Create `src/monitor_licitaciones/ui/dialogs/config_extraccion.py` for configuring date ranges and extraction options
- [ ] 4.6 Create `src/monitor_licitaciones/ui/dialogs/config_exportacion.py` for format selection and destination path
- [ ] 4.7 Create `src/monitor_licitaciones/ui/dialogs/config_piloto.py` with time selector and ChileCompra recommendation note (22:30 default)
- [ ] 4.8 Create `src/monitor_licitaciones/ui/main_window.py` with tabbed interface (Candidatas, Seguimiento, Ofertadas, Herramientas del Sistema)
- [ ] 4.9 Create `src/monitor_licitaciones/ui/__init__.py` and subpackage init files
- [ ] 4.10 Create UI integration tests (tests/test_ui/) for widget interactions and dialog flows

## Phase 5: Application Entry Point & CLI Scripts

- [ ] 5.1 Create `src/monitor_licitaciones/main.py` with fail-fast validation at startup and app initialization
- [ ] 5.2 Create `src/monitor_licitaciones/cli/migrate.py` script for running Alembic migrations
- [ ] 5.3 Create `src/monitor_licitaciones/cli/init_db.py` script for initializing database
- [ ] 5.4 Create `src/monitor_licitaciones/cli/seed.py` script for loading initial organismos data (from BuscarComprador endpoint or CSV)
- [ ] 5.5 Create `src/monitor_licitaciones/cli/__init__.py` package file
- [ ] 5.6 Create `.env.example` template with required variables (DATABASE_URL, TICKET_MERCADO_PUBLICO)
- [ ] 5.7 Create `pyproject.toml` with all dependencies and groups as specified in design
- [ ] 5.8 Create `alembic.ini` configuration file
- [ ] 5.9 Create `README.md` with setup instructions (5-step process from design)
- [ ] 5.10 Create logging configuration in main.py with Loguru (rotating file sink and console sink)

## Phase 6: Testing & Verification

- [ ] 6.1 Create conftest.py with fixtures for SQLite in-memory database and QApplication
- [ ] 6.2 Create integration tests for repositorios (tests/test_infrastructure/test_repositorio_licitaciones.py, test_repositorio_reglas.py)
- [ ] 6.3 Create integration tests for API client (tests/test_infrastructure/test_cliente_mp.py) using responses library
- [ ] 6.4 Create end-to-end test for extraction → scoring → UI flow (tests/test_e2e/test_flujo_completo.py) with mock server
- [ ] 6.5 Create tests for Pydantic validation of API responses (tests/test_validation/)
- [ ] 6.6 Configure pytest-cov for coverage reporting
