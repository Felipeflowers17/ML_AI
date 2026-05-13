"""Initial migration: create all tables.

Revision ID: 001
Revises:
Create Date: 2026-05-12
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- organismos ---
    op.create_table(
        "organismos",
        sa.Column("codigo", sa.String(), nullable=False),
        sa.Column("nombre", sa.String(200), nullable=False),
        sa.Column("puntaje_fijo", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.PrimaryKeyConstraint("codigo"),
    )
    op.create_index("idx_organismo_codigo", "organismos", ["codigo"])

    # --- estados_licitacion ---
    op.create_table(
        "estados_licitacion",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("codigo", sa.Integer(), nullable=False),
        sa.Column("descripcion", sa.String(100), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("codigo"),
    )

    # --- licitaciones ---
    op.create_table(
        "licitaciones",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("codigo_externo", sa.String(50), nullable=False),
        sa.Column("nombre", sa.String(500), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("detalle_productos", sa.Text(), nullable=True),
        sa.Column("fecha_publicacion", sa.DateTime(), nullable=True),
        sa.Column("fecha_cierre", sa.DateTime(), nullable=True),
        sa.Column("fecha_inicio", sa.DateTime(), nullable=True),
        sa.Column("fecha_adjudicacion", sa.DateTime(), nullable=True),
        sa.Column("codigo_organismo", sa.String(), nullable=True),
        sa.Column("codigo_estado", sa.Integer(), nullable=True),
        sa.Column("score_resumen", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("score_detalle", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("score_total", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("etapa", sa.String(), nullable=False, server_default=sa.text("'ignorada'")),
        sa.Column("justificacion_score", sa.Text(), nullable=True),
        sa.Column("tiene_detalle", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("fecha_extraccion", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("fecha_actualizacion", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["codigo_organismo"], ["organismos.codigo"], ),
        sa.ForeignKeyConstraint(["codigo_estado"], ["estados_licitacion.codigo"], ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_licitacion_codigo_externo", "licitaciones", ["codigo_externo"], unique=True)
    op.create_index("idx_licitacion_etapa", "licitaciones", ["etapa"])
    op.create_index("idx_licitacion_score_total", "licitaciones", ["score_total"])

    # --- palabras_clave ---
    op.create_table(
        "palabras_clave",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("termino", sa.String(100), nullable=False),
        sa.Column("categoria", sa.String(100), nullable=True),
        sa.Column("peso_titulo", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("peso_descripcion", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("peso_productos", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("activa", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_palabra_clave_termino", "palabras_clave", ["termino"])

    # --- configuracion ---
    op.create_table(
        "configuracion",
        sa.Column("clave", sa.String(50), nullable=False),
        sa.Column("valor", sa.Text(), nullable=True),
        sa.Column("fecha_actualizacion", sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("clave"),
    )


def downgrade() -> None:
    op.drop_table("configuracion")
    op.drop_table("palabras_clave")
    op.drop_index("idx_licitacion_score_total", table_name="licitaciones")
    op.drop_index("idx_licitacion_etapa", table_name="licitaciones")
    op.drop_index("idx_licitacion_codigo_externo", table_name="licitaciones")
    op.drop_table("licitaciones")
    op.drop_table("estados_licitacion")
    op.drop_index("idx_organismo_codigo", table_name="organismos")
    op.drop_table("organismos")
