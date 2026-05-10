select
    r.timestamp, r.action_name as after_action,
    r.mood_before, r.mood_after,
    r.mood_before != r.mood_after as mood_shifted,
    r.reflection
from reflections r
where r.session_id = %s
order by r.timestamp;