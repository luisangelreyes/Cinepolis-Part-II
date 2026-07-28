-- ============================================================
-- ENRIQUECIMIENTO ELENCO TMDB — generado por enriquecer_elenco.py
-- ============================================================

BEGIN;

-- Asegurar que existen las tablas necesarias
CREATE TABLE IF NOT EXISTS PERSONA (
  persona_id SERIAL PRIMARY KEY,
  nombre VARCHAR(200) NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS PELICULA_PERSONA (
  pelicula_id INT REFERENCES PELICULA(pelicula_id),
  persona_id  INT REFERENCES PERSONA(persona_id),
  rol         VARCHAR(50) NOT NULL,
  UNIQUE(pelicula_id, persona_id, rol)
);

COMMIT;