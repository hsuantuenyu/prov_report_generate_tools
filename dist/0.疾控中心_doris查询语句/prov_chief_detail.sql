/**********************************************************
* 主诉、现病史统计，导出模板《prov_chief_detail.xlsx》
************************************************************/
SELECT
      c.city,
      c.org_code,
      c.org_name,
      a.table_code as table_name,
      b.table_comment,
      a.table_column field_name,
      b.field_comment,
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
      ods_tem_quality_prov_table_mapping b,
      ods_tem_cdc_v211_org_code_new c,
      ods_tem_prov_table_list d 
    WHERE
      a.rn = 1
      and a.table_code = b.table_name 
      and a.table_column = b.field_name
      and a.hospital_code = c.org_code
      and a.table_code = d.table_name
      and c.is_516='是'
      AND sta_date >= '2026-06-10'
      AND sta_date <= '2026-06-11'
  group by city,org_code,org_name,a.table_code,b.table_comment,a.table_column,b.field_comment
  order by city,org_code,org_name,a.table_code,a.table_column
limit 20000;