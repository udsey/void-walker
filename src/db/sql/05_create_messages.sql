CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    session_id UUID
    REFERENCES sessions(session_id) ON DELETE CASCADE,
    timestamp TIMESTAMP NOT NULL,
    message TEXT NOT NULL,
    reply_to TEXT,
    is_sent BOOLEAN,
    last_read_messages TEXT[] DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);