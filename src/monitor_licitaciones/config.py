"""Constantes globales del proyecto.

Responsabilidad única: valores fijos y nombres de claves de configuración.
No contiene lógica de negocio.
"""

# ── Etapas del pipeline ────────────────────────────────────────────────
ETAPA_CANDIDATA = "candidata"
ETAPA_SEGUIMIENTO = "seguimiento"
ETAPA_OFERTADA = "ofertada"
ETAPA_IGNORADA = "ignorada"
ETAPAS_ACTIVAS = [ETAPA_CANDIDATA, ETAPA_SEGUIMIENTO, ETAPA_OFERTADA]

# ── Estado Publicada en API de Mercado Público ─────────────────────────
CODIGO_ESTADO_PUBLICADA = 5

# ── Paginación ─────────────────────────────────────────────────────────
TAMANIO_PAGINA = 50

# ── Claves de configuración del piloto automático ──────────────────────
PILOTO_ACTIVO = "piloto_activo"
PILOTO_HORA = "piloto_hora"
PILOTO_HORA_DEFAULT = "22:30"
PILOTO_ULTIMA_EJECUCION = "piloto_ultima_ejecucion"
PILOTO_ULTIMO_ERROR = "piloto_ultimo_error"

# ── API de Mercado Público ─────────────────────────────────────────────
API_PAUSA_SEGUNDOS = 2.0
API_MAX_INTENTOS = 3
API_BASE_RETRASO = 1.5
API_TIMEOUT_SEGUNDOS = 15

# ── Exportación ────────────────────────────────────────────────────────
EXPORT_CHUNK_SIZE = 1000
