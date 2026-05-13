"""DB queries."""

import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

DATABASE_URL = (
    f"postgresql+psycopg2://{os.getenv('DB_USER')}:"
    f"{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:"
    f"{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}")
engine = create_engine(DATABASE_URL)


def query(sql: str, params: tuple = None) -> pd.DataFrame:
    """Query db."""
    df = pd.read_sql(sql, engine, params=params)
    for col in df.select_dtypes(include=["timedelta"]).columns:
        df[col] = df[col].astype(str)
    for col in df.select_dtypes(include=["object"]).columns:
        df[col] = df[col].apply(
            lambda x: ", ".join(x) if isinstance(x, list) else x)
    return df

# ~~~~~~~~~~~~~~~~~~ RAW Tables Page ~~~~~~~~~~~~~~~~~~

def get_sessions() -> pd.DataFrame:
    """Get sessions table."""
    return query("""select * from sessions
                    order by created_at desc
                    limit 1000""")


def get_actions() -> pd.DataFrame:
    """Get actions table."""
    return query("""select * from actions
                    order by created_at desc
                    limit 1000""")


def get_messages() -> pd.DataFrame:
    """Get messages table."""
    return query("""select * from messages
                    order by created_at desc
                    limit 100""")


def get_invites() -> pd.DataFrame:
    """Get invites table."""
    return query("""select * from invites
                    order by created_at desc
                    limit 100""")


def get_feedback() -> pd.DataFrame:
    """Get feedback table."""
    return query("""select * from feedback
                    order by created_at desc
                    limit 100""")


def get_reflections() -> pd.DataFrame:
    """Get reflections table"""
    return query("""select * from reflections
                    order by created_at desc
                    limit 100""")


def get_personas() -> pd.DataFrame:
    """Get personas table."""
    return query("""select * from personas
                    order by created_at desc
                    limit 100""")



raw_map = {
    "sessions": get_sessions,
    "actions": get_actions,
    "messages": get_messages,
    "invites": get_invites,
    "reflection": get_reflections,
    "personas": get_personas,
    "feedback": get_feedback

}


# ~~~~~~~~~~~~~~~~~~ Sessions Page ~~~~~~~~~~~~~~~~~~

def get_session_overview(session_id: str) -> pd.DataFrame:
    """Get session overview table."""
    query_text = """select
            s.session_id, s.name, s.is_friend,
            s.model_name, s.model_temperature,
            s.initial_url, s.current_url,
            s.exit_reason, s.start_time, s.end_time,
            (s.end_time - s.start_time) as session_duration,
            s.start_time as start_time,
            s.end_time as end_time,
            s.total_actions, s.total_invited,
            count(distinct a.id) as logged_actions,
            count(
            distinct case when a.name = 'reflect' then a.id end
            ) as reflections,
            count(
            distinct case when a.name = 'select_action' then a.id end
            ) as selections,
            count(distinct m.id) as messages_sent,
            count(
            distinct case when m.reply_to is not null then m.id end
            ) as replies_sent,
            count(distinct i.id) as invites_sent,
            p.age, p.gender, p.country, p.mother_language, p.second_languages,
            p.archetype, p.social_tendency,
            p.attention_span, p.mood as initial_mood, s.mood as final_mood
        from sessions s
        left join actions a on a.session_id = s.session_id
        left join messages m on
            m.session_id = s.session_id and m.is_sent = true
        left join invites i on i.session_id = s.session_id
        left join personas p on p.session_id = s.session_id
        where s.session_id = %s
        group by s.session_id, p.id"""
    return query(query_text, (session_id, ))


def get_actions_per_session(session_id: str) -> pd.DataFrame:
    """Get actions per session table."""
    query_text = """select
            a.*
        from actions a
        where a.session_id = %s
        order by a.timestamp"""
    return query(query_text, (session_id, ))


def get_mood_timeline_per_session(session_id: str) -> pd.DataFrame:
    """Get timeline per session table."""
    query_text = """select
            r.timestamp, r.action_name as after_action,
            r.mood_before, r.mood_after,
            r.mood_before != r.mood_after as mood_shifted,
            r.reflection
        from reflections r
        where r.session_id = %s
        order by r.timestamp"""
    return query(query_text, (session_id, ))


def get_messages_per_session(session_id: str) -> pd.DataFrame:
    """Get messages per session table."""
    query_text = """select
            m.*,
            case when m.reply_to is not null
            then true else false end as is_reply
        from messages m
        where m.session_id = %s
        order by m.timestamp"""
    return query(query_text, (session_id, ))


