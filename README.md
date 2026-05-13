# Monitor de Licitaciones — ML_AI

Aplicación de escritorio para monitorear licitaciones públicas de
[Mercado Público Chile](https://www.mercadopublico.cl) con scoring
automático basado en reglas configurables.

---

## Setup (5 pasos)

### 1. Configurar entorno

```bash
cp .env.example .env
```

Editar `.env` con los valores correctos:

| Variable | Descripción |
|----------|-------------|
| `DATABASE_URL` | Conexión a PostgreSQL (`postgresql://usuario:contraseña@host:5432/bd`) |
| `TICKET_MERCADO_PUBLICO` | Token de API obtenido en https://api.mercadopublico.cl |

### 2. Instalar dependencias

```bash
poetry install
```

### 3. Inicializar base de datos

```bash
poetry run init-db
```

Verifica la conexión a PostgreSQL y crea todas las tablas vía Alembic.

### 4. Cargar organismos

```bash
poetry run seed
```

Descarga el catálogo de organismos desde la API. Si la API no está disponible,
intenta cargar desde `organismos.csv` (ver formato abajo).

### 5. Iniciar la aplicación

```bash
poetry run gui
```

---

## Troubleshooting

| Error | Causa probable | Solución |
|-------|----------------|----------|
| `DATABASE_URL no configurada` | Falta la variable en `.env` | Editar `.env` y agregar `DATABASE_URL` |
| `No se pudo conectar a PostgreSQL` | PostgreSQL no está corriendo | Iniciar PostgreSQL o verificar host/puerto en `DATABASE_URL` |
| `TICKET_MERCADO_PUBLICO no configurada` | Falta el ticket en `.env` | Obtener ticket en https://api.mercadopublico.cl |
| Error al cargar organismos | Sin ticket ni `organismos.csv` | Ver paso 4 — crear `organismos.csv` como fallback |

### Formato de `organismos.csv`

```csv
codigo,nombre
CH-123,Municipalidad de Santiago
CH-456,Gobierno Regional Metropolitano
```

---

## Comandos CLI

| Comando | Descripción |
|---------|-------------|
| `poetry run gui` | Inicia la interfaz gráfica |
| `poetry run init-db` | Inicializa la BD (verifica conexión + migra) |
| `poetry run migrate` | Aplica migraciones pendientes (sin verificar conexión) |
| `poetry run seed` | Carga catálogo de organismos |

---

## Tests

```bash
pytest
```

Los tests unitarios y de integración usan SQLite in-memory.
Los tests E2E requieren PostgreSQL (no incluidos por defecto).

---

## Stack

- **Python** 3.13+
- **PySide6** — UI
- **SQLAlchemy 2.0** — ORM
- **PostgreSQL** — Base de datos
- **Alembic** — Migraciones
- **Loguru** — Logging
- **Pydantic** — Validación de API
- **Poetry** — Gestión de dependencias
