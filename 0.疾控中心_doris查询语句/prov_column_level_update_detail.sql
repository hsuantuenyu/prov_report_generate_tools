 /**********************************************************
 * 描述：必填、条件必填字段完整性统计_更新部分，导出模板《prov_column_level_update_detail.xlsx》 
 ***********************************************************/
select * from (
SELECT
      c.city,
      c.org_code,
      c.org_name,
      a.table_code table_name,
      b.table_comment,
      'update_1' as table_type,
      -- b.column_level,
      case when b.emr_column_level is null then null else '1' end national_flag,
      SUM (a.total_count) total_count,
      SUM (a.noEmpty_count) noEmpty_count,
      avg(a.noEmpty_rate)  noEmpty_rate
    FROM
      (
        select
          hospital_code,
          hospital_name,
          m.table_code,
          m.table_column,
          total_count-empty_count as noEmpty_count,
          total_count,
          sta_date,
          1-empty_rate as noEmpty_rate,
          ROW_NUMBER() OVER (
            PARTITION BY hospital_code,
            m.table_code,
            m.table_column,
            sta_date
            ORDER BY
              __dt DESC
          ) AS rn
        from 
          cdc_sta_notnull_result m,
          ( SELECT table_code, table_column from (
            select 'pro_pt_inspectionreport' as table_code,'ywhdlbdm'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_pt_inspectionreport' as table_code,'ywhdlbmc'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_pt_inspection_ecg' as table_code,'ywhdlbdm'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_pt_inspection_ecg' as table_code,'ywhdlbmc'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_pt_inspection_pathology' as table_code,'ywhdlxdm'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_pt_inspection_pathology' as table_code,'ywhdlxmc'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_base_person_ylfw' as table_code,'head_sexcode'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_base_person_ylfw' as table_code,'head_sexname'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_base_person_ylfw' as table_code,'head_birthday'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_base_person_ylfw' as table_code,'mz'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_base_person_ylfw' as table_code,'mzmc'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_base_person_ylfw' as table_code,'head_address'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_base_person_ylfw' as table_code,'presentaddrprovince'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_base_person_ylfw' as table_code,'presentaddrprovincemc'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_base_person_ylfw' as table_code,'presentaddrcity'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_base_person_ylfw' as table_code,'presentaddrcitymc'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_base_person_ylfw' as table_code,'presentaddrcounty'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_base_person_ylfw' as table_code,'presentaddrcountymc'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_base_person_ylfw' as table_code,'xzzxz'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_base_person_ylfw' as table_code,'xzzxzmc'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_base_person_ylfw' as table_code,'head_contactno'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_base_person_ylfw' as table_code,'gzdwmc'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_opt_diagnosisbreakdown' as table_code,'zs'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_opt_diagnosisbreakdown' as table_code,'xbs'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_opt_diagnosisbreakdown' as table_code,'tgjc'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_opt_diagnosisbreakdown' as table_code,'assistexamresult'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_ipt_diagnosisbreakdown' as table_code,'bzzs'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_ipt_diagnosisbreakdown' as table_code,'xbs'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_ipt_diagnosisbreakdown' as table_code,'tgjc'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_ipt_diagnosisbreakdown' as table_code,'assistexamresult'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_emr_inf_report' as table_code,'gender_code'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_emr_inf_report' as table_code,'gender_name'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_emr_inf_report' as table_code,'nultitude_type_name'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_emr_inf_report' as table_code,'afp_doctor_date'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_opt_emr_doc' as table_code,'clinic_date'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_opt_emr_doc' as table_code,'zs'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_opt_emr_doc' as table_code,'xbs'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_opt_emr_doc' as table_code,'tgjc'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_opt_emr_doc' as table_code,'assistexamresult'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_opt_emr_doc' as table_code,'newly_diagnosed_code'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_opt_observation_doc' as table_code,'zs'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_opt_observation_doc' as table_code,'xbs'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_opt_observation_doc' as table_code,'tgjc'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_opt_observation_doc' as table_code,'assistexamresult'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_ipt_admissionnote' as table_code,'bzzs'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_ipt_admissionnote' as table_code,'bzxbs'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_ipt_admissionnote' as table_code,'temperature'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_ipt_admissionnote' as table_code,'pulse_rate'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_ipt_admissionnote' as table_code,'respiratory_rate'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_ipt_admissionnote' as table_code,'sbp'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_ipt_admissionnote' as table_code,'dbp'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_ipt_admissionnote' as table_code,'height'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_ipt_admissionnote' as table_code,'weight'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_ipt_admissionnote' as table_code,'assist_exam_pathological'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_ipt_admissionnote' as table_code,'assist_exam_test'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_ipt_admissionnote' as table_code,'assist_exam_special'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_ipt_admissionnote' as table_code,'assist_exam_other'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_ipt_admissionnote' as table_code,'pd_west_diag_name'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_ipt_admissionnote' as table_code,'pd_west_diag_code'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_ipt_admissionnote' as table_code,'bqmc'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_ipt_firstpagemedical' as table_code,'admissiondatetime'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_ipt_hospitaldischarger' as table_code,'rysj'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_ipt_hospitaldischarger' as table_code,'zgqk'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_ipt_hospitaldischarger' as table_code,'zgqkmc'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_ipt_hospitaldischarger' as table_code,'ryqk'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_pt_inspectionreport' as table_code,'bckgsj'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_pt_inspectionreport' as table_code,'bczgts'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_pt_inspectionreport' as table_code,'jcbgdh'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_pt_inspectionreport' as table_code,'jcxmdm'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_pt_inspectionreport' as table_code,'jcxmmc'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_pt_inspection_bscan' as table_code,'cssj'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_pt_inspection_bscan' as table_code,'csts'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_pt_inspection_bscan' as table_code,'xmdm'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_pt_inspection_bscan' as table_code,'xmmc'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_pt_inspection_pathology' as table_code,'rysj'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_pt_inspection_pathology' as table_code,'jxsj'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_pt_inspection_pathology' as table_code,'sqksmc'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_pt_inspection_pathology' as table_code,'sqksbm'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_pt_inspection_pathology' as table_code,'xmdm'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_pt_inspection_pathology' as table_code,'xmmc'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_opt_western_recipedetail' as table_code,'prescribe_input_date'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_opt_western_recipedetail' as table_code,'ypgg'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_opt_western_recipedetail' as table_code,'ypggdw'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_opt_western_recipedetail' as table_code,'jl'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_opt_western_recipedetail' as table_code,'dw'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_opt_chinese_recipedetail' as table_code,'prescribe_input_date'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_ipt_advicedetail' as table_code,'ypgg'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_ipt_advicedetail' as table_code,'ypbzggdw'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_ipt_advicedetail' as table_code,'mcsyjl'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_ipt_advicedetail' as table_code,'mcsyjldw'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_base_inspectionreporth' as table_code,'bbcyrqsj'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_base_inspectionreporth' as table_code,'bblb'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_base_inspectionreporth' as table_code,'bblbmc'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_base_inspectionreporth' as table_code,'jsbbrqsj'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_base_inspectionreporth' as table_code,'sqks'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_base_inspectionreporth' as table_code,'sqksmc'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_base_inspectionreporth' as table_code,'exam_apply_organ'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_base_checklist' as table_code,'jldw'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_base_person_ylfw' as table_code,'input_id'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_ipt_recordfirstduration' as table_code,'seniordoctor'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_ipt_recordfirstduration' as table_code,'hospizationdoctor'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_ipt_hospitaldischarger' as table_code,'hospizationdoctor'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_ipt_hospitaldischarger' as table_code,'attending_doctor_sig'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_opt_chinese_recipedetail' as table_code,'kfysgh'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_opt_chinese_recipedetail' as table_code,'cfklysqm'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_opt_western_recipedetail' as table_code,'order_doctor_id'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_opt_western_recipedetail' as table_code,'order_doctor_name'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_pt_deathrecords' as table_code,'hospizationdoctor'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_pt_deathrecords' as table_code,'attendingdoctor'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_ipt_hospitalsignsrecord' as table_code,'ywrybh'as table_column from cdc_sta_effec_result limit 1 union all
            select 'pro_ipt_hospitalsignsrecord' as table_code,'ywryxm'as table_column from cdc_sta_effec_result limit 1 
        ) k
    ) n
        where m.table_code = n.table_code
          and m.table_column = n.table_column
      ) a,
      ods_tem_quality_prov_table_mapping b,
      ods_tem_cdc_v211_org_code_new c 
    WHERE
      a.rn = 1
      and a.table_code = b.table_Name 
      and a.table_column = b.field_name
      and a.hospital_code = c.org_code
      and c.is_516 = '是'
      AND a.sta_date >= '2026-06-10'
      AND a.sta_date <= '2026-06-11'
group by c.city, c.org_code, c.org_name,  a.table_code, b.table_comment,b.column_level,b.emr_column_level
    union all 
    SELECT
      c.city,
      c.org_code,
      c.org_name,
      a.table_code,
      b.table_comment,
      'update_3' as table_type,
      -- b.column_level,
      case when b.emr_column_level is null then null else '1' end national_flag,
      SUM (a.total_count) total_count,
      SUM (a.noEmpty_count) noEmpty_count,
      avg(a.noEmpty_rate)  noEmpty_rate
    FROM
      (
        select
          -- a.org_code,
          -- a.org_name,
          a.hospital_code,
          a.hospital_name,
          m.table_code,
          m.table_column,
          total_count-empty_count as noEmpty_count,
          total_count,
          sta_date,
          1-empty_rate as noEmpty_rate,
          ROW_NUMBER() OVER (
            PARTITION BY hospital_code,
            m.table_code,
            m.table_column,
            sta_date
            ORDER BY
              __dt DESC
          ) AS rn
        from 
          cdc_sta_notnull_result m,
          ( SELECT table_code, table_column from (
             select 'pro_emr_inf_report' as table_code,'nationality_code'as table_column from cdc_sta_effec_result limit 1 union all
             select 'pro_emr_inf_report' as table_code,'nationality_name'as table_column from cdc_sta_effec_result limit 1 union all
             select 'pro_emr_inf_report' as table_code,'nation_code'as table_column from cdc_sta_effec_result limit 1 union all
             select 'pro_emr_inf_report' as table_code,'nation_name'as table_column from cdc_sta_effec_result limit 1 union all
             select 'pro_emr_inf_report' as table_code,'nultitude_type_other'as table_column from cdc_sta_effec_result limit 1 union all
             select 'pro_emr_inf_report' as table_code,'dead_date'as table_column from cdc_sta_effec_result limit 1 union all
             select 'pro_emr_inf_report' as table_code,'foreign_type_code'as table_column from cdc_sta_effec_result limit 1 union all
             select 'pro_emr_inf_report' as table_code,'foreign_type_name'as table_column from cdc_sta_effec_result limit 1 union all
             select 'pro_emr_inf_report' as table_code,'place_code'as table_column from cdc_sta_effec_result limit 1 union all
             select 'pro_emr_inf_report' as table_code,'place_name'as table_column from cdc_sta_effec_result limit 1 
        ) k
        ) n
        where m.table_code = n.table_code
          and m.table_column = n.table_column
      ) a,
      ods_tem_quality_prov_table_mapping b,
      ods_tem_cdc_v211_org_code_new c 
    WHERE
      a.rn = 1
      and a.table_code = b.table_Name 
      and a.table_column = b.field_name
      and a.hospital_code = c.org_code
      and c.is_516 = '是'
      AND sta_date >= '2026-06-10'
      AND sta_date <= '2026-06-11'
group by c.city, c.org_code, c.org_name,  a.table_code, b.table_comment,b.column_level,b.emr_column_level) f 
order by city, org_code
limit 50000;