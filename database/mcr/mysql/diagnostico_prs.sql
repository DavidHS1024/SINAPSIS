-- ============================================================
-- DIAGNÓSTICO DEL PRS ANÓMALO
-- Ejecutar estas consultas para confirmar la causa del inflado.
-- ============================================================

-- CONSULTA 1: ¿Cuántas relaciones tiene un synset típico?
-- Si da números enormes (>50), hay duplicación por method/version/wnSource.
SELECT '--- Q1: Relaciones por synset (muestra) ---' AS diagnostico;
SELECT sourceSynset, sourcePos, COUNT(*) AS num_relaciones
FROM `wei_spa-30_relation`
GROUP BY sourceSynset, sourcePos
ORDER BY num_relaciones DESC
LIMIT 10;

-- CONSULTA 2: ¿Hay relaciones duplicadas por los campos method/version/wnSource?
-- Compara el total de filas vs relaciones únicas (sin method/version/wnSource).
SELECT '--- Q2: Total filas vs relaciones unicas ---' AS diagnostico;
SELECT
    COUNT(*) AS total_filas,
    COUNT(DISTINCT relation, sourceSynset, sourcePos, targetSynset, targetPos) AS relaciones_unicas
FROM `wei_spa-30_relation`;

-- CONSULTA 3: ¿Qué valores tiene wnSource? (para ver si hay multiples fuentes)
SELECT '--- Q3: Distribucion por wnSource ---' AS diagnostico;
SELECT wnSource, COUNT(*) AS cantidad
FROM `wei_spa-30_relation`
GROUP BY wnSource
ORDER BY cantidad DESC;

-- CONSULTA 4: ¿Cuántos sentidos (synsets) tiene un peruanismo polisémico?
-- Ejemplo con palabras comunes que seguro están en el MCR.
SELECT '--- Q4: Polisemia de palabras comunes ---' AS diagnostico;
SELECT word, COUNT(DISTINCT offset, pos) AS num_synsets
FROM `wei_spa-30_variant`
WHERE word IN ('casa', 'palta', 'chacra', 'pata', 'cancha')
GROUP BY word;

-- CONSULTA 5: Verificar un caso concreto — relaciones de 'casa'
SELECT '--- Q5: Relaciones totales de un synset de casa ---' AS diagnostico;
SELECT v.word, v.offset, v.pos,
    (SELECT COUNT(*) FROM `wei_spa-30_relation` r
     WHERE (r.sourceSynset=v.offset AND r.sourcePos=v.pos)
        OR (r.targetSynset=v.offset AND r.targetPos=v.pos)) AS rels_con_duplicados,
    (SELECT COUNT(DISTINCT relation, 
        CASE WHEN r.sourceSynset=v.offset THEN r.targetSynset ELSE r.sourceSynset END)
     FROM `wei_spa-30_relation` r
     WHERE (r.sourceSynset=v.offset AND r.sourcePos=v.pos)
        OR (r.targetSynset=v.offset AND r.targetPos=v.pos)) AS rels_unicas
FROM `wei_spa-30_variant` v
WHERE v.word = 'casa'
LIMIT 5;
