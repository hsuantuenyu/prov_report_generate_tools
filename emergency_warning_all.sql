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
where b.table_name = c.table_name and c.enable_status = '1'
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
SELECT t.city,
       t.org_code,
       t.org_name,
       'all'                                                     AS association_table,
       COUNT(CASE WHEN t.total_records > 0 THEN 1 END)           AS total_records,
       SUM(CASE WHEN t.association_rate >= 90 THEN 1 ELSE 0 END) AS association_records,
       ROUND(
         SUM(CASE WHEN t.association_rate >= 90 THEN 1 ELSE 0 END ) * 100.0 / NULLIF(
           COUNT(CASE WHEN t.total_records > 0 THEN 1  END ), 0 )
           , 2) AS association_rate
FROM (SELECT a.city,
             a.org_code, a.org_name,
             a.table_name,
             a.association_table_name,
             SUM(a.total_records)       AS total_records,
             SUM(a.association_records) AS association_records,
             CASE
               WHEN SUM(a.total_records) > 0 THEN ROUND((SUM(a.association_records) / SUM(a.total_records)) * 100, 2)
               ELSE NULL
             END AS association_rate
      FROM prov_association_detail a
        LEFT JOIN prov_table_list b ON a.table_name = b.table_name and b.enable_status = '1'
        --JOIN emergency_association_config c ON a.table_name = c.table_name and a.association_table_name = c.association_table_name
      GROUP BY a.city, a.org_code, a.org_name, a.table_name, a.association_table_name) t
GROUP BY t.city, t.org_code, t.org_name 
order by t.city,t.org_code;

-- 明细、主单关联率
insert into prov_association_org
select city,org_code,org_name,'master' as association_table,
sum(t.total_records) as total_records,
sum(t.association_records) as association_records,
case when sum(t.total_records) > 0 then
    round((sum(t.association_records) / sum(t.total_records)) * 100, 2)
end association_rate
from (
select a.city,a.org_code,
       a.org_name,
       concat(a.table_name,',',a.association_table_name) as association_table,
       sum(a.total_records) total_records,
       sum(a.association_records) association_records
       from prov_association_detail a,prov_table_list b
where a.table_name = b.table_name and b.enable_status = '1'
and exists (select 1 from emergency_association_config c where a.table_name = c.table_name
and a.association_table_name = c.association_table_name
and c.association_type = '3')
group by a.city, a.org_code, a.org_name,a.table_name,a.association_table_name) t
group by t.city,t.org_code,t.org_name
order by t.city,t.org_code;

-- 关联门急诊诊断和在院诊断
insert into prov_association_org
select city,org_code,org_name,'other' as association_table,
sum(t.total_records) as total_records,
sum(t.association_records) as association_records,
case when sum(t.total_records) > 0 then
    round((sum(t.association_records) / sum(t.total_records)) * 100, 2)
end association_rate
from (
select a.city,a.org_code,
       a.org_name,
       concat(a.table_name,',',a.association_table_name) as association_table,
       sum(a.total_records) total_records,
       sum(a.association_records) association_records
       from prov_association_detail a,prov_table_list b
where a.table_name = b.table_name and b.enable_status = '1'
and not exists (select 1 from emergency_association_config c where a.table_name = c.table_name
and a.association_table_name = c.association_table_name
and c.association_type = '3')
group by a.city, a.org_code, a.org_name,a.table_name,a.association_table_name) t
group by t.city,t.org_code,t.org_name
order by t.city,t.org_code;

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
    where a.table_name = b.table_name and b.enable_status = '1'
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
    where a.table_name = b.table_name and b.enable_status = '1'
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
    where a.table_name = b.table_name and b.enable_status = '1'
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
    where a.table_name = b.table_name and b.enable_status = '1'
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
    where a.table_name = b.table_name and b.enable_status = '1'
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
    where a.table_name = b.table_name and b.enable_status = '1'
group by a.city, a.org_code, a.org_name,a.column_level
order by a.city, a.org_code,a.column_level;

insert into prov_column_level_org
select a.city,
       a.org_code,
       a.org_name,
       concat('version_2_column_level_',a.column_level) as column_level,
       sum(a.total_records)                                                        total_records,
       sum(a.notnull_records)                                                      notnull_records,
       case
           when sum(a.total_records) > 0 then
               round((sum(a.notnull_records) / sum(a.total_records)) * 100, 2) end notnull_rate
from prov_update_version_2_detail a,prov_table_list b
    where a.table_name = b.table_name and b.enable_status = '1'
group by a.city, a.org_code, a.org_name,a.column_level
order by a.city, a.org_code,a.column_level;


-- 业务主键唯一率机构汇总
truncate table prov_business_org;
insert into prov_business_org
select a.city,
       a.org_code,
       a.org_name,
       sum(a.total_records)                                                       total_records,
       sum(a.unique_records)                                                      unique_records,
       case
           when sum(a.total_records) > 0 then
               round((sum(a.unique_records) / sum(a.total_records)) * 100, 2) end unique_rate
from prov_business_detail a,
     prov_table_list b
where a.table_name = b.table_name
group by a.city, a.org_code, a.org_name
order by a.city, a.org_code;

-- 机构汇总结果生成
truncate table prov_city_summary;

insert into prov_city_summary
select a.city,
       count(a.org_code) org_cnt,
       sum(case when b.compliance_rate >=90 then 1 else 0 end) real_cnt,
       sum(case when c.compliance_rate >=100 then 1 else 0 end ) hour_cnt,
       sum(case when d.compliance_rate >=98 then 1 else 0 end) other_cnt,
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
       sum(j.total_records) j_total_records,
       sum(j.notnull_records) j_notnull_records,
       sum(k.total_records) k_total_records,
       sum(k.notnull_records) k_notnull_records,
       sum(case when m.association_rate >=90 then 1 else 0 end) association_org_cnt
from org_list a
 left join prov_timeliness_org b on b.org_code = a.org_code and b.table_level = '1'
         left join prov_timeliness_org c on c.org_code = a.org_code and c.table_level = '2'
         left join prov_timeliness_org d on d.org_code = a.org_code and d.table_level = '3'
         left join prov_column_level_org e on e.org_code = a.org_code and e.column_level = '1'
         left join prov_column_level_org f on f.org_code = a.org_code and f.column_level = '2'
         left join prov_column_level_org g on g.org_code = a.org_code and g.column_level = '3'
         left join prov_column_level_org h on h.org_code = a.org_code and h.column_level = 'update_1'
         left join prov_column_level_org i on i.org_code = a.org_code and i.column_level = 'update_3'
         left join prov_column_level_org j on j.org_code = a.org_code and j.column_level = 'version_2_column_level_1'
         left join prov_column_level_org k on k.org_code = a.org_code and k.column_level = 'version_2_column_level_3'
         left join prov_association_org m on m.org_code = a.org_code and m.association_table = 'all'
   where a.is_516_flag = '是'
group by a.city;