def get_invites_per_session(session_id: str) -> pd.DataFrame:
    """Get invites per session table."""
    query_text = """select
            i.*,
            s.exit_reason as friend_exit_reason,
            (s.end_time - s.start_time) as friend_session_duration
        from invites i
        left join sessions s on s.session_id = i.friend_session_id
        where i.session_id = %s
        order by i.timestamp"""
    return query(query_text, (session_id, ))


def get_feedback_per_session(session_id: str) -> pd.DataFrame:
    """Get feedback per session table."""
    query_text = """select f.*
        from feedback f
        where f.session_id = %s
        order by f.timestamp"""
    return query(query_text, (session_id, ))


def get_tool_usage_per_session(session_id: str) -> pd.DataFrame:
    """Get tool usage per session table."""
    query_text = """select
            a.name as tool_name,
            count(*) as times_used,
            count(case when a.function_result not ilike '%%fail%%'
                       and a.function_result not ilike '%%error%%'
                       then 1 end) as success_count,
            count(case when a.function_result ilike '%%fail%%'
                       or a.function_result ilike '%%error%%' then 1 end
                       ) as fail_count,
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
                           'observe_website',
                           'close_website', 'check_conditions', 'summarize')
        group by a.name
        order by times_used desc"""
    return query(query_text, (session_id, ))


session_map = {
    "overview": get_session_overview,
    "actions": get_actions_per_session,
    "mood timeline": get_mood_timeline_per_session,
    "messages": get_messages_per_session,
    "invites": get_invites_per_session,
    "feedback": get_feedback_per_session,
    "tool usage": get_tool_usage_per_session,
}


# ~~~~~~~~~~~~~~~~~~ Overview Page ~~~~~~~~~~~~~~~~~~


def get_overview_kpis() -> pd.DataFrame:
    """Get kpis."""
    return query("""
        select
            (select count(*) from sessions) as total_sessions,
            (select count(*) from messages where is_sent = true
                 ) as total_messages_sent,
            (select count(*) from messages where is_sent = false
                 ) as total_messages_failed,
            (select count(*) from actions) as total_actions,
            (select count(*) from invites) as total_invites,
            (select count(*) from feedback) as total_feedbacks,
            (select round(avg(total_actions), 1) from sessions
                 ) as avg_actions_per_session,
            (select round(avg(sent.cnt), 1) from (
                select count(*) as cnt from messages
                 where is_sent = true group by session_id
                 ) sent) as avg_messages_per_session,
            (select count(*) from reflections where mood_before != mood_after
                 ) as total_mood_shifts
    """)


def get_sessions_over_time() -> pd.DataFrame:
    """Get sessions over time."""
    return query("""
        select date_trunc('hour', start_time) as hour, count(*) as sessions
        from sessions
        group by hour order by hour
    """)


def get_action_distribution() -> pd.DataFrame:
    """Get action distribution."""
    return query("""
        select name as action, count(*) as times_used
        from actions
        where name not in ('reflect', 'select_action', 'decide_open_website',
                           'initialize_tools', 'open_website',
                           'observe_website',
                           'close_website', 'check_conditions', 'summarize')
        group by name order by times_used desc
    """)


def get_archetype_stats() -> pd.DataFrame:
    """Get archetype stats."""
    return query("""
        select
            p.archetype,
            count(distinct s.session_id) as sessions,
            avg(extract(epoch from (s.end_time - s.start_time))/60
                 ) as avg_duration_minutes,
            mode() within group (order by s.exit_reason) as most_common_exit
        from sessions s
        join personas p on p.session_id = s.session_id
        where s.end_time is not null
        group by p.archetype order by avg_duration_minutes desc
    """)


def get_exit_reason_distribution() -> pd.DataFrame:
    """Get exit reason distribution."""
    return query("""
        select exit_reason, count(*) as count
        from sessions
        where exit_reason is not null
        group by exit_reason order by count desc
    """)


def get_friend_vs_solo() -> pd.DataFrame:
    """Get friend/solo distribution."""
    return query("""
        select
            case when is_friend then 'friend' else 'solo' end as type,
            count(*) as count
        from sessions
        group by is_friend
    """)


overview_map = {
    "kpis": get_overview_kpis,
    "sessions_over_time": get_sessions_over_time,
    "action_distribution": get_action_distribution,
    "archetype_stats": get_archetype_stats,
    "exit_reasons": get_exit_reason_distribution,
    "friend_vs_solo": get_friend_vs_solo,
}


# ~~~~~~~~~~~~~~~~~~ Mood Page ~~~~~~~~~~~~~~~~~~

def get_mood_sankey() -> pd.DataFrame:
    """Get mood switches."""
    return query("""
        select mood_before, mood_after, count(*) as count
        from reflections
        where mood_before != mood_after
        and mood_before is not null and mood_after is not null
        group by mood_before, mood_after
        order by count desc
    """)


