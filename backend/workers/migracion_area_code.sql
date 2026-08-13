-- ============================================================
-- MIGRACIÓN: Añadir area_category_code a ASIENTO_PLANTILLA y PRECIO_BOLETO
-- Proyecto Visión — Cinépolis Part II
-- ============================================================

BEGIN;

-- 1. Añadir columna a ASIENTO_PLANTILLA
ALTER TABLE ASIENTO_PLANTILLA
    ADD COLUMN IF NOT EXISTS area_category_code VARCHAR(20);

-- 2. Añadir columna a PRECIO_BOLETO
ALTER TABLE PRECIO_BOLETO
    ADD COLUMN IF NOT EXISTS area_category_code VARCHAR(20);

-- 3. Borrar la restricción única anterior (basada en complejo+formato+tipo_boleto+tipo_sala)
--    y reemplazarla con una que incluya area_category_code para mayor granularidad.
ALTER TABLE PRECIO_BOLETO
    DROP CONSTRAINT IF EXISTS uq_precio_boleto;

ALTER TABLE PRECIO_BOLETO
    ADD CONSTRAINT uq_precio_boleto
    UNIQUE (complejo_id, formato_id, tipo_boleto_id, tipo_sala, area_category_code);

-- 4. Crear índices para acelerar las consultas del Backend
CREATE INDEX IF NOT EXISTS idx_asiento_plantilla_area
    ON ASIENTO_PLANTILLA (sala_id, area_category_code);

CREATE INDEX IF NOT EXISTS idx_precio_boleto_area
    ON PRECIO_BOLETO (complejo_id, area_category_code);

COMMIT;
