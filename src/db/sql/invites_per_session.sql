select
    i.timestamp, i.name as from_walker, i.friends_name as to_friend,
    i.common_language, i.message, i.shared_url, i.friend_session_id,
    s.exit_reason as friend_exit_reason,
    (s.end_time - s.start_time) as friend_session_duration
from invites i
left join sessions s on s.session_id = i.friend_session_id
where i.session_id = %s
order by i.timestamp;