def get_mood_shift_counts() -> pd.DataFrame:
    """Get mood shift count."""
    return query("""
        select mood_after as mood, count(*) as shifts_into
        from reflections
        where mood_before != mood_after
        and mood_after is not null
        group by mood_after
        order by shifts_into desc
    """)


def get_mood_over_actions() -> pd.DataFrame:
    return query("""
        with numbered as (
            select p.archetype,
                   row_number() over (
                 partition by r.session_id order by r.timestamp) as action_n,
                   r.mood_after as mood
            from reflections r
            join personas p on p.session_id = r.session_id
            where r.mood_after is not null
        ),
        counted as (
            select archetype, action_n, mood, count(*) as count
            from numbered
            group by archetype, action_n, mood
        )
        select archetype, action_n, mood, count,
               count * 100.0 / sum(count) over (
                 partition by archetype, action_n) as pct
        from counted
        order by archetype, action_n, mood
    """)


mood_map = {
    "sankey": get_mood_sankey,
    "shift_counts": get_mood_shift_counts,
    "mood_over_actions": get_mood_over_actions,
}


# ~~~~~~~~~~~~~~~~~~ Personas Page ~~~~~~~~~~~~~~~~~~

def get_persona_world_map() -> pd.DataFrame:
    """Get personas per country."""
    return query("""
        select country, count(*) as count
        from personas
        group by country order by count desc
    """)

def get_archetype_distribution() -> pd.DataFrame:
    """Get archetype distribution."""
    return query("""
        select archetype, count(*) as count
        from personas
        group by archetype order by count desc
    """)

def get_social_tendency_distribution() -> pd.DataFrame:
    """Get social tendency distribution."""
    return query("""
        select social_tendency, count(*) as count
        from personas
        group by social_tendency order by count desc
    """)

def get_generation_distribution() -> pd.DataFrame:
    """Get generation distribution."""
    return query("""
        select generation, count(*) as count
        from personas
        group by generation order by count desc
    """)

personas_map = {
    "world_map": get_persona_world_map,
    "archetypes": get_archetype_distribution,
    "social_tendency": get_social_tendency_distribution,
    "generations": get_generation_distribution,
}


# ~~~~~~~~~~~~~~~~~~ Story Page ~~~~~~~~~~~~~~~~~~

def get_session_breakdown(session_id: str) -> pd.DataFrame:
    """Get session breakdown."""
    query_text = """
        select * from (
            select
                to_char(a.timestamp, 'MI:SS') as time,
                a.timestamp,
                a.session_id,
                a.name as action_name,
                r.reflection,
                a.llm_prompt,
                a.llm_answer,
                a.llm_reason,
                a.function_result,
                case
                    when lag(a.name) over
                    (partition by a.session_id
                    order by a.timestamp) = 'select_action'
                    then lag(a.llm_answer) over (
                    partition by a.session_id order by a.timestamp)
                    else ''
                end as selection_reason,
                r.mood_before,
                r.mood_after,
                (r.mood_before is not null)
                and (r.mood_before != r.mood_after) as mood_shift,
                i.friends_name as friend_name,
                i.message as invite_message,
                m.message,
                m.reply_to,
                m.is_sent as message_is_sent,
                f.feedback_text as feedback,
                s.exit_reason,
                s.summary
            from actions a
            left join reflections r on r.session_id = a.session_id
            and date_trunc('second', r.timestamp) = (
                select min(date_trunc('second', r2.timestamp))
                from reflections r2
                where r2.session_id = a.session_id
                and date_trunc('second',
                r2.timestamp) > date_trunc('second', a.timestamp)
                and a.name != 'open_website'
            )
            left join invites i on i.session_id = a.session_id
                and date_trunc('second',
                i.timestamp) = date_trunc('second', a.timestamp)
                and a.name = 'invite_friend'
            left join messages m on m.session_id = a.session_id
                and date_trunc('second',
                m.timestamp) = date_trunc('second', a.timestamp)
                and a.name in ('send_message', 'respond_to_message')
            left join feedback f on f.session_id = a.session_id
                and date_trunc('second',
                f.timestamp) = date_trunc('second', a.timestamp)
                and a.name = 'send_feedback'
            left join sessions s on s.session_id = a.session_id
            where a.session_id = %s
            and a.name not in ('check_conditions')
            order by a.timestamp
        ) sub
        where action_name not in ('select_action', 'reflect')
    """
    return query(query_text, (session_id, ))


def get_persona(session_id: str) -> pd.DataFrame:
    """Get persona info."""
    query_text = """
        select
        p.* ,
        s.mood as final_mood
        from personas p
        left join sessions s on p.session_id = s.session_id
        where p.session_id = %s"""
    return query(query_text, (session_id, ))


novel_map = {
    'session_breakdown': get_session_breakdown,
    'persona': get_persona
}




