/**********************************************************
* 主诉、现病史统计，导出模板《省标主诉现病史明细模板.xlsx》
************************************************************/
SELECT
  --  'prov_chief_detail' importTableCode,
      city,
      a.hospital_code,
      a.hospital_name,
      a.table_code,
      a.table_column,
      sum(a.total_count) total_count,
      sum(a.noEmpty_count) noEmpty_count,
      avg(a.noEmpty_rate) noEmpty_rate
    FROM
      (
        select
          m.hospital_code,
          m.hospital_name,
          m.sta_date,
          m.table_code,
          m.table_column,
          m.total_count,
          case when m.total_count =0 then 0 else 
          m.total_count-m.empty_count end noEmpty_count,
          case when m.total_count=0 then 0 else 
          1 - (m.empty_count/m.total_count) end  noEmpty_rate,
          ROW_NUMBER() OVER (
            PARTITION BY m.hospital_code,
            m.hospital_name,
            m.table_code,
            m.table_column,
            m.empty_rate,
            m.sta_time
            ORDER BY
              __dt DESC
          ) AS rn
        from
          cdc_sta_notnull_result m,
          (SELECT k.table_code, k.table_column from (
          select 'pro_opt_diagnosisbreakdown' table_code,'zs' table_column from  cdc_sta_notnull_result limit 1 union all
          select 'pro_opt_diagnosisbreakdown' table_code,'xbs' table_column from  cdc_sta_notnull_result limit 1 union all
          select 'pro_ipt_diagnosisbreakdown' table_code,'bzzs' table_column from  cdc_sta_notnull_result limit 1 union all
          select 'pro_ipt_diagnosisbreakdown' table_code,'xbs' table_column from  cdc_sta_notnull_result limit 1 union all
          select 'pro_ipt_admissionnote' table_code,'bzzs' table_column from  cdc_sta_notnull_result limit 1 union all
          select 'pro_ipt_admissionnote' table_code,'bzxbs' table_column from  cdc_sta_notnull_result limit 1 union all
          select 'pro_opt_emr_doc' table_code,'zs' table_column from  cdc_sta_notnull_result limit 1 union all
          select 'pro_opt_emr_doc' table_code,'xbs' table_column from  cdc_sta_notnull_result limit 1   
          ) k ) n
         where m.table_code = n.table_code and m.table_column = n.table_column
      ) a,
      ods_tem_prov_table_list b,
      ods_tem_cdc_v211_org_code_new c 
    WHERE
      a.rn = 1
      and a.table_code = b.table_name 
      and a.hospital_code = c.org_code
      and c.is_516='是'
      AND sta_date >= '2026-05-25'
      AND sta_date <= '2026-05-25'
  group by city,a.hospital_code,
      a.hospital_name,
      a.table_code,
      a.table_column
      order by city,a.hospital_code,a.hospital_name,a.table_code,a.table_column
limit 20000;