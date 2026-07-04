-- ============================================================
-- CARGA REDUCIDA DEL MCR 3.0 PARA SINAPSIS
-- Solo WordNet español + tablas data/ (ILI, relaciones, lexnames)
-- ============================================================
-- Estas son las únicas tablas que el módulo mcr_baseline.py
-- consulta para calcular CPW y PRS. El resto de lenguas
-- (catalán, inglés, euskera, gallego, portugués) se omiten.
-- ============================================================

-- WordNet Español (las 5 tablas del español)
LOAD DATA LOCAL INFILE '/mcr_files/spaWN/wei_spa-30_examples.tsv' INTO TABLE `wei_spa-30_examples`;
LOAD DATA LOCAL INFILE '/mcr_files/spaWN/wei_spa-30_relation.tsv' INTO TABLE `wei_spa-30_relation`;
LOAD DATA LOCAL INFILE '/mcr_files/spaWN/wei_spa-30_synset.tsv' INTO TABLE `wei_spa-30_synset`;
LOAD DATA LOCAL INFILE '/mcr_files/spaWN/wei_spa-30_to_ili.tsv' INTO TABLE `wei_spa-30_to_ili`;
LOAD DATA LOCAL INFILE '/mcr_files/spaWN/wei_spa-30_variant.tsv' INTO TABLE `wei_spa-30_variant`;

-- Datos generales: ILI, relaciones, grupos de relaciones, lexnames
-- (necesarios para interpretar los tipos de relación y el índice interlingüístico)
LOAD DATA LOCAL INFILE '/mcr_files/data/wei_ili_record.tsv' INTO TABLE `wei_ili_record`;
LOAD DATA LOCAL INFILE '/mcr_files/data/wei_lexnames.tsv' INTO TABLE `wei_lexnames`;
LOAD DATA LOCAL INFILE '/mcr_files/data/wei_relations_group.tsv' INTO TABLE `wei_relations_group`;
LOAD DATA LOCAL INFILE '/mcr_files/data/wei_relations.tsv' INTO TABLE `wei_relations`;
