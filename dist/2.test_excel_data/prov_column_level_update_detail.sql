CREATE TABLE prov_table_list (table_seq INTEGER, table_name VARCHAR, table_comment VARCHAR, timeliness_type VARCHAR, timeliness_comment VARCHAR, national_flag INTEGER, pingan_flag INTEGER, early_warning INTEGER, emergency_warning INTEGER, medicine_regulatory INTEGER, quality_flag INTEGER);
COMMENT ON COLUMN prov_table_list.table_seq IS '表序号';
COMMENT ON COLUMN prov_table_list.table_name IS '表名称';
COMMENT ON COLUMN prov_table_list.table_comment IS '表注释';
COMMENT ON COLUMN prov_table_list.timeliness_type IS '时效性类别，0：实时表；1：2小时内；2：T+0';
COMMENT ON COLUMN prov_table_list.timeliness_comment IS '时效性注释';
COMMENT ON COLUMN prov_table_list.national_flag IS '国标表标志';
COMMENT ON COLUMN prov_table_list.pingan_flag IS '平安表标志';
COMMENT ON COLUMN prov_table_list.early_warning IS '预警处标志';
COMMENT ON COLUMN prov_table_list.emergency_warning IS '应急处标志';
COMMENT ON COLUMN prov_table_list.medicine_regulatory IS '药政处标志';


INSERT INTO prov_table_list (table_seq, table_name, table_comment, timeliness_type, timeliness_comment, national_flag, pingan_flag, early_warning, emergency_warning, medicine_regulatory, quality_flag) VALUES 
(1, 'pro_base_person_ylfw', '患者基本信息', '0', '≤ 150秒', 1, 1, 1, 0, 0, 1),
(2, 'pro_emr_inf_report', '传染病报告卡', '0', '≤ 150秒', 1, 1, 1, 0, 0, 1),
(3, 'pro_opt_diagnosisbreakdown', '门急诊诊断明细', '0', '≤ 150秒', 1, 1, 1, 1, 0, 1),
(4, 'pro_ipt_diagnosisbreakdown', '在院诊断明细', '0', '≤ 150秒', 1, 1, 1, 1, 0, 1),
(5, 'pro_base_inspectionreporth', '检验记录', '1', '≤ 90分钟', 1, 1, 1, 0, 0, 1),
(6, 'pro_base_checklist', '检验明细信息', '1', '≤ 90分钟', 1, 1, 1, 0, 0, 1),
(7, 'pro_base_bacterialcultureheader', '细菌培养记录', '1', '≤ 90分钟', 0, 0, 0, 0, 0, 0),
(8, 'pro_opt_emr_doc', '门急诊病历', '2', '≤ 23小时', 1, 0, 1, 0, 0, 1),
(9, 'pro_opt_observation_doc', '急诊留观病历', '2', '≤ 23小时', 1, 1, 1, 0, 0, 1),
(10, 'pro_opt_record', '门急诊就诊记录', '2', '≤ 23小时', 0, 1, 1, 1, 0, 1),
(11, 'pro_opt_western_recipedetail', '门急诊西药处方明细', '2', '≤ 23小时', 1, 1, 1, 1, 0, 1),
(12, 'pro_opt_chinese_recipedetail', '门急诊中药处方明细', '2', '≤ 23小时', 1, 0, 1, 1, 0, 1),
(13, 'pro_opt_handledetail', '门急诊开单项目明细', '2', '≤ 23小时', 0, 0, 0, 1, 0, 0),
(14, 'pro_opt_handledetail_exe', '门急诊医嘱执行记录', '2', '≤ 23小时', 0, 0, 0, 1, 0, 0),
(15, 'pro_opt_fee', '门急诊收费信息', '2', '≤ 23小时', 0, 0, 0, 1, 0, 0),
(16, 'pro_opt_feedetail', '门急诊收费明细', '2', '≤ 23小时', 0, 0, 0, 1, 1, 0),
(17, 'pro_ipt_record', '入院登记表', '2', '≤ 23小时', 0, 1, 1, 1, 0, 1),
(18, 'pro_ipt_dis_reg', '出/退院登记', '2', '≤ 23小时', 0, 0, 0, 1, 0, 0),
(19, 'pro_ipt_firstpagemedical', '西医住院病案首页', '2', '≤ 23小时', 1, 0, 1, 0, 0, 1),
(20, 'pro_ipt_firstpagemedical_dia', '西医住院病案首页_诊断信息', '2', '≤ 23小时', 1, 0, 1, 0, 0, 1),
(21, 'pro_ipt_admissionnote', '入院记录', '2', '≤ 23小时', 1, 0, 1, 0, 0, 1),
(22, 'pro_ipt_recordfirstduration', '首次病程记录', '2', '≤ 23小时', 1, 1, 1, 0, 0, 1),
(23, 'pro_ipt_dailycourser', '日常病程记录', '2', '≤ 23小时', 1, 1, 1, 0, 0, 1),
(24, 'pro_ipt_hospitaldischarger', '出院记录', '2', '≤ 23小时', 1, 1, 1, 1, 0, 1),
(25, 'pro_pt_deathrecords', '死亡记录', '2', '≤ 23小时', 1, 1, 1, 0, 0, 1),
(26, 'pro_ipt_advicedetail', '住院医嘱', '2', '≤ 23小时', 1, 1, 1, 1, 0, 1),
(27, 'pro_ipt_advicedetail_exe', '住院医嘱执行记录', '2', '≤ 23小时', 0, 0, 0, 1, 0, 0),
(28, 'pro_ipt_hospitalsignsrecord', '生命体征测量记录', '2', '≤ 23小时', 1, 1, 1, 0, 0, 1),
(29, 'pro_ipt_hospitalsettlement', '在院出院结算表', '2', '≤ 23小时', 0, 0, 0, 1, 0, 0),
(30, 'pro_ipt_hospitalchargesd', '住院收费明细', '2', '≤ 23小时', 0, 0, 0, 1, 1, 0),
(31, 'pro_pt_inspectionreport', '放射影像检查报告信息', '2', '≤ 23小时', 1, 1, 1, 0, 0, 1),
(32, 'pro_pt_inspection_bscan', 'B超报告单详细信息', '2', '≤ 23小时', 1, 0, 1, 0, 0, 1),
(33, 'pro_pt_inspection_endoscope', '内镜报告单详细信息', '2', '≤ 23小时', 0, 0, 0, 1, 0, 0),
(34, 'pro_pt_inspection_ecg', '心电报告单详细信息', '2', '≤ 23小时', 0, 0, 0, 1, 0, 0),
(35, 'pro_pt_inspection_pathology', '病理报告单详细信息', '2', '≤ 23小时', 1, 0, 1, 0, 0, 1),
(36, 'pro_pt_operation', '手术操作记录', '2', '≤ 23小时', 0, 0, 0, 1, 0, 0),
(37, 'pro_public_ware', '药品入库信息表', '2', '≤ 23小时', 0, 0, 0, 0, 1, 0),
(38, 'pro_public_out', '药品出库信息表', '2', '≤ 23小时', 0, 0, 0, 0, 1, 0),
(39, 'pro_dic_department', '科室字典表', '2', '≤ 23小时', 1, 0, 1, 1, 0, 1),
(40, 'pro_dic_practitioner', '医护人员信息表', '2', '≤ 23小时', 1, 0, 1, 1, 0, 1),
(41, 'pro_dic_drug_detail', '药品字典表', '2', '≤ 23小时', 0, 0, 0, 0, 1, 0);
