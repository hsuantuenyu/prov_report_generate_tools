select city,
       org_cnt,
       real_cnt,
       concat(round((real_cnt / org_cnt) * 100, 2), '%')                  as real_rate,
       hour_cnt,
       concat(round((hour_cnt / org_cnt) * 100, 2), '%')                  as hour_rate,
       other_cnt,
       concat(round((other_cnt / org_cnt) * 100, 2), '%')                 as other_rate,
       e_total_records,
       e_notnull_records,
       case when e_total_records >0 then 
       concat(round((e_notnull_records / e_total_records) * 100, 2), '%') end as e_notnull_rate,
       f_total_records,
       f_notnull_records,
       case when f_total_records >0 then 
       concat(round((f_notnull_records / f_total_records) * 100, 2), '%') end as f_notnull_rate,
       g_total_records,
       g_notnull_records,
       case when g_total_records >0 then 
       concat(round((g_notnull_records / g_total_records) * 100, 2), '%') end as g_notnull_rate,
       h_total_records,
       h_notnull_records,
       case when h_total_records >0 then 
       concat(round((h_notnull_records / h_total_records) * 100, 2), '%') end as h_notnull_rate,
       i_total_records,
       i_notnull_records,
       case when i_total_records >0 then 
       concat(round((i_notnull_records / i_total_records) * 100, 2), '%') end as i_notnull_rate,
       association_org_cnt,
       concat(round((association_org_cnt / org_cnt) * 100, 2), '%')       as association__rate
from prov_city_summary a
union
select 'Total'                                                                            city,
       sum(org_cnt),
       sum(real_cnt),
       concat(round((sum(real_cnt) / sum(org_cnt)) * 100, 2), '%')                  as real_rate,
       sum(hour_cnt)                                                                   hour_cnt,
       concat(round((sum(hour_cnt) / sum(org_cnt)) * 100, 2), '%')                  as hour_rate,
       sum(other_cnt)                                                                  other_cnt,
       concat(round((sum(other_cnt) / sum(org_cnt)) * 100, 2), '%')                 as other_rate,
       sum(e_total_records)                                                            e_total_records,
       sum(e_notnull_records)                                                          e_notnull_records,
       concat(round((sum(e_notnull_records) / sum(e_total_records)) * 100, 2), '%') as e_notnull_rate,
       sum(f_total_records)                                                            f_total_records,
       sum(f_notnull_records)                                                          f_notnull_records,
       concat(round((sum(f_notnull_records) / sum(f_total_records)) * 100, 2), '%') as f_notnull_rate,
       sum(g_total_records) g_total_records,
       sum(g_notnull_records)  g_notnull_records,
       concat(round((sum(g_notnull_records) / sum(g_total_records)) * 100, 2), '%') as g_notnull_rate,
       sum(h_total_records) h_total_records,
       sum(h_notnull_records) h_notnull_records,
       concat(round((sum(h_notnull_records) / sum(h_total_records)) * 100, 2), '%') as h_notnull_rate,
       sum(i_total_records)                                                            i_total_records,
       sum(i_notnull_records)                                                          i_notnull_records,
       
       concat(round((sum(i_notnull_records) / sum(i_total_records)) * 100, 2), '%')  i_not_notnull_rate,
       sum(association_org_cnt)                                                        association_org_cnt,
       concat(round((sum(association_org_cnt) / sum(org_cnt)) * 100, 2), '%')       as association__rate
from prov_city_summary
order by city;

-- 机构汇总
select a.city,
       a.org_code,
       a.org_name,
       b.total_records,
       b.compliance_records,
       case
           when b.total_records is null then null
           when b.total_records = 0 then '-'
           else concat(b.compliance_rate, '%') end  compliance_rate,
       c.total_records,
       c.compliance_records,
       case
           when c.total_records is null then null
           when c.total_records = 0 then '-'
           else concat(c.compliance_rate, '%') end  compliance_rate,
       d.total_records,
       d.compliance_records,
       case
           when d.total_records is null then null
           when d.total_records = 0 then '-'
           else concat(d.compliance_rate, '%') end  compliance_rate,
       e.total_records,
       e.notnull_records,
       case
           when e.total_records is null then null
           when e.total_records = 0 then '-'
           else concat(e.notnull_rate, '%') end     notnull_rate,
       f.total_records,
       f.notnull_records,
       case
           when f.total_records is null then null
           when f.total_records = 0 then '-'
           else concat(f.notnull_rate, '%') end     notnull_rate,
       g.total_records,
       g.notnull_records,
       case
           when g.total_records is null then null
           when g.total_records = 0 then '-'
           else concat(f.notnull_rate, '%') end     notnull_rate,
       h.total_records,
       h.notnull_records,
       case
           when h.total_records is null then null
           when h.total_records = 0 then '-'
           else concat(h.notnull_rate, '%') end     notnull_rate,
       i.total_records,
       i.notnull_records,
       case
           when i.total_records is null then null
           when i.total_records = 0 then '-'
           else concat(i.notnull_rate, '%') end     notnull_rate,
       j.total_records,
       j.association_records,
       case
           when j.total_records is null then null
           when j.total_records = 0 then '-'
           else concat(j.association_rate, '%') end association_rate,
       k.total_records,
       k.association_records,
       case
           when k.total_records is null then null
           when k.total_records = 0 then '-'
           else concat(k.association_rate, '%') end association_rate,
       l.total_records,
       l.association_records,
       case
           when l.total_records is null then null
           when l.total_records = 0 then '-'
           else concat(l.association_rate, '%') end association_rate
