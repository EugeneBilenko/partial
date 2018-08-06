LIST_TRAIT_MATCHES = """
        SELECT
          tm.id           AS id,
          tm.count        AS count,
          tm.score        AS score,
          tm.name         AS name,
          tm.m_count      AS m_count,
          (
            SELECT DISTINCT
              array_agg('[' || genome_userrsid.genotype || ',' || genome_snp.rsid || ',' || (CASE WHEN genome_snp.minor_allele IS NULL THEN '' ELSE genome_snp.minor_allele END) || ',' || genome_snp.id || ']')
            FROM aggregate_conclusions_snpmatches AS sm
              JOIN genome_snp ON (sm.snp_id = genome_snp.id)
              FULL OUTER JOIN genome_userrsid ON (sm.user_snp_id = genome_userrsid.id)
            WHERE sm.trait_id = tm.id
          )               AS snps,
          (
            SELECT AVG(GREATEST(gp.homozygous_minor_freq, gp.homozygous_major_freq, gp.heterozygous_freq))
            FROM genome_populationgenome AS gp
            WHERE gp.snp_id
                  IN (
                    SELECT aggregate_conclusions_snpmatches.snp_id
                    FROM aggregate_conclusions_snpmatches
                    WHERE aggregate_conclusions_snpmatches.trait_id = tm.id
                  ) AND gp.abbr = '{1}'
          )               AS avg_score
        FROM
          aggregate_conclusions_traitmatches AS tm
        WHERE
          tm.file_id = {0} AND tm.m_count >= {4} AND tm.score > {5} AND tm.score <= {6} {7}
        ORDER BY
          score DESC,
          tm.p_term DESC
        LIMIT {2}
        OFFSET {3}
        """