-- 
truncate table prov_timeliness_org;
insert into prov_timeliness_org
select b.city,
       b.org_code,
       b.org_name,
       b.table_level,
       sum(b.total_records)       total_records,
       sum(b.compliance_records) compliance_records,
       case
           when sum(b.total_records) > 0 then
               round((sum(b.compliance_records) / sum(b.total_records)) * 100, 2)
           end                   compliance_rate
from prov_timeliness_detail b,prov_table_list c 
where b.table_name = c.table_name 
and c.national_flag ='1'
group by b.city,
         b.org_code,
         b.org_name,
         b.table_level
order by b.city, b.org_code,b.table_level;

-- 
truncate table prov_association_org;
-- 关联关系
-- create table qzrj_association_org as
insert into prov_association_org
select a.city,
a.org_code,
       a.org_name,
       'all' association_table,
       sum(a.total_records) total_records,
       sum(a.association_records) association_records,
       case when sum(a.total_records) >0 then
           round((sum(a.association_records)/sum(a.total_records))*100,2)
       end association_rate
       from prov_association_detail a,prov_table_list b 
where a.table_name = b.table_name 
and b.national_flag ='1'
and a.association_table_name in('pro_base_person_ylfw','pro_opt_diagnosisbreakdown,pro_ipt_diagnosisbreakdown')
group by a.city, a.org_code, a.org_name
order by a.city,a.org_code;

-- 患者基本信息
insert into prov_association_org
select a.city,a.org_code,
       a.org_name,
       a.association_table_name as association_table,
       sum(a.total_records) total_records,
       sum(a.association_records) association_records,
       case when sum(a.total_records) >0 then
           round((sum(a.association_records)/sum(a.total_records))*100,2)
       end association_rate
       from prov_association_detail a,prov_table_list b 
where a.table_name = b.table_name 
and b.national_flag ='1'
and a.association_table_name='pro_base_person_ylfw'
group by a.city, a.org_code, a.org_name,a.association_table_name
order by a.city,a.org_code;

-- 关联门急诊诊断和在院诊断
insert into prov_association_org
select a.city,a.org_code,
       a.org_name,
       a.association_table_name as association_table,
       sum(a.total_records) total_records,
       sum(a.association_records) association_records,
       case when sum(a.total_records) >0 then
           round((sum(a.association_records)/sum(a.total_records))*100,2)
       end association_rate
       from prov_association_detail a,prov_table_list b 
where a.table_name = b.table_name 
and b.national_flag ='1'
and a.association_table_name='pro_opt_diagnosisbreakdown,pro_ipt_diagnosisbreakdown'
group by a.city, a.org_code, a.org_name,a.association_table_name
order by a.city,a.org_code;

-- 主诉
insert into prov_chief_org 
select a.city,
               a.org_code,
               a.org_name,
               sum(a.total_records)   total_records,
               sum(a.notnull_records) notnull_records,
               case
                   when sum(a.total_records) > 0 then
                       round((sum(a.notnull_records) / sum(a.total_records)) ,4)
                   end              notnull_rate
        from prov_chief_detail a,prov_table_list b 
    where a.table_name = b.table_name 
    and b.national_flag ='1'
    and a.field_name in ('bzzs', 'chiefcomplaint', 'zs')
        group by a.city, a.org_code, a.org_name
        order by a.city, a.org_code;
        
-- 现病史        
insert into prov_illness_org 
select a.city,
               a.org_code,
               a.org_name,
               sum(a.total_records)   total_records,
               sum(a.notnull_records) notnull_records,
               case
                   when sum(a.total_records) > 0 then
                       round((sum(a.notnull_records) / sum(a.total_records)) ,4)
                   end              notnull_rate
        from prov_chief_detail a,prov_table_list b 
    where a.table_name = b.table_name 
    and b.national_flag ='1'
    and  a.field_name in ('bzxbs', 'xbs')
        group by a.city, a.org_code, a.org_name
        order by a.city, a.org_code;       
        
