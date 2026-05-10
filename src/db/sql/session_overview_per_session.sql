select
    s.session_id, s.name, s.is_friend,
    s.model_name, s.model_temperature,
    s.initial_url, s.current_url,
    s.exit_reason, s.start_time, s.end_time,
    (s.end_time - s.start_time) as session_duration,
    s.total_actions, s.total_invited,
    count(
        distinct a.id)
        as logged_actions,
    count(
        distinct case when a.name = 'reflect' then a.id end)
        as reflections,
    count(
        distinct case when a.name = 'select_action' then a.id end)
        as selections,
    count(
        distinct m.id) as messages_sent,
    count(
        distinct case when m.reply_to is not null then m.id end)
        as replies_sent,
    count(distinct i.id) as invites_sent,
    p.age, p.gender, p.country, p.mother_language, p.second_languages,
    p.archetype, p.social_tendency, p.attention_span,
    p.mood as initial_mood
from sessions s
left join actions a on a.session_id = s.session_id
left join messages m on
    m.session_id = s.session_id and m.is_sent = true
left join invites i on i.session_id = s.session_id
left join personas p on p.session_id = s.session_id
where s.session_id = %s
group by s.session_id, p.id;