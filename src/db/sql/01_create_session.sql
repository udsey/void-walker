CREATE TABLE
    IF NOT EXISTS sessions (
        session_id UUID PRIMARY KEY,
        parent_session_id UUID,
        start_time TIMESTAMP NOT NULL,
        end_time TIMESTAMP,
        model_name TEXT,
        model_temperature FLOAT,
        name TEXT,
        system_prompt TEXT,
        mood TEXT,
        current_url TEXT,
        initial_url TEXT,
        is_friend BOOLEAN DEFAULT FALSE,
        total_actions INTEGER DEFAULT 0,
        total_invited INTEGER DEFAULT 0,
        summary TEXT,
        exit_reason TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );