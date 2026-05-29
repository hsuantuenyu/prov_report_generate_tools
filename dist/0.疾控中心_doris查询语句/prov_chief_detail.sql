/****************************************************
* 表时效性统计脚本：对应导出模板 prov_timeliness_detail
****************************************************/
SELECT
  b.city,
  b.org_code,
  b.org_name,
  a.table_code,
  c.table_comment,
  c.table_level,
  SUM(a.total_count) AS total_records,
  SUM(a.compliance_records) AS compliance_records,
  IF(
    SUM(a.total_count) > 0,
    SUM(a.compliance_records) / SUM(a.total_count),
    NULL
  ) AS compliance_rate,
  case c.table_level when '1' then '1' end table_flag
FROM
  (
    SELECT
      hospital_code,
      hospital_name,
      sta_date,
      table_code,
      total_count,
      refer_time,
      IF(total_count = 0, 0, total_count - sta_count) AS compliance_records,
      FROM_UNIXTIME(sta_time / 1000) AS sta_time,
      ROW_NUMBER() OVER (
        PARTITION BY hospital_code,
        hospital_name,
        sta_date,
        table_code,
        sta_time
        ORDER BY
          __dt DESC
      ) AS rn
    FROM
      cdc_sta_effec_result
  ) a
  INNER JOIN ods_tem_cdc_v211_org_code_new b on a.hospital_code = b.org_code and b.is_516 = '是'
  INNER JOIN ods_tem_prov_table_list c on c.table_name = a.table_code and c.quality_flag ='1'
WHERE
  a.rn = 1
  AND a.sta_date >= '2026-05-25'
  AND a.sta_date <= '2026-05-25'
GROUP BY b.city,b.org_code,b.org_name,a.table_code,c.table_comment,c.table_level
  order by b.city,b.org_code 
LIMIT 50000;