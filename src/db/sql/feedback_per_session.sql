select f.timestamp, f.feedback_text
from feedback f
where f.session_id = %s
order by f.timestamp;
