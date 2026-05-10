CREATE TABLE
    IF NOT EXISTS actions (
        id SERIAL PRIMARY KEY,
        session_id UUID REFERENCES sessions (session_id) ON DELETE CASCADE,
        name TEXT NOT NULL,
        timestamp TIMESTAMP NOT NULL,
        llm_prompt TEXT,
        llm_answer TEXT,
        llm_reason TEXT,
        function_result TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );