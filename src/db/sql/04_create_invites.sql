CREATE TABLE
    IF NOT EXISTS invites (
        id SERIAL PRIMARY KEY,
        session_id UUID REFERENCES sessions (session_id) ON DELETE CASCADE,
        timestamp TIMESTAMP NOT NULL,
        name TEXT,
        friends_name TEXT,
        common_language TEXT,
        shared_url TEXT,
        message TEXT,
        friend_session_id UUID,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );