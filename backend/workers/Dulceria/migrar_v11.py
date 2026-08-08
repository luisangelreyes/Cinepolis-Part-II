"""
=============================================================================
MIGRACIÓN V11 — Dulcería Incremental
=============================================================================
Ejecutar UNA SOLA VEZ antes de usar sofia_v11_extractor_dulceria.py.

Hace:
  1. Agrega UNIQUE (nombre_categoria)    → CATEGORIA_DULCERIA
  2. Agrega UNIQUE (api_id)              → PRODUCTO_DULCERIA
  3. Agrega UNIQUE (complejo_id)         → CATALOGO_COMPLEJO
  4. Agrega UNIQUE (catalogo_id, producto_id) → DETALLE_CATALOGO
  5. Agrega UNIQUE (api_id_opcion, regla_id)  → MODIFICADOR_OPCION
  6. Agrega columna imagen_url            → MODIFICADOR_OPCION (si no existe)
  7. Crea tabla DISPONIBILIDAD_MODIFICADOR
  8. Crea tabla HISTORIAL_PRECIO_DULCERIA (reemplaza HISTORIAL_PRODUCTO)
=============================================================================
"""

import os
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("❌ DATABASE_URL no encontrada en .env")
    sys.exit(1)

engine = create_engine(DATABASE_URL)

PASOS = [
    # ── Constraints UNIQUE para ON CONFLICT ─────────────────────────────────
    ("UNIQUE nombre_categoria en CATEGORIA_DULCERIA",
     """
     ALTER TABLE CATEGORIA_DULCERIA DROP CONSTRAINT IF EXISTS uq_cat_nombre;
     ALTER TABLE CATEGORIA_DULCERIA ADD CONSTRAINT uq_cat_nombre UNIQUE (nombre_categoria);
     """),

    ("UNIQUE api_id en PRODUCTO_DULCERIA",
     """
     ALTER TABLE PRODUCTO_DULCERIA DROP CONSTRAINT IF EXISTS uq_prod_api_id;
     ALTER TABLE PRODUCTO_DULCERIA ADD CONSTRAINT uq_prod_api_id UNIQUE (api_id);
     """),

    ("UNIQUE complejo_id en CATALOGO_COMPLEJO",
     """
     ALTER TABLE CATALOGO_COMPLEJO DROP CONSTRAINT IF EXISTS uq_catalogo_complejo;
     ALTER TABLE CATALOGO_COMPLEJO ADD CONSTRAINT uq_catalogo_complejo UNIQUE (complejo_id);
     """),

    ("UNIQUE (catalogo_id, producto_id) en DETALLE_CATALOGO",
     """
     ALTER TABLE DETALLE_CATALOGO DROP CONSTRAINT IF EXISTS uq_detalle_cat_prod;
     ALTER TABLE DETALLE_CATALOGO ADD CONSTRAINT uq_detalle_cat_prod UNIQUE (catalogo_id, producto_id);
     """),

    ("UNIQUE (producto_id, titulo_regla, tipo_modificador) en MODIFICADOR_REGLA",
     """
     ALTER TABLE MODIFICADOR_REGLA DROP CONSTRAINT IF EXISTS uq_regla_prod_titulo_tipo;
     ALTER TABLE MODIFICADOR_REGLA ADD CONSTRAINT uq_regla_prod_titulo_tipo UNIQUE (producto_id, titulo_regla, tipo_modificador);
     """),

    ("UNIQUE (regla_id, api_id_opcion) en MODIFICADOR_OPCION",
     """
     ALTER TABLE MODIFICADOR_OPCION DROP CONSTRAINT IF EXISTS uq_opcion_regla_api;
     ALTER TABLE MODIFICADOR_OPCION ADD CONSTRAINT uq_opcion_regla_api UNIQUE (regla_id, api_id_opcion);
     """),

    # ── Columna imagen_url en MODIFICADOR_OPCION ─────────────────────────────
    ("Columna imagen_url en MODIFICADOR_OPCION",
     """
     ALTER TABLE MODIFICADOR_OPCION
     ADD COLUMN IF NOT EXISTS imagen_url TEXT;
     """),

    # ── Nueva tabla DISPONIBILIDAD_MODIFICADOR ───────────────────────────────
    ("Crear tabla DISPONIBILIDAD_MODIFICADOR",
     """
     CREATE TABLE IF NOT EXISTS DISPONIBILIDAD_MODIFICADOR (
         disp_id        SERIAL PRIMARY KEY,
         opcion_id      INT           NOT NULL
                        REFERENCES MODIFICADOR_OPCION(opcion_id) ON DELETE CASCADE,
         catalogo_id    INT           NOT NULL
                        REFERENCES CATALOGO_COMPLEJO(catalogo_id) ON DELETE CASCADE,
         activo         BOOLEAN       NOT NULL DEFAULT TRUE,
         precio_extra   NUMERIC(10,2) NOT NULL DEFAULT 0.00,
         actualizado_en TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
         UNIQUE (opcion_id, catalogo_id)
     );
     CREATE INDEX IF NOT EXISTS idx_disp_mod_catalogo
         ON DISPONIBILIDAD_MODIFICADOR (catalogo_id);
     """),

    # ── Nueva tabla de historial de precios ──────────────────────────────────
    ("Crear tabla HISTORIAL_PRECIO_DULCERIA",
     """
     CREATE TABLE IF NOT EXISTS HISTORIAL_PRECIO_DULCERIA (
         historial_id    SERIAL PRIMARY KEY,
         producto_id     INT           NOT NULL
                         REFERENCES PRODUCTO_DULCERIA(producto_id) ON DELETE CASCADE,
         catalogo_id     INT           NOT NULL
                         REFERENCES CATALOGO_COMPLEJO(catalogo_id) ON DELETE CASCADE,
         precio_anterior NUMERIC(10,2) NOT NULL,
         precio_nuevo    NUMERIC(10,2) NOT NULL,
         registrado_en   TIMESTAMPTZ   NOT NULL DEFAULT NOW()
     );
     """),
]


def migrar():
    print("=" * 65)
    print("  MIGRACIÓN V11 — Dulcería Incremental")
    print("=" * 65)

    with engine.connect() as conn:
        for nombre, sql in PASOS:
            try:
                conn.execute(text(sql))
                conn.commit()
                print(f"  ✅ {nombre}")
            except Exception as e:
                conn.rollback()
                print(f"  ⚠  {nombre}: {e}")

    print("=" * 65)
    print("  Migración completada. Ya puedes correr sofia_v11.")
    print("=" * 65)


if __name__ == "__main__":
    migrar()