from org_list a
         left join prov_timeliness_org b on b.org_code = a.org_code and b.table_level = '1'
         left join prov_timeliness_org c on c.org_code = a.org_code and c.table_level = '2'
         left join prov_timeliness_org d on d.org_code = a.org_code and d.table_level = '3'
         left join prov_column_level_org e on e.org_code = a.org_code and e.column_level = '1'
         left join prov_column_level_org f on f.org_code = a.org_code and f.column_level = '2'
         left join prov_column_level_org g on g.org_code = a.org_code and g.column_level = '3'
         left join prov_column_level_org h on h.org_code = a.org_code and h.column_level = 'update_1'
         left join prov_column_level_org i on i.org_code = a.org_code and i.column_level = 'update_3'
         left join prov_association_org j on j.org_code = a.org_code and j.association_table = 'pro_base_person_ylfw'
         left join prov_association_org k on k.org_code = a.org_code and k.association_table = 'pro_opt_diagnosisbreakdown,pro_ipt_diagnosisbreakdown'
         left join prov_association_org l on l.org_code = a.org_code and l.association_table = 'all'
where a.is_516_flag = '是'
order by a.city, a.org_code;

-- 时效性sheet页
select a.city,
       a.org_code,
       a.org_name,
       b.table_name,
       b.table_comment,
       b.table_level,
       b.total_records,
       b.compliance_records,
       case
           when total_records is null then null
           when total_records = 0 then '-'
           else
               concat(round(b.compliance_rate*100,2), '%') end compliance_rate,
       b.table_flag
from org_list a
         left join prov_timeliness_detail b on a.org_code = b.org_code
         join prov_table_list c on b.table_name = c.table_name and c.national_flag='1'
where a.is_516_flag = '是'
order by a.city, a.org_code;

-- 必填字段完整性
select a.city,
       a.org_code,
       a.org_name,
       b.table_name,
       c.table_comment table_comment,
       b.total_records,
       b.notnull_records,
       case
           when total_records is null then null
           when total_records = 0 then '-'
           else
               concat(round(b.notnull_rate*100,2), '%') end notnull_rate
from org_list a
    left join prov_column_level_1_detail b on a.org_code = b.org_code
    join prov_table_list c on b.table_name = c.table_name and c.national_flag='1'
where a.is_516_flag = '是'
order by a.city, a.org_code;

-- 关键建议填
select a.city,
       a.org_code,
       a.org_name,
       b.table_name,
       c.table_comment table_comment,
       b.total_records,
       b.notnull_records,
       case
           when total_records is null then null
           when total_records = 0 then '-'
           else
               concat(round(b.notnull_rate*100,2), '%') end notnull_rate
from org_list a
         left join prov_column_level_2_detail b on a.org_code = b.org_code
         join prov_table_list c on b.table_name = c.table_name and c.national_flag='1'
where a.is_516_flag = '是'
order by a.city, a.org_code;

-- 条件必填
select a.city,
       a.org_code,
       a.org_name,
       b.table_name,
       b.table_comment,
       b.total_records,
       b.notnull_records,
       case
           when total_records is null then null
           when total_records = 0 then '-'
           else
               concat(round(b.notnull_rate*100,2), '%') end notnull_rate
from org_list a
         left join prov_column_level_3_detail b on a.org_code = b.org_code
         join prov_table_list c on b.table_name = c.table_name and c.national_flag='1'
where a.is_516_flag = '是'
order by a.city, a.org_code;

-- 关联关系明细
select a.city,a.org_code,a.org_name,
       b.table_name,
       c.table_comment table_comment,
       b.association_table_name,
       d.table_comment   association_table_comment,
       b.total_records,
       b.association_records,
       case when total_records = 0 then '-'
           else
               concat(round(b.association_rate*100,2),'%')
           end association_rate
       from org_list a
    left join  prov_association_detail b on b.org_code = a.org_code
    join prov_table_list c on b.table_name = c.table_name and c.national_flag='1'
    left join prov_table_list d on b.association_table_name = d.table_name
where a.is_516_flag ='是'
order by a.city,a.org_code;

-- 主诉sheet页明细

select a.city,
       a.org_code,
       a.org_name,
       a.station_hospital,
       b.table_name,
        c.table_comment table_comment,
       b.field_name,
       '主诉' field_comment,
       b.total_records,
       b.notnull_records,
       case
       when b.total_records is null then null
           when b.total_records = 0 then '-'
           else
               concat(round(b.notnull_rate*100,2), '%')
           end notnull_rate
from org_list a
         left join prov_chief_detail b on b.org_code = a.org_code and b.field_name in('bzzs', 'chiefcomplaint', 'zs')
         left join prov_table_list c on c.table_name = b.table_name
where a.is_516_flag = '是'
order by a.city, a.org_code;

-- 现病史
select a.city,
       a.org_code,
       a.org_name,
       a.station_hospital,
       b.table_name,
        c.table_comment table_comment,
       b.field_name,
       '现病史' field_comment,
       b.total_records,
       b.notnull_records,
       case
       when b.total_records is null then null
           when b.total_records = 0 then '-'
           else
               concat(round(b.notnull_rate*100,2), '%')
           end notnull_rate
from org_list a
         left join prov_chief_detail b on b.org_code = a.org_code and b.field_name in('bzxbs', 'xbs')
         left join prov_table_list c on c.table_name = b.table_name
where a.is_516_flag = '是'
order by a.city, a.org_code;