CREATE TABLE
    IF NOT EXISTS feedback (
        id SERIAL PRIMARY KEY,
        session_id UUID REFERENCES sessions (session_id) ON DELETE CASCADE,
        timestamp TIMESTAMP NOT NULL,
        feedback_text TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );