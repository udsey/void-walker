select
    a.id, a.name as action_name, a.timestamp,
    a.timestamp - lag(a.timestamp) over (
        partition by a.session_id
        order by a.timestamp) as time_since_prev,
    a.llm_reason, a.llm_answer, a.function_result
from actions a
where a.session_id = %s
order by a.timestamp;