-- 必填字段 
truncate table prov_column_level_org;
-- 字段完整性
-- create table qzrj_column_level_org as
insert into prov_column_level_org
select a.city,
       a.org_code,
       a.org_name,
       '1' column_level,
       sum(a.total_records)                                                        total_records,
       sum(a.notnull_records)                                                      notnull_records,
       case
           when sum(a.total_records) > 0 then
               round((sum(a.notnull_records) / sum(a.total_records)) * 100, 2) end notnull_rate
from prov_column_level_1_detail a,prov_table_list b 
    where a.table_name = b.table_name 
    and b.national_flag ='1'
group by a.city, a.org_code, a.org_name
order by a.city, a.org_code;       

-- 重要字段建议填
insert into prov_column_level_org
select a.city,
       a.org_code,
       a.org_name,
       '2' column_level,
       sum(a.total_records)                                                        total_records,
       sum(a.notnull_records)                                                      notnull_records,
       case
           when sum(a.total_records) > 0 then
               round((sum(a.notnull_records) / sum(a.total_records)) * 100, 2) end notnull_rate
from prov_column_level_2_detail a,prov_table_list b 
    where a.table_name = b.table_name 
    and b.national_flag ='1'
group by a.city, a.org_code, a.org_name
order by a.city, a.org_code;  

-- 条件必填
insert into prov_column_level_org
select a.city,
       a.org_code,
       a.org_name,
       '3' column_level,
       sum(a.total_records)                                                        total_records,
       sum(a.notnull_records)                                                      notnull_records,
       case
           when sum(a.total_records) > 0 then
               round((sum(a.notnull_records) / sum(a.total_records)) * 100, 2) end notnull_rate
from prov_column_level_3_detail a,prov_table_list b 
    where a.table_name = b.table_name 
    and b.national_flag ='1'
group by a.city, a.org_code, a.org_name
order by a.city, a.org_code;  


insert into prov_column_level_org
select a.city,
       a.org_code,
       a.org_name,
       a.column_level,
       sum(a.total_records)                                                        total_records,
       sum(a.notnull_records)                                                      notnull_records,
       case
           when sum(a.total_records) > 0 then
               round((sum(a.notnull_records) / sum(a.total_records)) * 100, 2) end notnull_rate
from prov_column_level_update_detail a,prov_table_list b 
    where a.table_name = b.table_name 
    and b.national_flag ='1'
group by a.city, a.org_code, a.org_name,a.column_level
order by a.city, a.org_code,a.column_level;  

-- 机构汇总结果生成
truncate table prov_city_summary;

insert into prov_city_summary
select a.city,
       count(a.org_code) org_cnt,
       sum(case when b.compliance_rate >=90 then 1 else 0 end) real_cnt,
       sum(case when c.compliance_rate >=100 then 1 else 0 end ) hour_cnt,
       sum(case when d.compliance_rate >=100 then 1 else 0 end) other_cnt,
       sum(e.total_records) e_total_records,
       sum(e.notnull_records) e_notnull_records,
       sum(f.total_records) f_total_records,
       sum(f.notnull_records) f_notnull_records,
       sum(g.total_records) g_total_records,
       sum(g.notnull_records) g_notnull_records,
       sum(h.total_records) h_total_records,
       sum(h.notnull_records) h_notnull_records,
       sum(i.total_records) i_total_records,
       sum(i.notnull_records) i_notnull_records,
       sum(case when j.association_rate >=100 then 1 else 0 end) association_org_cnt
from org_list a
 left join prov_timeliness_org b on b.org_code = a.org_code and b.table_level = '1'
         left join prov_timeliness_org c on c.org_code = a.org_code and c.table_level = '2'
         left join prov_timeliness_org d on d.org_code = a.org_code and d.table_level = '3'
         left join prov_column_level_org e on e.org_code = a.org_code and e.column_level = '1'
         left join prov_column_level_org f on f.org_code = a.org_code and f.column_level = '2'
         left join prov_column_level_org g on g.org_code = a.org_code and g.column_level = '3'
         left join prov_column_level_org h on h.org_code = a.org_code and h.column_level = 'update_1'
         left join prov_column_level_org i on i.org_code = a.org_code and i.column_level = 'update_3'
         left join prov_association_org j on j.org_code = a.org_code and j.association_table = 'all'
   where a.is_516_flag = '是'
group by a.city;