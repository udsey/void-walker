sessions = """
            CREATE TABLE IF NOT EXISTS sessions (
                session_id UUID PRIMARY KEY,
                friend_session_id UUID,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP,
                model_name TEXT,
                model_temperature FLOAT,
                name TEXT,
                system_prompt TEXT,
                current_url TEXT,
                is_friend BOOLEAN DEFAULT FALSE,
                total_actions INTEGER DEFAULT 0,
                total_invited INTEGER DEFAULT 0,
                summary TEXT,
                exit_reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """

actions = """
            CREATE TABLE IF NOT EXISTS actions (
                id SERIAL PRIMARY KEY,
                session_id UUID REFERENCES sessions(session_id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                llm_prompt TEXT,
                llm_answer TEXT,
                llm_reason TEXT,
                function_result TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """

feedback = """
            CREATE TABLE IF NOT EXISTS feedback (
                id SERIAL PRIMARY KEY,
                session_id UUID REFERENCES sessions(session_id) ON DELETE CASCADE,
                timestamp TIMESTAMP NOT NULL,
                feedback_text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """

invites = """
            CREATE TABLE IF NOT EXISTS invites (
                id SERIAL PRIMARY KEY,
                session_id UUID REFERENCES sessions(session_id) ON DELETE CASCADE,
                timestamp TIMESTAMP NOT NULL,
                name TEXT,
                friends_name TEXT,
                common_language TEXT,
                shared_url TEXT,
                message TEXT,
                friend_session_id UUID,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """

messages = """
            CREATE TABLE IF NOT EXISTS messages (
                id SERIAL PRIMARY KEY,
                session_id UUID REFERENCES sessions(session_id) ON DELETE CASCADE,
                timestamp TIMESTAMP NOT NULL,
                message TEXT NOT NULL,
                reply_to TEXT,
                is_sent BOOLEAN,
                last_read_messages TEXT[] DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """

reflections = """
            CREATE TABLE IF NOT EXISTS reflections (
                id SERIAL PRIMARY KEY,
                session_id UUID REFERENCES sessions(session_id) ON DELETE CASCADE,
                timestamp TIMESTAMP NOT NULL,
                action_name TEXT NOT NULL,
                mood_before TEXT,
                mood_after TEXT,
                reflection TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """

personas = """
    CREATE TABLE IF NOT EXISTS personas (
        id SERIAL PRIMARY KEY,
        session_id UUID REFERENCES sessions(session_id) ON DELETE CASCADE,
        timestamp TIMESTAMP NOT NULL,
        name VARCHAR(50),
        age INT,
        gender VARCHAR(20),
        country VARCHAR(50),
        mother_language VARCHAR(50),
        second_languages TEXT[],  -- Array of languages
        archetype TEXT,
        social_tendency VARCHAR(50),
        attention_span VARCHAR(20),
        mood VARCHAR(50),
        is_friend BOOLEAN DEFAULT FALSE,
        system_prompt TEXT
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
"""


create_indexes = """
            CREATE INDEX IF NOT EXISTS idx_sessions_name ON sessions(name);
            CREATE INDEX IF NOT EXISTS idx_sessions_exit_reason ON sessions(exit_reason);
            CREATE INDEX IF NOT EXISTS idx_actions_session_id ON actions(session_id);
            CREATE INDEX IF NOT EXISTS idx_reflections_session_id ON reflections(session_id);
            CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id);
            CREATE INDEX IF NOT EXISTS idx_invites_friend_session_id ON invites(friend_session_id);
        """


QUERIES = {
    "1_session_overview": """
        select
            s.session_id, s.name, s.is_friend, s.model_name, s.model_temperature,
            s.exit_reason, s.start_time, s.end_time,
            (s.end_time - s.start_time) as session_duration,
            s.total_actions, s.total_invited,
            count(distinct a.id) as logged_actions,
            count(distinct case when a.name = 'reflect' then a.id end) as reflections,
            count(distinct case when a.name = 'select_action' then a.id end) as selections,
            count(distinct m.id) as messages_sent,
            count(distinct case when m.reply_to is not null then m.id end) as replies_sent,
            count(distinct i.id) as invites_sent,
            p.age, p.gender, p.country, p.mother_language, p.second_languages,
            p.archetype, p.social_tendency, p.attention_span, p.mood as initial_mood
        from sessions s
        left join actions a on a.session_id = s.session_id
        left join messages m on m.session_id = s.session_id and m.is_sent = true
        left join invites i on i.session_id = s.session_id
        left join personas p on p.session_id = s.session_id
        where s.session_id = %s
        group by s.session_id, p.id
    """,
    "2_actions_sequence": """
        select
            a.id, a.name as action_name, a.timestamp,
            a.timestamp - lag(a.timestamp) over (partition by a.session_id order by a.timestamp) as time_since_prev,
            a.llm_reason, a.llm_answer, a.function_result
        from actions a
        where a.session_id = %s
        order by a.timestamp
    """,
    "3_mood_timeline": """
        select
            r.timestamp, r.action_name as after_action,
            r.mood_before, r.mood_after,
            r.mood_before != r.mood_after as mood_shifted,
            r.reflection
        from reflections r
        where r.session_id = %s
        order by r.timestamp
    """,
    "4_messages": """
        select
            m.id, m.timestamp, m.is_sent, m.message, m.reply_to,
            m.last_read_messages,
            case when m.reply_to is not null then true else false end as is_reply
        from messages m
        where m.session_id = %s
        order by m.timestamp
    """,
    "5_invites": """
        select
            i.timestamp, i.name as from_walker, i.friends_name as to_friend,
            i.common_language, i.message, i.shared_url, i.friend_session_id,
            s.exit_reason as friend_exit_reason,
            (s.end_time - s.start_time) as friend_session_duration
        from invites i
        left join sessions s on s.session_id = i.friend_session_id
        where i.session_id = %s
        order by i.timestamp
    """,
    "6_feedback": """
        select f.timestamp, f.feedback_text
        from feedback f
        where f.session_id = %s
        order by f.timestamp
    """,
    "7_tool_usage": """
        select
            a.name as tool_name,
            count(*) as times_used,
            count(case when a.function_result not ilike '%%fail%%'
                       and a.function_result not ilike '%%error%%' then 1 end) as success_count,
            count(case when a.function_result ilike '%%fail%%'
                       or a.function_result ilike '%%error%%' then 1 end) as fail_count,
            round(count(case when a.function_result not ilike '%%fail%%'
                             and a.function_result not ilike '%%error%%' then 1 end)
                  * 100.0 / count(*), 1) as success_rate_pct,
            min(a.timestamp) as first_used,
            max(a.timestamp) as last_used
        from actions a
        where a.session_id = %s
        and a.name not in ('reflect', 'select_action', 'decide_open_website',
                           'initialize_tools', 'open_website', 'observe_website',
                           'close_website', 'check_conditions')
        group by a.name
        order by times_used desc
    """
}
