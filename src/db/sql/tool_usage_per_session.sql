select
    a.name as tool_name,
    count(*) as times_used,
    count(case when a.function_result not ilike '%%fail%%'
                and a.function_result not ilike '%%error%%'
                then 1 end) as success_count,
    count(case when a.function_result ilike '%%fail%%'
                or a.function_result ilike '%%error%%'
                then 1 end) as fail_count,
    round(count(case when a.function_result not ilike '%%fail%%'
                        and a.function_result not ilike '%%error%%'
                        then 1 end)
            * 100.0 / count(*), 1) as success_rate_pct,
    min(a.timestamp) as first_used,
    max(a.timestamp) as last_used
from actions a
where a.session_id = %s
and a.name not in ('reflect', 'select_action', 'decide_open_website',
                    'initialize_tools', 'open_website',
                    'observe_website', 'close_website',
                    'check_conditions')
group by a.name
order by times_used desc;