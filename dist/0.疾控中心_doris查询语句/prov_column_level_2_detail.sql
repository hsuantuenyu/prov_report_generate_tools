/*
* 描述：必填字段完整性统计，导出模板《prov_column_level_2_detail.xlsx》
*/
SELECT
    a.city,
    a.org_code,
    a.org_name,
    a.table_code table_name,
    a.table_comment,
    a.column_level,
    case when a.emr_column_level is null then null else '1' end national_flag,
    SUM(a.total_count) total_count,
    SUM(a.noEmpty_count) noEmpty_count,
    AVG(a.noEmpty_rate) noEmpty_rate
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
        n.emr_column_level,
        m.table_column,
        n.field_comment,
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
    INNER JOIN ods_tem_quality_prov_table_mapping n  ON m.table_code = n.table_name AND m.table_column = n.field_name AND (n.column_level='2' or n.emr_column_level='2')
    INNER JOIN (SELECT DISTINCT org_code, org_name, city FROM ods_tem_cdc_v211_org_code_new  WHERE is_516 = '是') a 
        ON a.org_code = m.hospital_code
    WHERE  m.sta_date >= '2026-06-10'
    and  m.sta_date <= '2026-06-11'
) A
INNER JOIN ods_tem_prov_table_list b on b.table_name = a.table_code
WHERE rn = 1
GROUP BY a.city,a.org_code, a.org_name, a.table_code,a.table_comment, a.column_level,a.emr_column_level, a.table_seq
ORDER BY a.city,a.org_code, a.table_seq, a.column_level
LIMIT 25000;