/***************************************************
* 省标表关联关系统计：导出模板《省标关联关系明细模板.xlsx》
***************************************************/
select
--  'prov_relation_detail' importTableCode,
  a.city,
  a.org_code,
  a.org_name,
  b.main_table_code table_name,
  b.from_table_code association_table_name,
  sum(b.main_count) total_records,
  sum(b.from_count) association_records,
  case when sum(b.main_count) > 0 then (sum(b.from_count) / sum(b.main_count)) end association_rate 
from
  ods_tem_cdc_v211_org_code_new a,
  (
    select
      a.hospital_code,
      a.hospital_name,
      a.sta_date,
      a.main_table_code,
      case when a.main_table_code in ('pro_base_inspectionreporth', 'pro_base_bacterialcultureheader', 'pro_pt_inspectionreport',
       'pro_pt_inspection_bscan', 'pro_pt_inspection_endoscope', 'pro_pt_inspection_ecg', 'pro_pt_inspection_pathology', 'pro_pt_inspection_others')
      and a.from_table_code in (
        'pro_ipt_diagnosisbreakdown','pro_opt_diagnosisbreakdown'
      ) then 'pro_opt_diagnosisbreakdown,pro_ipt_diagnosisbreakdown' else a.from_table_code end as from_table_code,
      case when a.main_table_code in ('pro_base_inspectionreporth', 'pro_base_bacterialcultureheader', 'pro_pt_inspectionreport',
       'pro_pt_inspection_bscan', 'pro_pt_inspection_endoscope', 'pro_pt_inspection_ecg', 'pro_pt_inspection_pathology', 'pro_pt_inspection_others')
      and a.from_table_code in (
        'pro_ipt_diagnosisbreakdown','pro_opt_diagnosisbreakdown'
      ) then max(a.main_count) else a.main_count end as main_count,
      case when a.main_table_code in ( 'pro_base_inspectionreporth', 'pro_base_bacterialcultureheader', 'pro_pt_inspectionreport',
       'pro_pt_inspection_bscan', 'pro_pt_inspection_endoscope', 'pro_pt_inspection_ecg', 'pro_pt_inspection_pathology', 'pro_pt_inspection_others')
      and a.from_table_code in (
        'pro_ipt_diagnosisbreakdown','pro_opt_diagnosisbreakdown') then 
        SUM (
        case when a.from_table_code in ('pro_ipt_diagnosisbreakdown','pro_opt_diagnosisbreakdown') then a.from_count else 0 end
      ) over (partition by a.hospital_code,a.main_table_code,a.sta_date)
       else a.from_count end from_count
    from
      (
        select hospital_code, hospital_name, main_table_code, from_table_code, sta_date, main_count, from_count, rate, sta_time,
          ROW_NUMBER() OVER (
            PARTITION BY hospital_code, main_table_code, from_table_code, sta_date
            ORDER BY __dt DESC
          ) AS rn
        from
          cdc_sta_relevance_result
      ) a
    where
      a.rn = 1
      and a.sta_date >= '2026-05-25'
      and a.sta_date <= '2026-05-25'
    group by a.hospital_code, a.hospital_name, a.sta_date, a.main_table_code, a.from_table_code, a.main_count, a.from_count
  ) b,ods_tem_prov_table_list c 
 where a.org_code = b.hospital_code
 and a.is_516='是'
 and b.main_table_code = c.table_name
 group by a.city, a.org_code, a.org_name, b.main_table_code, b.from_table_code, b.main_count, b.from_count
 order by a.city, a.org_code
 limit 50000