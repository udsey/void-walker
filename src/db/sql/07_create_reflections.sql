CREATE TABLE
    IF NOT EXISTS reflections (
        id SERIAL PRIMARY KEY,
        session_id UUID REFERENCES sessions (session_id) ON DELETE CASCADE,
        timestamp TIMESTAMP NOT NULL,
        action_name TEXT NOT NULL,
        mood_before TEXT,
        mood_after TEXT,
        reflection TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );