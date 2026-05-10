select
    m.id, m.timestamp, m.is_sent, m.message, m.reply_to,
    m.last_read_messages,
    case when m.reply_to is not null
        then true else false end as is_reply
from messages m
where m.session_id = %s
order by m.timestamp;