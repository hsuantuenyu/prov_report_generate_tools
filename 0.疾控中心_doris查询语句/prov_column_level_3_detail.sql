/*
* 描述：必填字段完整性统计，导出模板《prov_column_level_3_detail.xlsx》
*/
SELECT
    city,
    org_code,
    org_name,
    table_code as table_name,
    table_comment,
    column_level,
    SUM(total_count) total_count,
    SUM(noEmpty_count) noEmpty_count,
    AVG(noEmpty_rate) noEmpty_rate
FROM (
    SELECT
    a.city,
        a.org_code,
        a.org_name,
        m.hospital_code,
        m.hospital_name,
        m.table_code,
        n.table_comment,
        n.column_level,
        m.table_column,
        m.total_count - m.empty_count AS noEmpty_count,
        m.total_count,
        m.sta_date,
        case when m.total_count = 0 then 0 else 
        1 - m.empty_rate end  AS noEmpty_rate,
        ROW_NUMBER() OVER (
            PARTITION BY m.hospital_code, m.table_code, m.table_column, m.sta_date
            ORDER BY m.__dt DESC
        ) AS rn,
        n.table_seq
    FROM cdc_sta_notnull_result m
    INNER JOIN ods_tem_quality_prov_table_mapping n  ON m.table_code = n.table_name AND m.table_column = n.field_name AND n.emr_column_level='3'
    INNER JOIN (SELECT DISTINCT org_code, org_name, city FROM ods_tem_cdc_v211_org_code_new  WHERE is_516 = '是') a 
        ON a.org_code = m.hospital_code
    WHERE  m.sta_date >= '2026-05-25'
    and  m.sta_date <= '2026-05-25'
) A
WHERE rn = 1
GROUP BY city,org_code, org_name, table_code, table_comment,column_level, table_seq
ORDER BY city,org_code, table_seq, column_level
LIMIT 25000;