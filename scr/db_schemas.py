sessions = """
            CREATE TABLE IF NOT EXISTS sessions (
                session_id UUID PRIMARY KEY,
                parent_session_id UUID,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP,
                model_name TEXT,
                model_temperature FLOAT,
                name TEXT,
                persona TEXT,
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
                function_result TEXT
            )
        """

feedback = """
            CREATE TABLE IF NOT EXISTS feedback (
                id SERIAL PRIMARY KEY,
                session_id UUID REFERENCES sessions(session_id) ON DELETE CASCADE,
                timestamp TIMESTAMP NOT NULL,
                feedback_text TEXT NOT NULL
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
                friend_session_id UUID
            )
        """

messages = """
            CREATE TABLE IF NOT EXISTS messages (
                id SERIAL PRIMARY KEY,
                session_id UUID REFERENCES sessions(session_id) ON DELETE CASCADE,
                timestamp TIMESTAMP NOT NULL,
                message TEXT NOT NULL,
                reply_to TEXT,
                is_sent BOOLEAN DEFAULT TRUE,
                last_read_messages TEXT[] DEFAULT '{}'
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
                reflection TEXT
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