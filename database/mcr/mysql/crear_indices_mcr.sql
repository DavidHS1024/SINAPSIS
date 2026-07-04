-- ============================================================
-- ÍNDICES PARA ACELERAR LAS CONSULTAS DE SINAPSIS
-- ============================================================
-- El MCR viene SIN índices en las columnas que consultamos.
-- Sin ellos, cada búsqueda escanea la tabla completa.
-- Crear estos índices reduce el tiempo de horas a segundos.
-- Ejecutar UNA SOLA VEZ. Tarda ~1-2 min en crearlos.
-- ============================================================

-- Índice para buscar lemas por palabra (acelera Fase 1)
CREATE INDEX idx_variant_word
    ON `wei_spa-30_variant` (word);

-- Índice compuesto para buscar synset por (offset, pos) en variant
CREATE INDEX idx_variant_offset_pos
    ON `wei_spa-30_variant` (offset, pos);

-- Índices para contar relaciones por synset origen (acelera Fase 1 y 2)
CREATE INDEX idx_relation_source
    ON `wei_spa-30_relation` (sourceSynset, sourcePos);

-- Índices para contar relaciones por synset destino (acelera Fase 1 y 2)
CREATE INDEX idx_relation_target
    ON `wei_spa-30_relation` (targetSynset, targetPos);

-- Verificar que se crearon
SHOW INDEX FROM `wei_spa-30_variant`;
SHOW INDEX FROM `wei_spa-30_relation`;
